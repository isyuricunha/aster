import asyncio
import base64
import imaplib
import json
import re
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import httpx


class CommunicationAdapterError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ReceivedAttachment:
    external_id: str | None
    filename: str
    media_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ReceivedMessage:
    external_message_id: str
    external_thread_id: str
    source_id: str
    sender_name: str | None
    sender_address: str | None
    recipients: list[dict[str, str]]
    subject: str | None
    content_text: str
    content_html: str | None
    metadata: dict[str, object]
    sent_at: datetime
    is_read: bool
    attachments: tuple[ReceivedAttachment, ...]


@dataclass(frozen=True, slots=True)
class SourceSync:
    source_key: str
    cursor_value: str | None
    messages: tuple[ReceivedMessage, ...]


@dataclass(frozen=True, slots=True)
class AccountTestResult:
    message: str
    identity: dict[str, object]


@dataclass(frozen=True, slots=True)
class DiscordSendResult:
    external_message_id: str
    sent_at: datetime
    metadata: dict[str, object]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for item, encoding in decode_header(value):
        if isinstance(item, bytes):
            parts.append(item.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(item)
    return "".join(parts).strip()


def _message_datetime(message: Message) -> datetime:
    try:
        parsed = parsedate_to_datetime(message.get("Date"))
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _decoded_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _email_content(
    message: Message,
) -> tuple[str, str | None, tuple[ReceivedAttachment, ...]]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[ReceivedAttachment] = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        filename = _decode_header(part.get_filename())
        media_type = part.get_content_type() or "application/octet-stream"
        if disposition == "attachment" or filename:
            data = part.get_payload(decode=True)
            if isinstance(data, bytes) and data:
                attachments.append(
                    ReceivedAttachment(
                        external_id=part.get("Content-ID") or f"part-{index}",
                        filename=filename or f"attachment-{index}",
                        media_type=media_type,
                        data=data,
                    )
                )
            continue
        if media_type == "text/plain":
            plain_parts.append(_decoded_payload(part))
        elif media_type == "text/html":
            html_parts.append(_decoded_payload(part))
    html = "\n".join(item for item in html_parts if item.strip()).strip() or None
    text = "\n".join(item for item in plain_parts if item.strip()).strip()
    if not text and html:
        parser = _TextExtractor()
        parser.feed(html)
        text = parser.text()
    return text, html, tuple(attachments)


def _normalized_subject(subject: str) -> str:
    value = subject.strip()
    while True:
        next_value = re.sub(
            r"^(re|fw|fwd)\s*:\s*",
            "",
            value,
            flags=re.IGNORECASE,
        )
        if next_value == value:
            return value.casefold()
        value = next_value


def _email_thread_id(message: Message, subject: str, fallback: str) -> str:
    references = str(message.get("References") or "").split()
    if references:
        return f"email:{references[0][:480]}"
    in_reply_to = str(message.get("In-Reply-To") or "").strip()
    if in_reply_to:
        return f"email:{in_reply_to[:480]}"
    normalized = _normalized_subject(subject)
    if normalized:
        return f"email-subject:{normalized[:470]}"
    return f"email:{fallback[:480]}"


def _imap_connect(
    config: dict[str, object],
    credentials: dict[str, str],
) -> imaplib.IMAP4:
    host = str(config["host"])
    port = int(config["port"])
    security = str(config["security"])
    timeout = min(float(config.get("timeout_seconds", 30)), 120.0)
    if security == "ssl":
        client: imaplib.IMAP4 = imaplib.IMAP4_SSL(
            host,
            port,
            ssl_context=ssl.create_default_context(),
            timeout=timeout,
        )
    else:
        client = imaplib.IMAP4(host, port, timeout=timeout)
        if security == "starttls":
            client.starttls(ssl_context=ssl.create_default_context())
    username = credentials.get("username")
    password = credentials.get("password")
    if not username:
        raise CommunicationAdapterError(
            "invalid_credentials",
            "IMAP username is required.",
        )
    client.login(username, password or "")
    return client


def _decode_modified_utf7(value: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(value):
        marker = value.find("&", index)
        if marker < 0:
            parts.append(value[index:])
            break
        parts.append(value[index:marker])
        end = value.find("-", marker)
        if end < 0:
            parts.append(value[marker:])
            break
        encoded = value[marker + 1 : end]
        if not encoded:
            parts.append("&")
        else:
            padded = encoded.replace(",", "/")
            padded += "=" * (-len(padded) % 4)
            try:
                parts.append(base64.b64decode(padded).decode("utf-16-be"))
            except (ValueError, UnicodeDecodeError):
                parts.append(value[marker : end + 1])
        index = end + 1
    return "".join(parts)


def _mailbox_flags(raw: bytes) -> set[bytes]:
    match = re.match(rb"^\((?P<flags>[^)]*)\)", raw)
    if match is None:
        return set()
    return {flag.casefold() for flag in match.group("flags").split()}


def _mailbox_name(raw: bytes) -> str | None:
    match = re.match(
        rb'^\((?P<flags>[^)]*)\)\s+(?:NIL|"(?:\\.|[^"])*")\s+(?P<name>.+)$',
        raw,
    )
    if match is None:
        return None
    name = match.group("name").strip()
    if name.startswith(b'"') and name.endswith(b'"'):
        name = name[1:-1].replace(b'\\"', b'"').replace(b"\\\\", b"\\")
    return _decode_modified_utf7(name.decode("ascii", errors="replace")).strip()


def _mailbox_priority(raw: bytes, name: str, fallback: str) -> int:
    flags = _mailbox_flags(raw)
    if name.casefold() == fallback.casefold() or b"\\inbox" in flags:
        return 0
    order = (
        (b"\\sent", 1),
        (b"\\drafts", 2),
        (b"\\archive", 3),
        (b"\\junk", 4),
        (b"\\trash", 5),
    )
    for flag, priority in order:
        if flag in flags:
            return priority
    normalized = name.casefold()
    if "sent" in normalized or "enviad" in normalized:
        return 6
    if "draft" in normalized or "rascunh" in normalized:
        return 7
    if "archive" in normalized or "arquivo" in normalized:
        return 8
    if "spam" in normalized or "junk" in normalized or "indesejad" in normalized:
        return 9
    if "trash" in normalized or "deleted" in normalized or "lixeira" in normalized:
        return 10
    return 20


def _selectable_mailboxes(client: imaplib.IMAP4, fallback: str) -> list[str]:
    status, data = client.list()
    if status != "OK" or not data:
        return [fallback]
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, bytes):
            continue
        flags = _mailbox_flags(item)
        if b"\\noselect" in flags or b"\\all" in flags:
            continue
        name = _mailbox_name(item)
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        found.append((_mailbox_priority(item, name, fallback), name))
    if fallback.casefold() not in seen:
        found.append((0, fallback))
    found.sort(key=lambda item: (item[0], item[1].casefold()))
    return [name for _, name in found[:50]] or [fallback]


def _cursor_map(cursor_value: str | None, fallback: str) -> dict[str, str]:
    if not cursor_value:
        return {}
    if cursor_value.isdigit():
        return {fallback: cursor_value}
    try:
        value = json.loads(cursor_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        str(folder): str(uid)
        for folder, uid in value.items()
        if str(folder).strip() and str(uid).isdigit()
    }


def _test_imap_sync(
    config: dict[str, object],
    credentials: dict[str, str],
) -> AccountTestResult:
    client = _imap_connect(config, credentials)
    folder = str(config["folder"])
    try:
        status, data = client.select(folder, readonly=True)
        if status != "OK":
            raise CommunicationAdapterError(
                "connection_failed",
                f"IMAP could not open {folder}.",
            )
        count = int(data[0]) if data and data[0] else 0
        mailboxes = _selectable_mailboxes(client, folder)
        return AccountTestResult(
            message=f"IMAP connection succeeded with {len(mailboxes)} selectable mailbox(es).",
            identity={
                "username": credentials.get("username", ""),
                "folder": folder,
                "mailboxes": mailboxes,
                "message_count": count,
            },
        )
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            client.shutdown()


def _parse_imap_message(
    raw: bytes,
    *,
    uid: str,
    folder: str,
    flags: str,
) -> ReceivedMessage:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    subject = _decode_header(message.get("Subject"))
    sender_name, sender_address = parseaddr(str(message.get("From") or ""))
    sender_name = _decode_header(sender_name) or None
    sender_address = sender_address.strip() or None
    recipient_values = [str(message.get(header) or "") for header in ("To", "Cc")]
    recipients = [
        {"name": _decode_header(name), "address": address}
        for name, address in getaddresses(recipient_values)
        if address
    ]
    content_text, content_html, attachments = _email_content(message)
    header_message_id = str(message.get("Message-ID") or "").strip()
    folder_key = folder.casefold()
    base_message_id = header_message_id or f"imap:{uid}"
    external_message_id = f"imap:{folder_key}:{base_message_id}"
    thread_id = _email_thread_id(message, subject, base_message_id)
    return ReceivedMessage(
        external_message_id=external_message_id[:512],
        external_thread_id=f"{thread_id}:{folder_key}"[:512],
        source_id=folder,
        sender_name=sender_name,
        sender_address=sender_address,
        recipients=recipients,
        subject=subject or None,
        content_text=content_text,
        content_html=content_html,
        metadata={
            "imap_uid": json.dumps({"folder": folder, "uid": uid}, separators=(",", ":")),
            "folder": folder,
            "flags": flags,
            "message_id_header": header_message_id,
            "in_reply_to": str(message.get("In-Reply-To") or ""),
            "references": str(message.get("References") or ""),
        },
        sent_at=_message_datetime(message),
        is_read="\\Seen" in flags,
        attachments=attachments,
    )


def _sync_imap_sync(
    config: dict[str, object],
    credentials: dict[str, str],
    cursor_value: str | None,
) -> SourceSync:
    client = _imap_connect(config, credentials)
    fallback = str(config["folder"])
    limit = int(config.get("max_messages_per_sync", 50))
    cursors = _cursor_map(cursor_value, fallback)
    messages: list[ReceivedMessage] = []
    try:
        folders = _selectable_mailboxes(client, fallback)
        per_folder_limit = max(1, limit // max(1, len(folders)))
        for folder in folders:
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                if folder == fallback:
                    raise CommunicationAdapterError(
                        "sync_failed",
                        f"IMAP could not open {folder}.",
                    )
                continue
            previous_uid = cursors.get(folder)
            criteria = f"UID {int(previous_uid) + 1}:*" if previous_uid else "ALL"
            status, data = client.uid("search", None, criteria)
            if status != "OK":
                if folder == fallback:
                    raise CommunicationAdapterError("sync_failed", "IMAP search failed.")
                continue
            raw_uids = data[0].split() if data and data[0] else []
            raw_uids = raw_uids[:per_folder_limit] if previous_uid else raw_uids[-per_folder_limit:]
            last_uid = previous_uid
            for raw_uid in raw_uids:
                uid = raw_uid.decode("ascii", errors="ignore")
                if not uid:
                    continue
                status, fetched = client.uid("fetch", uid, "(RFC822 FLAGS)")
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
                    _parse_imap_message(
                        raw_message,
                        uid=uid,
                        folder=folder,
                        flags=flags,
                    )
                )
                last_uid = uid
            if last_uid:
                cursors[folder] = last_uid
        messages.sort(key=lambda message: message.sent_at)
        return SourceSync(
            source_key=f"imap:{fallback}",
            cursor_value=json.dumps(cursors, ensure_ascii=False, separators=(",", ":")),
            messages=tuple(messages),
        )
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            client.shutdown()


def _imap_uid_parts(value: str, fallback: str) -> tuple[str, str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return fallback, value
    if not isinstance(payload, dict):
        return fallback, value
    folder = payload.get("folder")
    uid = payload.get("uid")
    if isinstance(folder, str) and isinstance(uid, str) and uid.isdigit():
        return folder, uid
    return fallback, value


def _mark_imap_seen_sync(
    config: dict[str, object],
    credentials: dict[str, str],
    uid_value: str,
) -> None:
    client = _imap_connect(config, credentials)
    folder, uid = _imap_uid_parts(uid_value, str(config["folder"]))
    try:
        status, _ = client.select(folder, readonly=False)
        if status != "OK":
            raise CommunicationAdapterError(
                "sync_failed",
                f"IMAP could not open {folder}.",
            )
        status, _ = client.uid("store", uid, "+FLAGS", "(\\Seen)")
        if status != "OK":
            raise CommunicationAdapterError(
                "sync_failed",
                "IMAP could not mark the message read.",
            )
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            client.shutdown()


async def test_imap_account(
    config: dict[str, object],
    credentials: dict[str, str],
) -> AccountTestResult:
    try:
        return await asyncio.to_thread(_test_imap_sync, config, credentials)
    except CommunicationAdapterError:
        raise
    except (OSError, imaplib.IMAP4.error) as error:
        raise CommunicationAdapterError(
            "connection_failed",
            "The IMAP account could not be reached.",
        ) from error


async def sync_imap_account(
    config: dict[str, object],
    credentials: dict[str, str],
    cursor_value: str | None,
) -> SourceSync:
    try:
        return await asyncio.to_thread(
            _sync_imap_sync,
            config,
            credentials,
            cursor_value,
        )
    except CommunicationAdapterError:
        raise
    except (OSError, imaplib.IMAP4.error) as error:
        raise CommunicationAdapterError(
            "sync_failed",
            "The IMAP account could not be synchronized.",
        ) from error


async def mark_imap_seen(
    config: dict[str, object],
    credentials: dict[str, str],
    uid: str,
) -> None:
    try:
        await asyncio.to_thread(
            _mark_imap_seen_sync,
            config,
            credentials,
            uid,
        )
    except CommunicationAdapterError:
        raise
    except (OSError, imaplib.IMAP4.error) as error:
        raise CommunicationAdapterError(
            "sync_failed",
            "The IMAP message could not be marked read.",
        ) from error


def _discord_headers(credentials: dict[str, str]) -> dict[str, str]:
    token = credentials.get("token")
    if not token:
        raise CommunicationAdapterError(
            "invalid_credentials",
            "Discord bot token is required.",
        )
    return {
        "Authorization": f"Bot {token}",
        "Accept": "application/json",
        "User-Agent": "Aster/0.1 Communication Hub",
    }


def _discord_api_base(config: dict[str, object]) -> str:
    return str(config.get("api_base_url", "https://discord.com/api/v10")).rstrip("/")


def _discord_datetime(value: object) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


async def test_discord_account(
    config: dict[str, object],
    credentials: dict[str, str],
    *,
    timeout_seconds: float,
) -> AccountTestResult:
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{_discord_api_base(config)}/users/@me",
                headers=_discord_headers(credentials),
            )
        if response.status_code >= 400:
            raise CommunicationAdapterError(
                "connection_failed",
                f"Discord returned HTTP {response.status_code}.",
            )
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise CommunicationAdapterError(
                "invalid_response",
                "Discord returned an invalid bot identity.",
            )
        username = str(payload.get("username") or "Discord bot")
        return AccountTestResult(
            message=f"Discord connection succeeded as {username}.",
            identity={
                "id": payload["id"],
                "username": username,
                "global_name": payload.get("global_name"),
            },
        )
    except CommunicationAdapterError:
        raise
    except (httpx.HTTPError, ValueError) as error:
        raise CommunicationAdapterError(
            "connection_failed",
            "The Discord account could not be reached.",
        ) from error


async def _download_discord_attachment(
    client: httpx.AsyncClient,
    item: dict[str, Any],
    *,
    max_bytes: int,
) -> ReceivedAttachment | None:
    url = item.get("url")
    if not isinstance(url, str):
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    declared_size = item.get("size")
    if isinstance(declared_size, int) and declared_size > max_bytes:
        return None
    response = await client.get(url)
    if response.status_code >= 400 or len(response.content) > max_bytes:
        return None
    return ReceivedAttachment(
        external_id=str(item.get("id")) if item.get("id") is not None else None,
        filename=str(item.get("filename") or "attachment"),
        media_type=str(item.get("content_type") or "application/octet-stream"),
        data=response.content,
    )


async def sync_discord_account(
    config: dict[str, object],
    credentials: dict[str, str],
    cursors: dict[str, str | None],
    identity: dict[str, object],
    *,
    timeout_seconds: float,
    max_attachment_bytes: int,
) -> list[SourceSync]:
    channel_ids = [str(item) for item in config.get("channel_ids", [])]
    limit = int(config.get("max_messages_per_sync", 50))
    labels = config.get("channel_labels", {})
    label_map = labels if isinstance(labels, dict) else {}
    bot_id = str(identity.get("id") or "")
    results: list[SourceSync] = []
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as client:
            for channel_id in channel_ids:
                source_key = f"discord:{channel_id}"
                cursor = cursors.get(source_key)
                params: dict[str, object] = {"limit": min(limit, 100)}
                if cursor:
                    params["after"] = cursor
                response = await client.get(
                    f"{_discord_api_base(config)}/channels/{channel_id}/messages",
                    params=params,
                    headers=_discord_headers(credentials),
                )
                if response.status_code >= 400:
                    raise CommunicationAdapterError(
                        "sync_failed",
                        f"Discord channel {channel_id} returned HTTP {response.status_code}.",
                    )
                payload = response.json()
                if not isinstance(payload, list):
                    raise CommunicationAdapterError(
                        "invalid_response",
                        "Discord returned an invalid message list.",
                    )
                ordered = sorted(
                    (item for item in payload if isinstance(item, dict)),
                    key=lambda item: int(str(item.get("id") or "0")),
                )
                messages: list[ReceivedMessage] = []
                next_cursor = cursor
                for item in ordered:
                    message_id = str(item.get("id") or "")
                    author = item.get("author")
                    if not message_id or not isinstance(author, dict):
                        continue
                    author_id = str(author.get("id") or "")
                    if author_id and author_id == bot_id:
                        next_cursor = message_id
                        continue
                    raw_attachments = item.get("attachments")
                    attachments: list[ReceivedAttachment] = []
                    if isinstance(raw_attachments, list):
                        for attachment in raw_attachments[:16]:
                            if not isinstance(attachment, dict):
                                continue
                            downloaded = await _download_discord_attachment(
                                client,
                                attachment,
                                max_bytes=max_attachment_bytes,
                            )
                            if downloaded is not None:
                                attachments.append(downloaded)
                    mentions = item.get("mentions")
                    mention_ids = (
                        [
                            str(mention.get("id"))
                            for mention in mentions
                            if isinstance(mention, dict) and mention.get("id") is not None
                        ]
                        if isinstance(mentions, list)
                        else []
                    )
                    recipients = (
                        [
                            {
                                "name": str(mention.get("username") or ""),
                                "address": str(mention.get("id")),
                            }
                            for mention in mentions
                            if isinstance(mention, dict) and mention.get("id") is not None
                        ]
                        if isinstance(mentions, list)
                        else []
                    )
                    reply_reference = item.get("message_reference")
                    thread_id = str(item.get("channel_id") or channel_id)
                    title = str(label_map.get(channel_id) or f"Discord channel {channel_id}")
                    author_name = str(
                        author.get("global_name")
                        or author.get("username")
                        or "Discord user"
                    )
                    messages.append(
                        ReceivedMessage(
                            external_message_id=f"discord:{message_id}",
                            external_thread_id=f"discord:{thread_id}",
                            source_id=channel_id,
                            sender_name=author_name,
                            sender_address=author_id or None,
                            recipients=recipients,
                            subject=title,
                            content_text=str(item.get("content") or ""),
                            content_html=None,
                            metadata={
                                "discord_message_id": message_id,
                                "channel_id": channel_id,
                                "guild_id": item.get("guild_id"),
                                "author_is_bot": bool(author.get("bot")),
                                "mentioned_bot": bool(bot_id and bot_id in mention_ids),
                                "message_reference": (
                                    reply_reference if isinstance(reply_reference, dict) else None
                                ),
                            },
                            sent_at=_discord_datetime(item.get("timestamp")),
                            is_read=False,
                            attachments=tuple(attachments),
                        )
                    )
                    next_cursor = message_id
                results.append(
                    SourceSync(
                        source_key=source_key,
                        cursor_value=next_cursor,
                        messages=tuple(messages),
                    )
                )
        return results
    except CommunicationAdapterError:
        raise
    except (httpx.HTTPError, ValueError) as error:
        raise CommunicationAdapterError(
            "sync_failed",
            "The Discord account could not be synchronized.",
        ) from error


async def send_discord_reply(
    config: dict[str, object],
    credentials: dict[str, str],
    *,
    channel_id: str,
    reply_to_message_id: str | None,
    content: str,
    timeout_seconds: float,
) -> DiscordSendResult:
    payload: dict[str, object] = {
        "content": content,
        "allowed_mentions": {"parse": []},
    }
    if reply_to_message_id:
        payload["message_reference"] = {
            "message_id": reply_to_message_id,
            "channel_id": channel_id,
            "fail_if_not_exists": False,
        }
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.post(
                f"{_discord_api_base(config)}/channels/{channel_id}/messages",
                headers=_discord_headers(credentials),
                json=payload,
            )
        if response.status_code >= 400:
            raise CommunicationAdapterError(
                "delivery_failed",
                f"Discord returned HTTP {response.status_code}.",
            )
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("id"), str):
            raise CommunicationAdapterError(
                "invalid_response",
                "Discord returned an invalid sent message.",
            )
        return DiscordSendResult(
            external_message_id=f"discord:{body['id']}",
            sent_at=_discord_datetime(body.get("timestamp")),
            metadata={
                "discord_message_id": body["id"],
                "channel_id": channel_id,
                "allowed_mentions": {"parse": []},
            },
        )
    except CommunicationAdapterError:
        raise
    except (httpx.HTTPError, ValueError) as error:
        raise CommunicationAdapterError(
            "delivery_failed",
            "The Discord reply could not be sent.",
        ) from error
