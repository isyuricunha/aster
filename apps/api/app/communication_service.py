import fnmatch
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import Automation, IntegrationConnection
from app.automation_queue import enqueue_run
from app.communication_adapters import (
    AccountTestResult,
    CommunicationAdapterError,
    ReceivedMessage,
    mark_imap_seen,
    send_discord_reply,
    sync_discord_account,
    sync_imap_account,
    test_discord_account,
    test_imap_account,
)
from app.communication_models import (
    CommunicationAccount,
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationRule,
    CommunicationSourceCursor,
    CommunicationThread,
)
from app.communication_schemas import (
    CommunicationAccountResponse,
    CommunicationAttachmentResponse,
    CommunicationMessageResponse,
    CommunicationRuleResponse,
    CommunicationThreadDetail,
    CommunicationThreadResponse,
)
from app.communication_storage import (
    CommunicationAttachmentStore,
    CommunicationStorageError,
)
from app.config import Settings
from app.integration_service import (
    IntegrationError,
    decrypt_credentials,
    deliver_email,
    encrypt_credentials,
)
from app.security import SecretCipher


class CommunicationServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def validate_communication_config(
    kind: str,
    config: dict[str, object],
) -> dict[str, object]:
    normalized = dict(config)
    if kind == "imap":
        return _validate_imap_config(normalized)
    if kind == "discord":
        return _validate_discord_config(normalized)
    raise CommunicationServiceError(
        "invalid_configuration",
        "Unsupported communication kind.",
    )


def _validate_imap_config(config: dict[str, object]) -> dict[str, object]:
    host = config.get("host")
    port = config.get("port", 993)
    security = config.get("security", "ssl")
    folder = config.get("folder", "INBOX")
    max_messages = config.get("max_messages_per_sync", 50)
    timeout = config.get("timeout_seconds", 30)
    if not isinstance(host, str) or not host.strip():
        raise CommunicationServiceError(
            "invalid_configuration",
            "IMAP host is required.",
        )
    if (
        not isinstance(port, int)
        or isinstance(port, bool)
        or not 1 <= port <= 65_535
    ):
        raise CommunicationServiceError(
            "invalid_configuration",
            "IMAP port is invalid.",
        )
    if security not in {"plain", "starttls", "ssl"}:
        raise CommunicationServiceError(
            "invalid_configuration",
            "IMAP security is invalid.",
        )
    if not isinstance(folder, str) or not folder.strip():
        raise CommunicationServiceError(
            "invalid_configuration",
            "IMAP folder is required.",
        )
    if (
        not isinstance(max_messages, int)
        or isinstance(max_messages, bool)
        or not 1 <= max_messages <= 500
    ):
        raise CommunicationServiceError(
            "invalid_configuration",
            "IMAP max_messages_per_sync is invalid.",
        )
    if (
        not isinstance(timeout, int | float)
        or isinstance(timeout, bool)
        or not 1 <= timeout <= 120
    ):
        raise CommunicationServiceError(
            "invalid_configuration",
            "IMAP timeout_seconds is invalid.",
        )
    smtp_id = config.get("smtp_integration_id")
    if smtp_id not in {None, ""}:
        try:
            smtp_id = str(UUID(str(smtp_id)))
        except ValueError as error:
            raise CommunicationServiceError(
                "invalid_configuration",
                "smtp_integration_id is invalid.",
            ) from error
    else:
        smtp_id = None
    return {
        **config,
        "host": host.strip(),
        "port": port,
        "security": security,
        "folder": folder.strip(),
        "max_messages_per_sync": max_messages,
        "timeout_seconds": float(timeout),
        "mark_seen_on_read": bool(config.get("mark_seen_on_read", True)),
        "smtp_integration_id": smtp_id,
    }


def _validate_discord_config(config: dict[str, object]) -> dict[str, object]:
    raw_url = config.get("api_base_url", "https://discord.com/api/v10")
    parsed = urlsplit(str(raw_url))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CommunicationServiceError(
            "invalid_configuration",
            "Discord api_base_url must use HTTP or HTTPS.",
        )
    raw_channels = config.get("channel_ids", [])
    if not isinstance(raw_channels, list):
        raise CommunicationServiceError(
            "invalid_configuration",
            "Discord channel_ids must be a list.",
        )
    channel_ids = [str(item).strip() for item in raw_channels if str(item).strip()]
    if (
        not channel_ids
        or len(channel_ids) > 100
        or len(channel_ids) != len(set(channel_ids))
    ):
        raise CommunicationServiceError(
            "invalid_configuration",
            "Discord requires between 1 and 100 unique channel IDs.",
        )
    raw_labels = config.get("channel_labels", {})
    if not isinstance(raw_labels, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in raw_labels.items()
    ):
        raise CommunicationServiceError(
            "invalid_configuration",
            "Discord channel_labels must be a string map.",
        )
    max_messages = config.get("max_messages_per_sync", 50)
    if (
        not isinstance(max_messages, int)
        or isinstance(max_messages, bool)
        or not 1 <= max_messages <= 100
    ):
        raise CommunicationServiceError(
            "invalid_configuration",
            "Discord max_messages_per_sync is invalid.",
        )
    labels = {
        key.strip(): value.strip()[:500]
        for key, value in raw_labels.items()
        if key.strip() and value.strip()
    }
    return {
        **config,
        "api_base_url": str(raw_url).rstrip("/"),
        "channel_ids": channel_ids,
        "channel_labels": labels,
        "max_messages_per_sync": max_messages,
    }


def communication_account_response(
    account: CommunicationAccount,
) -> CommunicationAccountResponse:
    return CommunicationAccountResponse.model_validate(account)


async def test_communication_account(
    account: CommunicationAccount,
    *,
    cipher: SecretCipher,
    timeout_seconds: float,
) -> AccountTestResult:
    config = validate_communication_config(account.kind, account.config)
    credentials = decrypt_credentials(cipher, account.encrypted_credentials)
    try:
        if account.kind == "imap":
            return await test_imap_account(config, credentials)
        return await test_discord_account(
            config,
            credentials,
            timeout_seconds=timeout_seconds,
        )
    except CommunicationAdapterError as error:
        raise CommunicationServiceError(error.code, error.message) from error


async def _source_cursors(
    session: AsyncSession,
    account_id: UUID,
) -> dict[str, CommunicationSourceCursor]:
    rows = list(
        await session.scalars(
            select(CommunicationSourceCursor).where(
                CommunicationSourceCursor.account_id == account_id
            )
        )
    )
    return {row.source_key: row for row in rows}


def _participant_key(participant: dict[str, str]) -> str:
    return (
        participant.get("address")
        or participant.get("name")
        or ""
    ).casefold()


def _merge_participants(
    current: list[dict[str, str]],
    received: ReceivedMessage,
) -> list[dict[str, str]]:
    candidates = list(current)
    if received.sender_address or received.sender_name:
        candidates.append(
            {
                "name": received.sender_name or "",
                "address": received.sender_address or "",
            }
        )
    candidates.extend(received.recipients)
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = _participant_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "name": str(candidate.get("name") or "")[:300],
                "address": str(candidate.get("address") or "")[:512],
            }
        )
    return result[:100]


async def _store_attachment(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    message: CommunicationMessage,
    attachment: object,
    store: CommunicationAttachmentStore,
    settings: Settings,
) -> str | None:
    data = getattr(attachment, "data", None)
    if not isinstance(data, bytes):
        return None
    try:
        stored = store.write(
            account_id=str(account.id),
            message_id=str(message.id),
            filename=str(getattr(attachment, "filename", "attachment")),
            media_type=str(
                getattr(
                    attachment,
                    "media_type",
                    "application/octet-stream",
                )
            ),
            data=data,
            max_bytes=settings.aster_communication_attachment_max_bytes,
        )
    except CommunicationStorageError:
        return None
    session.add(
        CommunicationAttachment(
            message_id=message.id,
            external_attachment_id=getattr(
                attachment,
                "external_id",
                None,
            ),
            filename=stored.filename,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            storage_key=stored.storage_key,
        )
    )
    return stored.storage_key


async def _persist_received_message(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    received: ReceivedMessage,
    store: CommunicationAttachmentStore,
    settings: Settings,
) -> tuple[CommunicationMessage | None, list[str]]:
    existing_id = await session.scalar(
        select(CommunicationMessage.id).where(
            CommunicationMessage.account_id == account.id,
            CommunicationMessage.external_message_id
            == received.external_message_id,
        )
    )
    if existing_id is not None:
        return None, []
    thread = await session.scalar(
        select(CommunicationThread).where(
            CommunicationThread.account_id == account.id,
            CommunicationThread.external_thread_id
            == received.external_thread_id,
        )
    )
    kind = "email" if account.kind == "imap" else "discord"
    if thread is None:
        thread = CommunicationThread(
            account_id=account.id,
            kind=kind,
            external_thread_id=received.external_thread_id,
            title=(received.subject or "Untitled conversation")[:500],
            participants=[],
            metadata={"source_id": received.source_id},
            unread_count=0,
            last_message_at=received.sent_at,
        )
        session.add(thread)
        await session.flush()
    thread.title = (received.subject or thread.title)[:500]
    thread.participants = _merge_participants(thread.participants, received)
    thread.last_message_at = max(
        _aware(thread.last_message_at),
        _aware(received.sent_at),
    )
    if not received.is_read:
        thread.unread_count += 1
    message = CommunicationMessage(
        account_id=account.id,
        thread_id=thread.id,
        external_message_id=received.external_message_id,
        direction="inbound",
        source_id=received.source_id,
        sender_name=received.sender_name,
        sender_address=received.sender_address,
        recipients=received.recipients,
        subject=received.subject,
        content_text=received.content_text[
            : settings.aster_communication_message_max_characters
        ],
        content_html=(
            received.content_html[
                : settings.aster_communication_message_max_characters
            ]
            if received.content_html
            else None
        ),
        metadata=received.metadata,
        is_read=received.is_read,
        sent_at=received.sent_at,
        received_at=datetime.now(UTC),
    )
    session.add(message)
    await session.flush()
    storage_keys: list[str] = []
    attachment_limit = settings.aster_communication_max_attachments
    for attachment in received.attachments[:attachment_limit]:
        storage_key = await _store_attachment(
            session,
            account=account,
            message=message,
            attachment=attachment,
            store=store,
            settings=settings,
        )
        if storage_key:
            storage_keys.append(storage_key)
    return message, storage_keys


def _rule_matches(
    rule: CommunicationRule,
    message: CommunicationMessage,
) -> bool:
    sender = (
        message.sender_address
        or message.sender_name
        or ""
    ).casefold()
    if rule.sender_pattern and not fnmatch.fnmatchcase(
        sender,
        rule.sender_pattern.casefold(),
    ):
        return False
    if rule.source_ids:
        candidates = {
            value.casefold()
            for value in (message.source_id, message.sender_address)
            if value
        }
        allowed = {item.casefold() for item in rule.source_ids}
        if not candidates.intersection(allowed):
            return False
    if (
        rule.body_contains
        and rule.body_contains.casefold()
        not in message.content_text.casefold()
    ):
        return False
    if rule.require_mention and not bool(
        message.metadata.get("mentioned_bot")
    ):
        return False
    return True


def _automation_payload(
    account: CommunicationAccount,
    thread: CommunicationThread,
    message: CommunicationMessage,
    attachments: list[CommunicationAttachment],
) -> dict[str, object]:
    return {
        "type": "communication.message.received",
        "account": {
            "id": str(account.id),
            "name": account.name,
            "kind": account.kind,
        },
        "thread": {
            "id": str(thread.id),
            "title": thread.title,
            "kind": thread.kind,
        },
        "message": {
            "id": str(message.id),
            "source_id": message.source_id,
            "sender_name": message.sender_name,
            "sender_address": message.sender_address,
            "subject": message.subject,
            "content": message.content_text,
            "sent_at": message.sent_at.isoformat(),
            "attachments": [
                {
                    "id": str(attachment.id),
                    "filename": attachment.filename,
                    "media_type": attachment.media_type,
                    "size_bytes": attachment.size_bytes,
                }
                for attachment in attachments
            ],
        },
    }


async def _enqueue_matching_automations(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    message: CommunicationMessage,
) -> int:
    rows = (
        await session.execute(
            select(CommunicationRule, Automation)
            .join(
                Automation,
                Automation.id == CommunicationRule.automation_id,
            )
            .where(
                CommunicationRule.account_id == account.id,
                CommunicationRule.enabled.is_(True),
                Automation.enabled.is_(True),
                Automation.trigger_type == "communication",
            )
        )
    ).all()
    if not rows:
        return 0
    thread = await session.get(CommunicationThread, message.thread_id)
    if thread is None:
        return 0
    attachments = list(
        await session.scalars(
            select(CommunicationAttachment).where(
                CommunicationAttachment.message_id == message.id
            )
        )
    )
    trigger_payload = _automation_payload(
        account,
        thread,
        message,
        attachments,
    )
    count = 0
    for rule, automation in rows:
        if not _rule_matches(rule, message):
            continue
        run = await enqueue_run(
            session,
            automation,
            trigger_source="communication",
            occurrence_key=(
                f"communication:{message.id}:{automation.id}"
            ),
            scheduled_for=message.received_at,
            trigger_payload=trigger_payload,
        )
        if run is not None:
            count += 1
    return count


async def _fetch_sources(
    account: CommunicationAccount,
    *,
    config: dict[str, object],
    credentials: dict[str, str],
    cursors: dict[str, CommunicationSourceCursor],
    settings: Settings,
) -> list[object]:
    if account.kind == "imap":
        source_key = f"imap:{config['folder']}"
        cursor = cursors.get(source_key)
        return [
            await sync_imap_account(
                config,
                credentials,
                cursor.cursor_value if cursor else None,
            )
        ]
    return await sync_discord_account(
        config,
        credentials,
        {
            key: cursor.cursor_value
            for key, cursor in cursors.items()
        },
        account.external_identity,
        timeout_seconds=settings.aster_integration_timeout_seconds,
        max_attachment_bytes=(
            settings.aster_communication_attachment_max_bytes
        ),
    )


async def sync_communication_account(
    session: AsyncSession,
    account: CommunicationAccount,
    *,
    cipher: SecretCipher,
    store: CommunicationAttachmentStore,
    settings: Settings,
) -> tuple[int, int]:
    config = validate_communication_config(account.kind, account.config)
    credentials = decrypt_credentials(cipher, account.encrypted_credentials)
    cursors = await _source_cursors(session, account.id)
    try:
        sources = await _fetch_sources(
            account,
            config=config,
            credentials=credentials,
            cursors=cursors,
            settings=settings,
        )
    except CommunicationAdapterError as error:
        raise CommunicationServiceError(error.code, error.message) from error

    messages_added = 0
    automations_enqueued = 0
    written_storage_keys: list[str] = []
    try:
        for source in sources:
            source_key = str(getattr(source, "source_key"))
            cursor = cursors.get(source_key)
            if cursor is None:
                cursor = CommunicationSourceCursor(
                    account_id=account.id,
                    source_key=source_key,
                )
                session.add(cursor)
                cursors[source_key] = cursor
            for received in getattr(source, "messages"):
                message, storage_keys = await _persist_received_message(
                    session,
                    account=account,
                    received=received,
                    store=store,
                    settings=settings,
                )
                written_storage_keys.extend(storage_keys)
                if message is None:
                    continue
                messages_added += 1
                automations_enqueued += await _enqueue_matching_automations(
                    session,
                    account=account,
                    message=message,
                )
            cursor.cursor_value = getattr(source, "cursor_value")
        now = datetime.now(UTC)
        account.last_sync_status = "succeeded"
        account.last_sync_at = now
        account.last_error = None
        account.next_sync_at = now + timedelta(
            seconds=account.poll_interval_seconds
        )
        account.sync_lease_owner = None
        account.sync_lease_expires_at = None
        await session.commit()
        return messages_added, automations_enqueued
    except Exception:
        await session.rollback()
        for storage_key in written_storage_keys:
            store.delete(storage_key)
        raise


async def record_sync_failure(
    session: AsyncSession,
    account: CommunicationAccount,
    message: str,
) -> None:
    now = datetime.now(UTC)
    account.last_sync_status = "failed"
    account.last_sync_at = now
    account.last_error = message[:500]
    account.next_sync_at = now + timedelta(
        seconds=account.poll_interval_seconds
    )
    account.sync_lease_owner = None
    account.sync_lease_expires_at = None
    await session.commit()


def attachment_response(
    attachment: CommunicationAttachment,
) -> CommunicationAttachmentResponse:
    return CommunicationAttachmentResponse(
        id=attachment.id,
        filename=attachment.filename,
        media_type=attachment.media_type,
        size_bytes=attachment.size_bytes,
        sha256=attachment.sha256,
        content_path=(
            f"/api/communication-attachments/{attachment.id}/content"
        ),
    )


async def message_response(
    session: AsyncSession,
    message: CommunicationMessage,
) -> CommunicationMessageResponse:
    attachments = list(
        await session.scalars(
            select(CommunicationAttachment)
            .where(CommunicationAttachment.message_id == message.id)
            .order_by(CommunicationAttachment.created_at)
        )
    )
    return CommunicationMessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        account_id=message.account_id,
        external_message_id=message.external_message_id,
        direction=message.direction,
        source_id=message.source_id,
        sender_name=message.sender_name,
        sender_address=message.sender_address,
        recipients=message.recipients,
        subject=message.subject,
        content_text=message.content_text,
        content_html=message.content_html,
        metadata=message.metadata,
        is_read=message.is_read,
        sent_at=message.sent_at,
        received_at=message.received_at,
        attachments=[
            attachment_response(attachment)
            for attachment in attachments
        ],
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


async def thread_response(
    session: AsyncSession,
    thread: CommunicationThread,
    account_name: str,
) -> CommunicationThreadResponse:
    message_count = int(
        await session.scalar(
            select(func.count(CommunicationMessage.id)).where(
                CommunicationMessage.thread_id == thread.id
            )
        )
        or 0
    )
    latest = await session.scalar(
        select(CommunicationMessage)
        .where(CommunicationMessage.thread_id == thread.id)
        .order_by(CommunicationMessage.sent_at.desc())
        .limit(1)
    )
    preview = " ".join(
        (latest.content_text if latest else "").split()
    )[:240]
    return CommunicationThreadResponse(
        id=thread.id,
        account_id=thread.account_id,
        account_name=account_name,
        kind=thread.kind,
        external_thread_id=thread.external_thread_id,
        title=thread.title,
        participants=thread.participants,
        metadata=thread.metadata,
        unread_count=thread.unread_count,
        last_message_at=thread.last_message_at,
        message_count=message_count,
        preview=preview,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


async def thread_detail(
    session: AsyncSession,
    thread: CommunicationThread,
    account_name: str,
) -> CommunicationThreadDetail:
    summary = await thread_response(session, thread, account_name)
    messages = list(
        await session.scalars(
            select(CommunicationMessage)
            .where(CommunicationMessage.thread_id == thread.id)
            .order_by(CommunicationMessage.sent_at)
        )
    )
    return CommunicationThreadDetail(
        **summary.model_dump(),
        messages=[
            await message_response(session, message)
            for message in messages
        ],
    )


async def rule_response(
    session: AsyncSession,
    rule: CommunicationRule,
) -> CommunicationRuleResponse:
    account = await session.get(CommunicationAccount, rule.account_id)
    automation = await session.get(Automation, rule.automation_id)
    return CommunicationRuleResponse(
        id=rule.id,
        name=rule.name,
        account_id=rule.account_id,
        account_name=account.name if account else "Deleted account",
        automation_id=rule.automation_id,
        automation_name=(
            automation.name if automation else "Deleted automation"
        ),
        enabled=rule.enabled,
        sender_pattern=rule.sender_pattern,
        source_ids=rule.source_ids,
        body_contains=rule.body_contains,
        require_mention=rule.require_mention,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


async def mark_thread_read(
    session: AsyncSession,
    thread: CommunicationThread,
    *,
    account: CommunicationAccount,
    cipher: SecretCipher,
) -> None:
    unread = list(
        await session.scalars(
            select(CommunicationMessage).where(
                CommunicationMessage.thread_id == thread.id,
                CommunicationMessage.is_read.is_(False),
            )
        )
    )
    if (
        account.kind == "imap"
        and account.config.get("mark_seen_on_read", True)
    ):
        credentials = decrypt_credentials(
            cipher,
            account.encrypted_credentials,
        )
        config = validate_communication_config(
            account.kind,
            account.config,
        )
        for message in unread:
            uid = message.metadata.get("imap_uid")
            if not isinstance(uid, str):
                continue
            try:
                await mark_imap_seen(config, credentials, uid)
            except CommunicationAdapterError:
                break
    for message in unread:
        message.is_read = True
    thread.unread_count = 0
    await session.commit()


async def _persist_outbound_message(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    thread: CommunicationThread,
    external_message_id: str,
    source_id: str | None,
    sender_name: str | None,
    sender_address: str | None,
    recipients: list[dict[str, str]],
    subject: str | None,
    content: str,
    metadata: dict[str, object],
    sent_at: datetime,
) -> CommunicationMessage:
    message = CommunicationMessage(
        account_id=account.id,
        thread_id=thread.id,
        external_message_id=external_message_id[:512],
        direction="outbound",
        source_id=source_id,
        sender_name=sender_name,
        sender_address=sender_address,
        recipients=recipients,
        subject=subject,
        content_text=content,
        content_html=None,
        metadata=metadata,
        is_read=True,
        sent_at=sent_at,
        received_at=datetime.now(UTC),
    )
    session.add(message)
    thread.last_message_at = max(
        _aware(thread.last_message_at),
        _aware(sent_at),
    )
    await session.commit()
    await session.refresh(message)
    return message


async def reply_to_thread(
    session: AsyncSession,
    *,
    thread: CommunicationThread,
    account: CommunicationAccount,
    content: str,
    cipher: SecretCipher,
    settings: Settings,
) -> CommunicationMessage:
    latest = await session.scalar(
        select(CommunicationMessage)
        .where(
            CommunicationMessage.thread_id == thread.id,
            CommunicationMessage.direction == "inbound",
        )
        .order_by(CommunicationMessage.sent_at.desc())
        .limit(1)
    )
    if latest is None:
        raise CommunicationServiceError(
            "reply_unavailable",
            "This thread does not have an inbound message to reply to.",
        )
    credentials = decrypt_credentials(
        cipher,
        account.encrypted_credentials,
    )
    config = validate_communication_config(
        account.kind,
        account.config,
    )
    if account.kind == "imap":
        return await _reply_to_email(
            session,
            account=account,
            thread=thread,
            latest=latest,
            content=content,
            cipher=cipher,
            config=config,
        )
    return await _reply_to_discord(
        session,
        account=account,
        thread=thread,
        latest=latest,
        content=content,
        credentials=credentials,
        config=config,
        settings=settings,
    )


async def _reply_to_email(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    thread: CommunicationThread,
    latest: CommunicationMessage,
    content: str,
    cipher: SecretCipher,
    config: dict[str, object],
) -> CommunicationMessage:
    integration_value = config.get("smtp_integration_id")
    if not integration_value:
        raise CommunicationServiceError(
            "reply_unavailable",
            "Configure an SMTP integration for this IMAP account.",
        )
    integration = await session.get(
        IntegrationConnection,
        UUID(str(integration_value)),
    )
    if (
        integration is None
        or integration.kind != "smtp"
        or not integration.enabled
    ):
        raise CommunicationServiceError(
            "reply_unavailable",
            "The configured SMTP integration is unavailable.",
        )
    recipient = latest.sender_address
    if not recipient:
        raise CommunicationServiceError(
            "reply_unavailable",
            "The inbound email does not have a reply address.",
        )
    subject = latest.subject or thread.title
    if not subject.casefold().startswith("re:"):
        subject = f"Re: {subject}"
    headers: dict[str, str] = {}
    message_id_header = latest.metadata.get("message_id_header")
    if isinstance(message_id_header, str) and message_id_header:
        headers["In-Reply-To"] = message_id_header
        references = latest.metadata.get("references")
        headers["References"] = (
            f"{references} {message_id_header}".strip()
            if isinstance(references, str)
            else message_id_header
        )
    try:
        await deliver_email(
            integration,
            cipher=cipher,
            recipients=[recipient],
            subject=subject,
            body=content,
            headers=headers,
        )
    except IntegrationError as error:
        raise CommunicationServiceError(error.code, error.message) from error
    return await _persist_outbound_message(
        session,
        account=account,
        thread=thread,
        external_message_id=f"outbound-email:{uuid4()}",
        source_id=latest.source_id,
        sender_name=account.name,
        sender_address=None,
        recipients=[
            {
                "name": latest.sender_name or "",
                "address": recipient,
            }
        ],
        subject=subject,
        content=content,
        metadata={"reply_to_message_id": str(latest.id)},
        sent_at=datetime.now(UTC),
    )


async def _reply_to_discord(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    thread: CommunicationThread,
    latest: CommunicationMessage,
    content: str,
    credentials: dict[str, str],
    config: dict[str, object],
    settings: Settings,
) -> CommunicationMessage:
    channel_id = latest.source_id
    if not channel_id:
        raise CommunicationServiceError(
            "reply_unavailable",
            "The Discord thread does not have a channel ID.",
        )
    raw_message_id = latest.metadata.get("discord_message_id")
    try:
        result = await send_discord_reply(
            config,
            credentials,
            channel_id=channel_id,
            reply_to_message_id=(
                str(raw_message_id) if raw_message_id else None
            ),
            content=content,
            timeout_seconds=(
                settings.aster_integration_timeout_seconds
            ),
        )
    except CommunicationAdapterError as error:
        raise CommunicationServiceError(error.code, error.message) from error
    identity = account.external_identity
    return await _persist_outbound_message(
        session,
        account=account,
        thread=thread,
        external_message_id=result.external_message_id,
        source_id=channel_id,
        sender_name=str(identity.get("username") or account.name),
        sender_address=str(identity.get("id") or "") or None,
        recipients=[],
        subject=thread.title,
        content=content,
        metadata=result.metadata,
        sent_at=result.sent_at,
    )


async def list_threads_query(
    session: AsyncSession,
    *,
    account_id: UUID | None,
    kind: str | None,
    unread_only: bool,
    query: str | None,
    offset: int,
    limit: int,
) -> list[CommunicationThreadResponse]:
    statement = select(
        CommunicationThread,
        CommunicationAccount.name,
    ).join(
        CommunicationAccount,
        CommunicationAccount.id == CommunicationThread.account_id,
    )
    if account_id is not None:
        statement = statement.where(
            CommunicationThread.account_id == account_id
        )
    if kind is not None:
        statement = statement.where(
            CommunicationThread.kind == kind
        )
    if unread_only:
        statement = statement.where(
            CommunicationThread.unread_count > 0
        )
    if query:
        pattern = f"%{query}%"
        matching_threads = select(
            CommunicationMessage.thread_id
        ).where(
            or_(
                CommunicationMessage.content_text.ilike(pattern),
                CommunicationMessage.sender_address.ilike(pattern),
                CommunicationMessage.sender_name.ilike(pattern),
            )
        )
        statement = statement.where(
            or_(
                CommunicationThread.title.ilike(pattern),
                CommunicationThread.id.in_(matching_threads),
            )
        )
    rows = (
        await session.execute(
            statement.order_by(
                CommunicationThread.last_message_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [
        await thread_response(session, thread, account_name)
        for thread, account_name in rows
    ]


async def validate_rule_targets(
    session: AsyncSession,
    *,
    account_id: UUID,
    automation_id: UUID,
) -> None:
    if await session.get(CommunicationAccount, account_id) is None:
        raise HTTPException(
            status_code=422,
            detail="The communication account does not exist.",
        )
    automation = await session.get(Automation, automation_id)
    if automation is None:
        raise HTTPException(
            status_code=422,
            detail="The automation does not exist.",
        )
    if automation.trigger_type != "communication":
        raise HTTPException(
            status_code=422,
            detail=(
                "Communication rules require an automation with "
                "a communication trigger."
            ),
        )


def encrypted_communication_credentials(
    cipher: SecretCipher,
    values: dict[str, str],
) -> str | None:
    return encrypt_credentials(cipher, values)
