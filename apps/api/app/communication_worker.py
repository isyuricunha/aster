from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.communication_models import CommunicationAccount, CommunicationSourceCursor
from app.communication_runtime import install_communication_runtime
from app.communication_service import (
    CommunicationServiceError,
    record_sync_failure,
    sync_communication_account,
)
from app.communication_storage import CommunicationAttachmentStore
from app.config import Settings
from app.imap_sync_patch import imap_backfill_progress
from app.security import SecretCipher

_MAX_BACKFILL_BATCHES_PER_CLAIM = 10

install_communication_runtime()


async def claim_due_communication_account(
    session: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int,
) -> UUID | None:
    now = datetime.now(UTC)
    account = await session.scalar(
        select(CommunicationAccount)
        .where(
            CommunicationAccount.enabled.is_(True),
            or_(
                CommunicationAccount.next_sync_at.is_(None),
                CommunicationAccount.next_sync_at <= now,
            ),
            or_(
                CommunicationAccount.sync_lease_expires_at.is_(None),
                CommunicationAccount.sync_lease_expires_at <= now,
            ),
        )
        .order_by(CommunicationAccount.next_sync_at.asc().nullsfirst())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if account is None:
        return None
    account.sync_lease_owner = worker_id
    account.sync_lease_expires_at = now + timedelta(seconds=lease_seconds)
    account.next_sync_at = account.sync_lease_expires_at
    await session.commit()
    return account.id


async def _imap_backfill_pending(
    session: AsyncSession,
    account: CommunicationAccount,
) -> bool:
    if account.kind != "imap":
        return False
    folder = str(account.config.get("folder") or "INBOX")
    cursor_value = await session.scalar(
        select(CommunicationSourceCursor.cursor_value).where(
            CommunicationSourceCursor.account_id == account.id,
            CommunicationSourceCursor.source_key == f"imap:{folder}",
        )
    )
    pending, _ = imap_backfill_progress(cursor_value)
    return pending


async def sync_claimed_communication_account(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    account_id: UUID,
    worker_id: str,
    cipher: SecretCipher,
    store: CommunicationAttachmentStore,
    settings: Settings,
) -> tuple[int, int]:
    async with session_factory() as session:
        account = await session.get(CommunicationAccount, account_id)
        if account is None or account.sync_lease_owner != worker_id:
            return 0, 0
        messages_added = 0
        automations_enqueued = 0
        try:
            for _ in range(_MAX_BACKFILL_BATCHES_PER_CLAIM):
                added, enqueued = await sync_communication_account(
                    session,
                    account,
                    cipher=cipher,
                    store=store,
                    settings=settings,
                )
                messages_added += added
                automations_enqueued += enqueued
                if not await _imap_backfill_pending(session, account):
                    return messages_added, automations_enqueued

            account.next_sync_at = datetime.now(UTC)
            await session.commit()
            return messages_added, automations_enqueued
        except CommunicationServiceError as error:
            await record_sync_failure(session, account, error.message)
            return 0, 0
        except Exception as error:
            await record_sync_failure(
                session,
                account,
                "The communication account could not be synchronized.",
            )
            raise error


async def sync_due_communication_account(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    worker_id: str,
    cipher: SecretCipher,
    store: CommunicationAttachmentStore,
    settings: Settings,
) -> bool:
    async with session_factory() as session:
        account_id = await claim_due_communication_account(
            session,
            worker_id=worker_id,
            lease_seconds=settings.aster_communication_lease_seconds,
        )
    if account_id is None:
        return False
    await sync_claimed_communication_account(
        session_factory,
        account_id=account_id,
        worker_id=worker_id,
        cipher=cipher,
        store=store,
        settings=settings,
    )
    return True
