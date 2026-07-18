from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import Automation
from app.communication_models import (
    CommunicationAccount,
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationRule,
    CommunicationThread,
)
from app.communication_schemas import (
    CommunicationAccountCreate,
    CommunicationAccountResponse,
    CommunicationAccountTestResponse,
    CommunicationAccountUpdate,
    CommunicationMessageResponse,
    CommunicationReply,
    CommunicationRuleCreate,
    CommunicationRuleResponse,
    CommunicationRuleUpdate,
    CommunicationSyncResponse,
    CommunicationThreadDetail,
    CommunicationThreadResponse,
)
from app.communication_service import (
    CommunicationServiceError,
    communication_account_response,
    encrypted_communication_credentials,
    list_threads_query,
    mark_thread_read,
    message_response,
    reply_to_thread,
    rule_response,
    sync_communication_account,
    test_communication_account,
    thread_detail,
    validate_communication_config,
    validate_rule_targets,
)
from app.communication_storage import (
    CommunicationAttachmentStore,
    CommunicationStorageError,
)
from app.config import settings
from app.db import get_session
from app.dependencies import get_communication_store, get_secret_cipher
from app.integration_service import decrypt_credentials
from app.security import SecretCipher

router = APIRouter(prefix="/api", tags=["communications"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]
StoreDep = Annotated[CommunicationAttachmentStore, Depends(get_communication_store)]


async def _account(session: AsyncSession, account_id: UUID) -> CommunicationAccount:
    account = await session.get(CommunicationAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Communication account not found")
    return account


async def _thread(session: AsyncSession, thread_id: UUID) -> CommunicationThread:
    thread = await session.get(CommunicationThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Communication thread not found")
    return thread


async def _rule(session: AsyncSession, rule_id: UUID) -> CommunicationRule:
    rule = await session.get(CommunicationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Communication rule not found")
    return rule


@router.get(
    "/communication-accounts",
    response_model=list[CommunicationAccountResponse],
)
async def list_communication_accounts(
    session: SessionDep,
) -> list[CommunicationAccountResponse]:
    accounts = list(
        await session.scalars(
            select(CommunicationAccount).order_by(CommunicationAccount.name)
        )
    )
    return [communication_account_response(item) for item in accounts]


@router.post(
    "/communication-accounts",
    response_model=CommunicationAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_communication_account(
    payload: CommunicationAccountCreate,
    session: SessionDep,
    cipher: CipherDep,
) -> CommunicationAccountResponse:
    try:
        config = validate_communication_config(payload.kind, payload.config)
    except CommunicationServiceError as error:
        raise HTTPException(status_code=422, detail=error.message) from error
    account = CommunicationAccount(
        name=payload.name,
        kind=payload.kind,
        enabled=payload.enabled,
        config=config,
        encrypted_credentials=encrypted_communication_credentials(
            cipher, payload.credentials
        ),
        credential_names=sorted(payload.credentials),
        poll_interval_seconds=payload.poll_interval_seconds,
        next_sync_at=datetime.now(UTC) if payload.enabled else None,
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Communication account name already exists",
        ) from error
    await session.refresh(account)
    return communication_account_response(account)


@router.get(
    "/communication-accounts/{account_id}",
    response_model=CommunicationAccountResponse,
)
async def read_communication_account(
    account_id: UUID,
    session: SessionDep,
) -> CommunicationAccountResponse:
    return communication_account_response(await _account(session, account_id))


@router.put(
    "/communication-accounts/{account_id}",
    response_model=CommunicationAccountResponse,
)
async def update_communication_account(
    account_id: UUID,
    payload: CommunicationAccountUpdate,
    session: SessionDep,
    cipher: CipherDep,
) -> CommunicationAccountResponse:
    account = await _account(session, account_id)
    if payload.kind != account.kind:
        has_messages = await session.scalar(
            select(CommunicationMessage.id)
            .where(CommunicationMessage.account_id == account.id)
            .limit(1)
        )
        if has_messages is not None:
            raise HTTPException(
                status_code=409,
                detail="Delete the account history before changing its kind.",
            )
    try:
        config = validate_communication_config(payload.kind, payload.config)
    except CommunicationServiceError as error:
        raise HTTPException(status_code=422, detail=error.message) from error
    if payload.preserve_credentials and payload.kind == account.kind:
        credentials = decrypt_credentials(cipher, account.encrypted_credentials)
        credentials.update(payload.credentials)
    else:
        credentials = dict(payload.credentials)
    previous_enabled = account.enabled
    account.name = payload.name
    account.kind = payload.kind
    account.enabled = payload.enabled
    account.config = config
    account.encrypted_credentials = encrypted_communication_credentials(
        cipher, credentials
    )
    account.credential_names = sorted(credentials)
    account.poll_interval_seconds = payload.poll_interval_seconds
    account.last_sync_status = None
    account.last_error = None
    if payload.kind != account.kind:
        account.external_identity = {}
    if payload.enabled and not previous_enabled:
        account.next_sync_at = datetime.now(UTC)
    elif not payload.enabled:
        account.next_sync_at = None
        account.sync_lease_owner = None
        account.sync_lease_expires_at = None
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Communication account name already exists",
        ) from error
    await session.refresh(account)
    return communication_account_response(account)


@router.delete(
    "/communication-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_communication_account(
    account_id: UUID,
    session: SessionDep,
    store: StoreDep,
) -> Response:
    account = await _account(session, account_id)
    storage_keys = list(
        await session.scalars(
            select(CommunicationAttachment.storage_key)
            .join(
                CommunicationMessage,
                CommunicationMessage.id == CommunicationAttachment.message_id,
            )
            .where(CommunicationMessage.account_id == account.id)
        )
    )
    await session.delete(account)
    await session.commit()
    for storage_key in storage_keys:
        store.delete(storage_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/communication-accounts/{account_id}/test",
    response_model=CommunicationAccountTestResponse,
)
async def test_communication_account_route(
    account_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
) -> CommunicationAccountTestResponse:
    account = await _account(session, account_id)
    try:
        result = await test_communication_account(
            account,
            cipher=cipher,
            timeout_seconds=settings.aster_integration_timeout_seconds,
        )
    except CommunicationServiceError as error:
        account.last_sync_status = "failed"
        account.last_sync_at = datetime.now(UTC)
        account.last_error = error.message[:500]
        await session.commit()
        raise HTTPException(status_code=502, detail=error.message) from error
    account.external_identity = result.identity
    account.last_sync_status = "succeeded"
    account.last_sync_at = datetime.now(UTC)
    account.last_error = None
    await session.commit()
    return CommunicationAccountTestResponse(
        status="ok",
        message=result.message,
        identity=result.identity,
    )


@router.post(
    "/communication-accounts/{account_id}/sync",
    response_model=CommunicationSyncResponse,
)
async def sync_communication_account_route(
    account_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    store: StoreDep,
) -> CommunicationSyncResponse:
    account = await _account(session, account_id)
    try:
        added, enqueued = await sync_communication_account(
            session,
            account,
            cipher=cipher,
            store=store,
            settings=settings,
        )
    except CommunicationServiceError as error:
        account.last_sync_status = "failed"
        account.last_sync_at = datetime.now(UTC)
        account.last_error = error.message[:500]
        account.next_sync_at = datetime.now(UTC) + timedelta(
            seconds=account.poll_interval_seconds
        )
        await session.commit()
        raise HTTPException(status_code=502, detail=error.message) from error
    return CommunicationSyncResponse(
        status="ok",
        messages_added=added,
        automations_enqueued=enqueued,
    )


@router.get(
    "/communication-threads",
    response_model=list[CommunicationThreadResponse],
)
async def list_communication_threads(
    session: SessionDep,
    account_id: UUID | None = None,
    kind: str | None = None,
    unread_only: bool = False,
    query: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CommunicationThreadResponse]:
    if kind not in {None, "email", "discord"}:
        raise HTTPException(status_code=422, detail="Unsupported thread kind")
    return await list_threads_query(
        session,
        account_id=account_id,
        kind=kind,
        unread_only=unread_only,
        query=query.strip() if query and query.strip() else None,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/communication-threads/{thread_id}",
    response_model=CommunicationThreadDetail,
)
async def read_communication_thread(
    thread_id: UUID,
    session: SessionDep,
) -> CommunicationThreadDetail:
    thread = await _thread(session, thread_id)
    account = await _account(session, thread.account_id)
    return await thread_detail(session, thread, account.name)


@router.post(
    "/communication-threads/{thread_id}/read",
    response_model=CommunicationThreadDetail,
)
async def mark_communication_thread_read(
    thread_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
) -> CommunicationThreadDetail:
    thread = await _thread(session, thread_id)
    account = await _account(session, thread.account_id)
    await mark_thread_read(session, thread, account=account, cipher=cipher)
    await session.refresh(thread)
    return await thread_detail(session, thread, account.name)


@router.post(
    "/communication-threads/{thread_id}/reply",
    response_model=CommunicationMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reply_to_communication_thread(
    thread_id: UUID,
    payload: CommunicationReply,
    session: SessionDep,
    cipher: CipherDep,
) -> CommunicationMessageResponse:
    thread = await _thread(session, thread_id)
    account = await _account(session, thread.account_id)
    try:
        message = await reply_to_thread(
            session,
            thread=thread,
            account=account,
            content=payload.content,
            cipher=cipher,
            settings=settings,
        )
    except CommunicationServiceError as error:
        raise HTTPException(status_code=422, detail=error.message) from error
    return await message_response(session, message)


@router.get("/communication-attachments/{attachment_id}/content")
async def read_communication_attachment(
    attachment_id: UUID,
    session: SessionDep,
    store: StoreDep,
) -> Response:
    attachment = await session.get(CommunicationAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Communication attachment not found")
    try:
        content = store.read(attachment.storage_key)
    except CommunicationStorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    safe_name = attachment.filename.replace('"', "'")
    return Response(
        content=content,
        media_type=attachment.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/communication-rules",
    response_model=list[CommunicationRuleResponse],
)
async def list_communication_rules(
    session: SessionDep,
) -> list[CommunicationRuleResponse]:
    rules = list(
        await session.scalars(
            select(CommunicationRule).order_by(CommunicationRule.name)
        )
    )
    return [await rule_response(session, item) for item in rules]


@router.post(
    "/communication-rules",
    response_model=CommunicationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_communication_rule(
    payload: CommunicationRuleCreate,
    session: SessionDep,
) -> CommunicationRuleResponse:
    await validate_rule_targets(
        session,
        account_id=payload.account_id,
        automation_id=payload.automation_id,
    )
    rule = CommunicationRule(**payload.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return await rule_response(session, rule)


@router.put(
    "/communication-rules/{rule_id}",
    response_model=CommunicationRuleResponse,
)
async def update_communication_rule(
    rule_id: UUID,
    payload: CommunicationRuleUpdate,
    session: SessionDep,
) -> CommunicationRuleResponse:
    rule = await _rule(session, rule_id)
    await validate_rule_targets(
        session,
        account_id=payload.account_id,
        automation_id=payload.automation_id,
    )
    for name, value in payload.model_dump().items():
        setattr(rule, name, value)
    await session.commit()
    await session.refresh(rule)
    return await rule_response(session, rule)


@router.delete(
    "/communication-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_communication_rule(
    rule_id: UUID,
    session: SessionDep,
) -> Response:
    rule = await _rule(session, rule_id)
    await session.delete(rule)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/communication-summary")
async def communication_summary(session: SessionDep) -> dict[str, int]:
    return {
        "accounts": int(
            await session.scalar(select(func.count(CommunicationAccount.id))) or 0
        ),
        "threads": int(
            await session.scalar(select(func.count(CommunicationThread.id))) or 0
        ),
        "unread": int(
            await session.scalar(
                select(func.coalesce(func.sum(CommunicationThread.unread_count), 0))
            )
            or 0
        ),
        "rules": int(
            await session.scalar(select(func.count(CommunicationRule.id))) or 0
        ),
        "communication_automations": int(
            await session.scalar(
                select(func.count(Automation.id)).where(
                    Automation.trigger_type == "communication"
                )
            )
            or 0
        ),
    }
