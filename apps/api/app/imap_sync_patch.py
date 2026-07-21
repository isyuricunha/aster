import asyncio
import base64
import imaplib
import logging
import re
from dataclasses import dataclass

from app import communication_adapters, communication_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ImapMailbox:
    display_name: str
    select_name: str
    priority: int


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
    logger.warning("Skipping IMAP mailbox %s after SELECT returned %s", mailbox.display_name, status)
    return False


def _sync_imap_sync(
    config: dict[str, object],
    credentials: dict[str, str],
    cursor_value: str | None,
) -> communication_adapters.SourceSync:
    client = communication_adapters._imap_connect(config, credentials)
    fallback = str(config["folder"])
    limit = int(config.get("max_messages_per_sync", 50))
    cursors = communication_adapters._cursor_map(cursor_value, fallback)
    messages: list[communication_adapters.ReceivedMessage] = []
    try:
        mailboxes = _discover_mailboxes(client, fallback)
        per_mailbox_limit = max(1, limit // max(1, len(mailboxes)))
        for mailbox in mailboxes:
            required = mailbox.display_name.casefold() == fallback.casefold()
            if not _select_mailbox(client, mailbox, readonly=True, required=required):
                continue
            previous_uid = cursors.get(mailbox.display_name)
            criteria = f"UID {int(previous_uid) + 1}:*" if previous_uid else "ALL"
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
                continue
            if status != "OK":
                if required:
                    raise communication_adapters.CommunicationAdapterError(
                        "sync_failed",
                        f"IMAP search failed in {mailbox.display_name}.",
                    )
                continue
            raw_uids = data[0].split() if data and data[0] else []
            raw_uids = (
                raw_uids[:per_mailbox_limit]
                if previous_uid
                else raw_uids[-per_mailbox_limit:]
            )
            last_uid = previous_uid
            for raw_uid in raw_uids:
                uid = raw_uid.decode("ascii", errors="ignore")
                if not uid:
                    continue
                try:
                    status, fetched = client.uid("fetch", uid, "(RFC822 FLAGS)")
                except imaplib.IMAP4.error as error:
                    logger.warning(
                        "Skipping IMAP message %s/%s after FETCH failed: %s",
                        mailbox.display_name,
                        uid,
                        _error_detail(error),
                    )
                    continue
                if status != "OK" or not fetched:
                    continue
                raw_message = next(
                    (
                        item[1]
                        for item in fetched
                        if isinstance(item, tuple) and isinstance(item[1], bytes)
                    ),
                    None,
                )
                if raw_message is None:
                    continue
                flags = " ".join(
                    item[0].decode("utf-8", errors="replace")
                    for item in fetched
                    if isinstance(item, tuple) and isinstance(item[0], bytes)
                )
                messages.append(
                    communication_adapters._parse_imap_message(
                        raw_message,
                        uid=uid,
                        folder=mailbox.display_name,
                        flags=flags,
                    )
                )
                last_uid = uid
            if last_uid:
                cursors[mailbox.display_name] = last_uid
        messages.sort(key=lambda message: message.sent_at)
        return communication_adapters.SourceSync(
            source_key=f"imap:{fallback}",
            cursor_value=communication_adapters.json.dumps(
                cursors,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            messages=tuple(messages),
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
) -> communication_adapters.SourceSync:
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
