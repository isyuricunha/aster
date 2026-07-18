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
    SourceSync,
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


def validate_communication_config(
    kind: str,
    config: dict[str, object],
) -> dict[str, object]:
    normalized = dict(config)
    if kind == "imap":
        host = normalized.get("host")
        port = normalized.get("port", 993)
        security = normalized.get("security", "ssl")
        folder = normalized.get("folder", "INBOX")
        max_messages = normalized.get("max_messages_per_sync", 50)
        timeout = normalized.get("timeout_seconds", 30)
        if not isinstance(host, str) or not host.strip():
            raise CommunicationServiceError("invalid_configuration", "IMAP host is required.")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65_535:
            raise CommunicationServiceError("invalid_configuration", "IMAP port is invalid.")
        if security not in {"plain", "starttls", "ssl"}:
            raise CommunicationServiceError("invalid_configuration", "IMAP security is invalid.")
        if not isinstance(folder, str) or not folder.strip():
            raise CommunicationServiceError("invalid_configuration", "IMAP folder is required.")
        if (
            not isinstance(max_messages, int)
            or isinstance(max_messages, bool)
            or not 1 <= max_messages <= 500
        ):
            raise CommunicationServiceError(
                "invalid_configuration", "IMAP max_messages_per_sync is invalid."
            )
        if not isinstance(timeout, int | float) or isinstance(timeout, bool) or not 1 <= timeout <= 120:
            raise CommunicationServiceError(
                "invalid_configuration", "IMAP timeout_seconds is invalid."
            )
        smtp_id = normalized.get("smtp_integration_id")
        if smtp_id not in {None, ""}:
            try:
                normalized["smtp_integration_id"] = str(UUID(str(smtp_id)))
            except ValueError as error:
                raise CommunicationServiceError(
                    "invalid_configuration", "smtp_integration_id is invalid."
                ) from error
        else:
            normalized["smtp_integration_id"] = None
        normalized.update(
            host=host.strip(),
            port=port,
            security=security,
            folder=folder.strip(),
            max_messages_per_sync=max_messages,
            timeout_seconds=float(timeout),
            mark_seen_on_read=bool(normalized.get("mark_seen_on_read", True)),
        )
        return normalized
    if kind == "discord":
        raw_url = normalized.get("api_base_url", "https://discord.com/api/v10")
        parsed = urlsplit(str(raw_url))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CommunicationServiceError(
                "invalid_configuration", "Discord api_base_url must use HTTP or HTTPS."
            )
        raw_channels = normalized.get("channel_ids", [])
        if not isinstance(raw_channels, list):
            raise CommunicationServiceError(
                "invalid_configuration", "Discord channel_ids must be a list."
            )
        channel_ids = [str(item).strip() for item in raw_channels if str(item).strip()]
        if not channel_ids or len(channel_ids) > 100 or len(channel_ids) != len(set(channel_ids)):
            raise CommunicationServiceError(
                "invalid_configuration",
                "Discord requires between 1 and 100 unique channel IDs.",
            )
        raw_labels = normalized.get("channel_labels", {})
        if not isinstance(raw_labels, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in raw_labels.items()
        ):
            raise CommunicationServiceError(
                "invalid_configuration", "Discord channel_labels must be a string map."
            )
        max_messages = normalized.get("max_messages_per_sync", 50)
        if (
            not isinstance(max_messages, int)
            or isinstance(max_messages, bool)
            or not 1 <= max_messages <= 100
        ):
            raise CommunicationServiceError(
                "invalid_configuration", "Discord max_messages_per_sync is invalid."
            )
        normalized.update(
            api_base_url=str(raw_url).rstrip("/"),
            channel_ids=channel_ids,
            channel_labels={
                key.strip(): value.strip()[:500]
                for key, value in raw_labels.items()
                if key.strip() and value.strip()
            },
            max_messages_per_sync=max_messages,
        )
        return normalized
    raise CommunicationServiceError("invalid_configuration", "Unsupported communication kind.")


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
    items = list(
        await session.scalars(
            select(CommunicationSourceCursor).where(
                CommunicationSourceCursor.account_id == account_id
            )
        )
    )
    return {item.source_key: item for item in items}


def _participant_key(item: dict[str, str]) -> str:
    return (item.get("address") or item.get("name") or "").casefold()


def _merge_participants(
    current: list[dict[str, str]],
    message: ReceivedMessage,
) -> list[dict[str, str]]:
    values = list(current)
    if message.sender_address or message.sender_name:
        values.append(
            {
                "name": message.sender_name or "",
                "address": message.sender_address or "",
            }
        )
    values.extend(message.recipients)
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        key = _participant_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(
            {
                "name": str(value.get("name") or "")[:300],
                "address": str(value.get("address") or "")[:512],
            }
        )
    return merged[:100]


async def _persist_attachment(
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
                getattr(attachment, "media_type", "application/octet-stream")
            ),
            data=data,
            max_bytes=settings.aster_communication_attachment_max_bytes,
        )
    except CommunicationStorageError:
        return None
    session.add(
        CommunicationAttachment(
            message_id=message.id,
            external_attachment_id=getattr(attachment, "external_id", None),
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
    existing = await session.scalar(
        select(CommunicationMessage.id).where(
            CommunicationMessage.account_id == account.id,
            CommunicationMessage.external_message_id == received.external_message_id,
        )
    )
    if existing is not None:
        return None, []
    thread = await session.scalar(
        select(CommunicationThread).where(
            CommunicationThread.account_id == account.id,
            CommunicationThread.external_thread_id == received.external_thread_id,
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
    thread.last_message_at = max(thread.last_message_at, received.sent_at)
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
            received.content_html[: settings.aster_communication_message_max_characters]
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
    for attachment in received.attachments[: settings.aster_communication_max_attachments]:
        storage_key = await _persist_attachment(
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


def _rule_matches(rule: CommunicationRule, message: CommunicationMessage) -> bool:
    sender = (message.sender_address or message.sender_name or "").casefold()
    if rule.sender_pattern and not fnmatch.fnmatchcase(
        sender, rule.sender_pattern.casefold()
    ):
        return False
    if rule.source_ids:
        candidates = {
            value.casefold()
            for value in (message.source_id, message.sender_address)
            if value
        }
        if not candidates.intersection(item.casefold() for item in rule.source_ids):
            return False
    if rule.body_contains and rule.body_contains.casefold() not in message.content_text.casefold():
        return False
    if rule.require_mention and not bool(message.metadata.get("mentioned_bot")):
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
                    "id": str(item.id),
                    "filename": item.filename,
                    "media_type": item.media_type,
                    "size_bytes": item.size_bytes,
                }
                for item in attachments
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
            .join(Automation, Automation.id == CommunicationRule.automation_id)
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
    payload = _automation_payload(account, thread, message, attachments)
    count = 0
    for rule, automation in rows:
        if not _rule_matches(rule, message):
            continue
        run = await enqueue_run(
            session,
            automation,
            trigger_source="communication",
            occurrence_key=f"communication:{message.id}:{automation.id}",
            scheduled_for=message.received_at,
            trigger_payload=payload,
        )
        if run is not None:
            count += 1
    return count


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
        if account.kind == "imap":
            key = f"imap:{config['folder']}"
            current = cursors.get(key)
            sources = [
                await sync_imap_account(
                    config,
                    credentials,
                    current.cursor_value if current else None,
                )
            ]
        else:
            sources = await sync_discord_account(
                config,
                credentials,
                {key: value.cursor_value for key, value in cursors.items()},
                account.external_identity,
                timeout_seconds=settings.aster_integration_timeout_seconds,
                max_attachment_bytes=settings.aster_communication_attachment_max_bytes,
            )
    except CommunicationAdapterError as error:
        raise CommunicationServiceError(error.code, error.message) from error

    messages_added = 0
    automations_enqueued = 0
    written_storage_keys: list[str] = []
    try:
        for source in sources:
            cursor = cursors.get(source.source_key)
            if cursor is None:
                cursor = CommunicationSourceCursor(
                    account_id=account.id,
                    source_key=source.source_key,
                )
                session.add(cursor)
                cursors[source.source_key] = cursor
            for received in source.messages:
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
            cursor.cursor_value = source.cursor_value
        now = datetime.now(UTC)
        account.last_sync_status = "succeeded"
        account.last_sync_at = now
        account.last_error = None
        account.next_sync_at = now + timedelta(seconds=account.poll_interval_seconds)
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
    account.next_sync_at = now + timedelta(seconds=account.poll_interval_seconds)
    account.sync_lease_owner = None
    account.sync_lease_expires_at = None
    await session.commit()


async def attachment_response(
    attachment: CommunicationAttachment,
) -> CommunicationAttachmentResponse:
    return CommunicationAttachmentResponse(
        id=attachment.id,
        filename=attachment.filename,
        media_type=attachment.media_type,
        size_bytes=attachment.size_bytes,
        sha256=attachment.sha256,
        content_path=f"/api/communication-attachments/{attachment.id}/content",
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
        attachments=[await attachment_response(item) for item in attachments],
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
    preview = " ".join((latest.content_text if latest else "").split())[:240]
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
        messages=[await message_response(session, item) for item in messages],
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
        automation_name=automation.name if automation else "Deleted automation",
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
    if account.kind == "imap" and account.config.get("mark_seen_on_read", True):
        credentials = decrypt_credentials(cipher, account.encrypted_credentials)
        config = validate_communication_config(account.kind, account.config)
        for message in unread:
            uid = message.metadata.get("imap_uid")
            if isinstance(uid, str):
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
    thread.last_message_at = max(thread.last_message_at, sent_at)
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
    latest_inbound = await session.scalar(
        select(CommunicationMessage)
        .where(
            CommunicationMessage.thread_id == thread.id,
            CommunicationMessage.direction == "inbound",
        )
        .order_by(CommunicationMessage.sent_at.desc())
        .limit(1)
    )
    if latest_inbound is None:
        raise CommunicationServiceError(
            "reply_unavailable", "This thread does not have an inbound message to reply to."
        )
    credentials = decrypt_credentials(cipher, account.encrypted_credentials)
    config = validate_communication_config(account.kind, account.config)
    if account.kind == "imap":
        integration_value = config.get("smtp_integration_id")
        if not integration_value:
            raise CommunicationServiceError(
                "reply_unavailable", "Configure an SMTP integration for this IMAP account."
            )
        integration = await session.get(IntegrationConnection, UUID(str(integration_value)))
        if integration is None or integration.kind != "smtp" or not integration.enabled:
            raise CommunicationServiceError(
                "reply_unavailable", "The configured SMTP integration is unavailable."
            )
        recipient = latest_inbound.sender_address
        if not recipient:
            raise CommunicationServiceError(
                "reply_unavailable", "The inbound email does not have a reply address."
            )
        subject = latest_inbound.subject or thread.title
        if not subject.casefold().startswith("re:"):
            subject = f"Re: {subject}"
        headers: dict[str, str] = {}
        message_id_header = latest_inbound.metadata.get("message_id_header")
        if isinstance(message_id_header, str) and message_id_header:
            headers["In-Reply-To"] = message_id_header
            references = latest_inbound.metadata.get("references")
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
            source_id=latest_inbound.source_id,
            sender_name=account.name,
            sender_address=None,
            recipients=[{"name": latest_inbound.sender_name or "", "address": recipient}],
            subject=subject,
            content=content,
            metadata={"reply_to_message_id": str(latest_inbound.id)},
            sent_at=datetime.now(UTC),
        )
    channel_id = latest_inbound.source_id
    if not channel_id:
        raise CommunicationServiceError(
            "reply_unavailable", "The Discord thread does not have a channel ID."
        )
    raw_message_id = latest_inbound.metadata.get("discord_message_id")
    result = await send_discord_reply(
        config,
        credentials,
        channel_id=channel_id,
        reply_to_message_id=str(raw_message_id) if raw_message_id else None,
        content=content,
        timeout_seconds=settings.aster_integration_timeout_seconds,
    )
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
    statement = select(CommunicationThread, CommunicationAccount.name).join(
        CommunicationAccount,
        CommunicationAccount.id == CommunicationThread.account_id,
    )
    if account_id is not None:
        statement = statement.where(CommunicationThread.account_id == account_id)
    if kind is not None:
        statement = statement.where(CommunicationThread.kind == kind)
    if unread_only:
        statement = statement.where(CommunicationThread.unread_count > 0)
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                CommunicationThread.title.ilike(pattern),
                CommunicationThread.id.in_(
                    select(CommunicationMessage.thread_id).where(
                        or_(
                            CommunicationMessage.content_text.ilike(pattern),
                            CommunicationMessage.sender_address.ilike(pattern),
                            CommunicationMessage.sender_name.ilike(pattern),
                        )
                    )
                ),
            )
        )
    rows = (
        await session.execute(
            statement.order_by(CommunicationThread.last_message_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [await thread_response(session, thread, name) for thread, name in rows]


async def validate_rule_targets(
    session: AsyncSession,
    *,
    account_id: UUID,
    automation_id: UUID,
) -> None:
    if await session.get(CommunicationAccount, account_id) is None:
        raise HTTPException(status_code=422, detail="The communication account does not exist.")
    automation = await session.get(Automation, automation_id)
    if automation is None:
        raise HTTPException(status_code=422, detail="The automation does not exist.")
    if automation.trigger_type != "communication":
        raise HTTPException(
            status_code=422,
            detail="Communication rules require an automation with a communication trigger.",
        )


def encrypted_communication_credentials(
    cipher: SecretCipher,
    values: dict[str, str],
) -> str | None:
    return encrypt_credentials(cipher, values)
