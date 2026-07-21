import asyncio
import base64
import imaplib
import json
import logging
import re
from dataclasses import dataclass

from app import communication_adapters, communication_service

logger = logging.getLogger(__name__)

_CURSOR_VERSION = 2


@dataclass(frozen=True, slots=True)
class ImapMailbox:
    display_name: str
    select_name: str
    priority: int


@dataclass(slots=True)
class ImapMailboxCursor:
    newest_uid: int = 0
    backfill_before_uid: int = 1
    backfill_complete: bool = False


@dataclass(slots=True)
class ImapMailboxWork:
    mailbox: ImapMailbox
    state: ImapMailboxCursor
    new_uids: list[int]
    backfill_uids: list[int]


@dataclass(frozen=True, slots=True)
class ImapSourceSync:
    source_key: str
    cursor_value: str
    messages: tuple[communication_adapters.ReceivedMessage, ...]
    backfill_pending: bool
    backfill_remaining: int


def _encode_modified_utf7(value: str) -> str:
    result: list[str] = []
    pending: list[str] = []

    def flush_pending() -> None:
        if not pending:
            return
        encoded = base64.b64encode("".join(pending).encode("utf-16-be")).decode("ascii")
        result.append("&" + encoded.rstrip("=").replace("/", ",") + "-")
        pending.clear()

    for character in value:
        codepoint = ord(character)
        if 0x20 <= codepoint <= 0x7E and character != "&":
            flush_pending()
            result.append(character)
        elif character == "&":
            flush_pending()
            result.append("&-")
        else:
            pending.append(character)
    flush_pending()
    return "".join(result)


def _quoted_mailbox(value: str) -> str:
    encoded = _encode_modified_utf7(value)
    escaped = encoded.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _mailbox_entry(raw: bytes, fallback: str) -> ImapMailbox | None:
    match = re.match(
        rb'^\((?P<flags>[^)]*)\)\s+(?:NIL|"(?:\\.|[^"])*")\s+(?P<name>.+)$',
        raw,
    )
    if match is None:
        return None
    wire_name = match.group("name").strip()
    decoded_name = wire_name
    if decoded_name.startswith(b'"') and decoded_name.endswith(b'"'):
        decoded_name = decoded_name[1:-1].replace(b'\\"', b'"').replace(b"\\\\", b"\\")
    display_name = communication_adapters._decode_modified_utf7(
        decoded_name.decode("ascii", errors="replace")
    ).strip()
    if not display_name:
        return None
    return ImapMailbox(
        display_name=display_name,
        select_name=wire_name.decode("ascii", errors="replace"),
        priority=communication_adapters._mailbox_priority(raw, display_name, fallback),
    )


def _discover_mailboxes(client: imaplib.IMAP4, fallback: str) -> list[ImapMailbox]:
    fallback_mailbox = ImapMailbox(fallback, _quoted_mailbox(fallback), 0)
    status, data = client.list()
    if status != "OK" or not data:
        return [fallback_mailbox]

    found: list[ImapMailbox] = []
    seen: set[str] = set()
    for raw in data:
        if not isinstance(raw, bytes):
            continue
        flags = communication_adapters._mailbox_flags(raw)
        if b"\\noselect" in flags or b"\\all" in flags:
            continue
        mailbox = _mailbox_entry(raw, fallback)
        if mailbox is None or mailbox.display_name.casefold() in seen:
            continue
        seen.add(mailbox.display_name.casefold())
        found.append(mailbox)

    if fallback.casefold() not in seen:
        found.append(fallback_mailbox)
    found.sort(key=lambda item: (item.priority, item.display_name.casefold()))
    return found[:50] or [fallback_mailbox]


def _error_detail(error: BaseException) -> str:
    detail = " ".join(str(error).split())
    return (detail or type(error).__name__)[:300]


def _select_mailbox(
    client: imaplib.IMAP4,
    mailbox: ImapMailbox,
    *,
    readonly: bool,
    required: bool,
) -> bool:
    try:
        status, data = client.select(mailbox.select_name, readonly=readonly)
    except imaplib.IMAP4.error as error:
        if required:
            raise communication_adapters.CommunicationAdapterError(
                "sync_failed",
                f"IMAP could not open {mailbox.display_name}: {_error_detail(error)}",
            ) from error
        logger.warning(
            "Skipping IMAP mailbox %s after SELECT failed: %s",
            mailbox.display_name,
            _error_detail(error),
        )
        return False
    if status == "OK":
        return True
    detail = " ".join(
        item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
        for item in (data or [])
    ).strip()
    if required:
        suffix = f": {detail[:300]}" if detail else ""
        raise communication_adapters.CommunicationAdapterError(
            "sync_failed",
            f"IMAP could not open {mailbox.display_name}{suffix}",
        )
    logger.warning(
        "Skipping IMAP mailbox %s after SELECT returned %s",
        mailbox.display_name,
        status,
    )
    return False


def _positive_int(value: object, fallback: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed >= 0 else fallback


def _legacy_cursor(uid: object) -> ImapMailboxCursor | None:
    newest_uid = _positive_int(uid)
    if newest_uid <= 0:
        return None
    return ImapMailboxCursor(
        newest_uid=newest_uid,
        backfill_before_uid=newest_uid + 1,
        backfill_complete=False,
    )


def _load_cursor(
    cursor_value: str | None,
    fallback: str,
) -> dict[str, ImapMailboxCursor]:
    if not cursor_value:
        return {}
    if cursor_value.isdigit():
        state = _legacy_cursor(cursor_value)
        return {fallback: state} if state else {}
    try:
        payload = json.loads(cursor_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    if payload.get("version") == _CURSOR_VERSION:
        raw_mailboxes = payload.get("mailboxes")
        if not isinstance(raw_mailboxes, dict):
            return {}
        result: dict[str, ImapMailboxCursor] = {}
        for name, raw_state in raw_mailboxes.items():
            if not isinstance(name, str) or not name.strip() or not isinstance(raw_state, dict):
                continue
            newest_uid = _positive_int(raw_state.get("newest_uid"))
            before_uid = _positive_int(
                raw_state.get("backfill_before_uid"),
                newest_uid + 1 if newest_uid else 1,
            )
            result[name] = ImapMailboxCursor(
                newest_uid=newest_uid,
                backfill_before_uid=max(1, before_uid),
                backfill_complete=bool(raw_state.get("backfill_complete", False)),
            )
        return result

    result = {}
    for name, uid in payload.items():
        if not isinstance(name, str) or not name.strip():
            continue
        state = _legacy_cursor(uid)
        if state:
            result[name] = state
    return result


def _serialize_cursor(
    states: dict[str, ImapMailboxCursor],
    *,
    backfill_remaining: int,
) -> str:
    pending = any(not state.backfill_complete for state in states.values())
    payload = {
        "version": _CURSOR_VERSION,
        "backfill_pending": pending,
        "backfill_remaining": max(0, backfill_remaining),
        "mailboxes": {
            name: {
                "newest_uid": state.newest_uid,
                "backfill_before_uid": state.backfill_before_uid,
                "backfill_complete": state.backfill_complete,
            }
            for name, state in sorted(states.items(), key=lambda item: item[0].casefold())
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def imap_backfill_progress(cursor_value: str | None) -> tuple[bool, int]:
    if not cursor_value:
        return False, 0
    try:
        payload = json.loads(cursor_value)
    except json.JSONDecodeError:
        return True, 0 if cursor_value.isdigit() else 0
    if not isinstance(payload, dict):
        return False, 0
    if payload.get("version") != _CURSOR_VERSION:
        return bool(payload), 0
    remaining = _positive_int(payload.get("backfill_remaining"))
    return bool(payload.get("backfill_pending", False)), remaining


def _search_uids(
    client: imaplib.IMAP4,
    mailbox: ImapMailbox,
    criteria: str,
    *,
    required: bool,
) -> list[int] | None:
    try:
        status, data = client.uid("search", None, criteria)
    except imaplib.IMAP4.error as error:
        if required:
            raise communication_adapters.CommunicationAdapterError(
                "sync_failed",
                f"IMAP search failed in {mailbox.display_name}: {_error_detail(error)}",
            ) from error
        logger.warning(
            "Skipping IMAP mailbox %s after SEARCH failed: %s",
            mailbox.display_name,
            _error_detail(error),
        )
        return None
    if status != "OK":
        if required:
            raise communication_adapters.CommunicationAdapterError(
                "sync_failed",
                f"IMAP search failed in {mailbox.display_name}.",
            )
        logger.warning(
            "Skipping IMAP mailbox %s after SEARCH returned %s",
            mailbox.display_name,
            status,
        )
        return None
    raw_values = data[0].split() if data and data[0] else []
    return sorted(
        {
            int(raw_uid)
            for raw_uid in raw_values
            if isinstance(raw_uid, bytes) and raw_uid.isdigit() and int(raw_uid) > 0
        }
    )


def _initial_work(
    client: imaplib.IMAP4,
    mailbox: ImapMailbox,
    *,
    required: bool,
) -> ImapMailboxWork | None:
    all_uids = _search_uids(client, mailbox, "ALL", required=required)
    if all_uids is None:
        return None
    if not all_uids:
        return ImapMailboxWork(
            mailbox=mailbox,
            state=ImapMailboxCursor(backfill_complete=True),
            new_uids=[],
            backfill_uids=[],
        )
    newest_uid = all_uids[-1]
    return ImapMailboxWork(
        mailbox=mailbox,
        state=ImapMailboxCursor(
            newest_uid=newest_uid,
            backfill_before_uid=newest_uid + 1,
            backfill_complete=False,
        ),
        new_uids=[],
        backfill_uids=list(reversed(all_uids)),
    )


def _existing_work(
    client: imaplib.IMAP4,
    mailbox: ImapMailbox,
    state: ImapMailboxCursor,
    *,
    required: bool,
) -> ImapMailboxWork | None:
    new_criteria = f"UID {state.newest_uid + 1}:*" if state.newest_uid else "ALL"
    new_uids = _search_uids(client, mailbox, new_criteria, required=required)
    if new_uids is None:
        return None
    new_uids = [uid for uid in new_uids if uid > state.newest_uid]

    backfill_uids: list[int] = []
    if not state.backfill_complete:
        upper = max(0, state.backfill_before_uid - 1)
        if upper == 0:
            state.backfill_complete = True
        else:
            found = _search_uids(client, mailbox, f"UID 1:{upper}", required=required)
            if found is None:
                return None
            backfill_uids = [uid for uid in reversed(found) if uid < state.backfill_before_uid]
            if not backfill_uids:
                state.backfill_complete = True
                state.backfill_before_uid = 1

    return ImapMailboxWork(
        mailbox=mailbox,
        state=state,
        new_uids=new_uids,
        backfill_uids=backfill_uids,
    )


def _allocate_round_robin(
    queues: dict[str, list[int]],
    budget: int,
) -> dict[str, list[int]]:
    allocations = {name: [] for name in queues}
    names = list(queues)
    while budget > 0:
        progressed = False
        for name in names:
            queue = queues[name]
            if not queue:
                continue
            allocations[name].append(queue.pop(0))
            budget -= 1
            progressed = True
            if budget == 0:
                break
        if not progressed:
            break
    return allocations


def _merge_allocations(
    target: dict[str, list[int]],
    extra: dict[str, list[int]],
) -> None:
    for name, values in extra.items():
        target.setdefault(name, []).extend(values)


def _allocate_work(
    work: dict[str, ImapMailboxWork],
    limit: int,
) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    new_queues = {name: list(item.new_uids) for name, item in work.items()}
    backfill_queues = {name: list(item.backfill_uids) for name, item in work.items()}
    has_new = any(new_queues.values())
    has_backfill = any(backfill_queues.values())

    initial_new_budget = limit
    if has_new and has_backfill and limit > 1:
        initial_new_budget = max(1, limit // 2)
    elif not has_new:
        initial_new_budget = 0

    new_allocations = _allocate_round_robin(new_queues, initial_new_budget)
    used = sum(len(values) for values in new_allocations.values())
    remaining = max(0, limit - used)
    backfill_allocations = _allocate_round_robin(backfill_queues, remaining)
    used += sum(len(values) for values in backfill_allocations.values())
    remaining = max(0, limit - used)
    if remaining:
        _merge_allocations(
            new_allocations,
            _allocate_round_robin(new_queues, remaining),
        )
    return new_allocations, backfill_allocations


def _fetch_message(
    client: imaplib.IMAP4,
    mailbox: ImapMailbox,
    uid: int,
) -> communication_adapters.ReceivedMessage | None:
    try:
        status, fetched = client.uid("fetch", str(uid), "(RFC822 FLAGS)")
    except imaplib.IMAP4.error as error:
        logger.warning(
            "Skipping IMAP message %s/%s after FETCH failed: %s",
            mailbox.display_name,
            uid,
            _error_detail(error),
        )
        return None
    if status != "OK" or not fetched:
        return None
    raw_message = next(
        (
            item[1]
            for item in fetched
            if isinstance(item, tuple) and isinstance(item[1], bytes)
        ),
        None,
    )
    if raw_message is None:
        return None
    flags = " ".join(
        item[0].decode("utf-8", errors="replace")
        for item in fetched
        if isinstance(item, tuple) and isinstance(item[0], bytes)
    )
    return communication_adapters._parse_imap_message(
        raw_message,
        uid=str(uid),
        folder=mailbox.display_name,
        flags=flags,
    )


def _state_for_mailbox(
    states: dict[str, ImapMailboxCursor],
    mailbox: ImapMailbox,
) -> ImapMailboxCursor | None:
    direct = states.get(mailbox.display_name)
    if direct is not None:
        return direct
    matched_name = next(
        (
            name
            for name in states
            if name.casefold() == mailbox.display_name.casefold()
        ),
        None,
    )
    if matched_name is None:
        return None
    state = states.pop(matched_name)
    states[mailbox.display_name] = state
    return state


def _gather_work(
    client: imaplib.IMAP4,
    mailboxes: list[ImapMailbox],
    states: dict[str, ImapMailboxCursor],
    fallback: str,
) -> dict[str, ImapMailboxWork]:
    work: dict[str, ImapMailboxWork] = {}
    for mailbox in mailboxes:
        required = mailbox.display_name.casefold() == fallback.casefold()
        if not _select_mailbox(client, mailbox, readonly=True, required=required):
            continue
        state = _state_for_mailbox(states, mailbox)
        item = (
            _existing_work(client, mailbox, state, required=required)
            if state is not None
            else _initial_work(client, mailbox, required=required)
        )
        if item is None:
            continue
        states[mailbox.display_name] = item.state
        work[mailbox.display_name] = item
    return work


def _fetch_allocated(
    client: imaplib.IMAP4,
    work: dict[str, ImapMailboxWork],
    new_allocations: dict[str, list[int]],
    backfill_allocations: dict[str, list[int]],
    fallback: str,
) -> tuple[list[communication_adapters.ReceivedMessage], dict[str, int]]:
    messages: list[communication_adapters.ReceivedMessage] = []
    successful_backfill = {name: 0 for name in work}
    for name, item in work.items():
        allocated_new = new_allocations.get(name, [])
        allocated_backfill = backfill_allocations.get(name, [])
        if not allocated_new and not allocated_backfill:
            continue
        required = item.mailbox.display_name.casefold() == fallback.casefold()
        if not _select_mailbox(client, item.mailbox, readonly=True, required=required):
            continue

        for uid in allocated_new:
            message = _fetch_message(client, item.mailbox, uid)
            if message is None:
                break
            messages.append(message)
            item.state.newest_uid = uid

        for uid in allocated_backfill:
            message = _fetch_message(client, item.mailbox, uid)
            if message is None:
                item.state.backfill_before_uid = uid + 1
                break
            messages.append(message)
            successful_backfill[name] += 1
            item.state.backfill_before_uid = uid
        else:
            if allocated_backfill and len(allocated_backfill) == len(item.backfill_uids):
                item.state.backfill_complete = True
                item.state.backfill_before_uid = 1
    return messages, successful_backfill


def _sync_imap_sync(
    config: dict[str, object],
    credentials: dict[str, str],
    cursor_value: str | None,
) -> ImapSourceSync:
    client = communication_adapters._imap_connect(config, credentials)
    fallback = str(config["folder"])
    limit = int(config.get("max_messages_per_sync", 50))
    states = _load_cursor(cursor_value, fallback)
    try:
        mailboxes = _discover_mailboxes(client, fallback)
        work = _gather_work(client, mailboxes, states, fallback)
        new_allocations, backfill_allocations = _allocate_work(work, limit)
        messages, successful_backfill = _fetch_allocated(
            client,
            work,
            new_allocations,
            backfill_allocations,
            fallback,
        )
        backfill_remaining = sum(
            max(0, len(item.backfill_uids) - successful_backfill.get(name, 0))
            for name, item in work.items()
            if not item.state.backfill_complete
        )
        backfill_pending = any(not state.backfill_complete for state in states.values())
        messages.sort(key=lambda message: message.sent_at)
        return ImapSourceSync(
            source_key=f"imap:{fallback}",
            cursor_value=_serialize_cursor(
                states,
                backfill_remaining=backfill_remaining,
            ),
            messages=tuple(messages),
            backfill_pending=backfill_pending,
            backfill_remaining=backfill_remaining,
        )
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            client.shutdown()


async def sync_imap_account(
    config: dict[str, object],
    credentials: dict[str, str],
    cursor_value: str | None,
) -> ImapSourceSync:
    try:
        return await asyncio.to_thread(_sync_imap_sync, config, credentials, cursor_value)
    except communication_adapters.CommunicationAdapterError:
        raise
    except (OSError, imaplib.IMAP4.error) as error:
        logger.exception("IMAP synchronization failed")
        raise communication_adapters.CommunicationAdapterError(
            "sync_failed",
            f"IMAP synchronization failed: {_error_detail(error)}",
        ) from error
    except Exception as error:
        logger.exception("Unexpected IMAP synchronization failure")
        raise communication_adapters.CommunicationAdapterError(
            "sync_failed",
            f"IMAP synchronization failed while processing mail: {type(error).__name__}.",
        ) from error


def _mark_imap_seen_sync(
    config: dict[str, object],
    credentials: dict[str, str],
    uid_value: str,
) -> None:
    client = communication_adapters._imap_connect(config, credentials)
    folder, uid = communication_adapters._imap_uid_parts(uid_value, str(config["folder"]))
    mailbox = ImapMailbox(folder, _quoted_mailbox(folder), 0)
    try:
        _select_mailbox(client, mailbox, readonly=False, required=True)
        status, data = client.uid("store", uid, "+FLAGS", "(\\Seen)")
        if status != "OK":
            detail = " ".join(
                item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
                for item in (data or [])
            ).strip()
            suffix = f": {detail[:300]}" if detail else ""
            raise communication_adapters.CommunicationAdapterError(
                "sync_failed",
                f"IMAP could not mark the message read{suffix}",
            )
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            client.shutdown()


async def mark_imap_seen(
    config: dict[str, object],
    credentials: dict[str, str],
    uid: str,
) -> None:
    try:
        await asyncio.to_thread(_mark_imap_seen_sync, config, credentials, uid)
    except communication_adapters.CommunicationAdapterError:
        raise
    except (OSError, imaplib.IMAP4.error) as error:
        logger.exception("IMAP mark-seen failed")
        raise communication_adapters.CommunicationAdapterError(
            "sync_failed",
            f"IMAP could not mark the message read: {_error_detail(error)}",
        ) from error


def install_imap_sync_patch() -> None:
    communication_adapters.sync_imap_account = sync_imap_account
    communication_adapters.mark_imap_seen = mark_imap_seen
    communication_service.sync_imap_account = sync_imap_account
    communication_service.mark_imap_seen = mark_imap_seen
