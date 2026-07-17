from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import (
    Automation,
    AutomationDelivery,
    AutomationRun,
    IntegrationConnection,
    Notification,
)
from app.automation_schemas import (
    AutomationCreate,
    AutomationResponse,
    AutomationRunResponse,
    AutomationUpdate,
    IntegrationConnectionCreate,
    IntegrationConnectionResponse,
    IntegrationConnectionUpdate,
    IntegrationTestResponse,
    NotificationListResponse,
    NotificationResponse,
    WebhookAcceptedResponse,
)
from app.automation_service import (
    accept_webhook,
    apply_automation_write,
    automation_response,
    enqueue_manual_run,
    enqueue_run,
    integration_response,
    new_webhook_token,
    hash_webhook_token,
    run_response,
    unread_notification_count,
)
from app.config import settings
from app.db import get_session
from app.dependencies import get_secret_cipher
from app.integration_service import (
    IntegrationError,
    encrypt_credentials,
    test_integration,
    validate_integration_config,
)
from app.security import SecretCipher

private_router = APIRouter(prefix="/api", tags=["automations"])
public_router = APIRouter(prefix="/api", tags=["webhooks"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]


async def _get_integration(session: AsyncSession, integration_id: UUID) -> IntegrationConnection:
    integration = await session.get(IntegrationConnection, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


async def _get_automation(session: AsyncSession, automation_id: UUID) -> Automation:
    automation = await session.get(Automation, automation_id)
    if automation is None:
        raise HTTPException(status_code=404, detail="Automation not found")
    return automation


async def _get_run(session: AsyncSession, run_id: UUID) -> AutomationRun:
    run = await session.get(AutomationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Automation run not found")
    return run


@private_router.get("/integrations", response_model=list[IntegrationConnectionResponse])
async def list_integrations(session: SessionDep) -> list[IntegrationConnectionResponse]:
    items = list(
        await session.scalars(select(IntegrationConnection).order_by(IntegrationConnection.name))
    )
    return [integration_response(item) for item in items]


@private_router.post(
    "/integrations",
    response_model=IntegrationConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_integration(
    payload: IntegrationConnectionCreate,
    session: SessionDep,
    cipher: CipherDep,
) -> IntegrationConnectionResponse:
    try:
        config = validate_integration_config(payload.kind, payload.config)
    except IntegrationError as error:
        raise HTTPException(status_code=422, detail=error.message) from error
    integration = IntegrationConnection(
        name=payload.name,
        kind=payload.kind,
        enabled=payload.enabled,
        config=config,
        encrypted_credentials=encrypt_credentials(cipher, payload.credentials),
        credential_names=sorted(payload.credentials),
    )
    session.add(integration)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Integration name already exists") from error
    await session.refresh(integration)
    return integration_response(integration)


@private_router.get(
    "/integrations/{integration_id}", response_model=IntegrationConnectionResponse
)
async def read_integration(
    integration_id: UUID, session: SessionDep
) -> IntegrationConnectionResponse:
    return integration_response(await _get_integration(session, integration_id))


@private_router.put(
    "/integrations/{integration_id}", response_model=IntegrationConnectionResponse
)
async def update_integration(
    integration_id: UUID,
    payload: IntegrationConnectionUpdate,
    session: SessionDep,
    cipher: CipherDep,
) -> IntegrationConnectionResponse:
    integration = await _get_integration(session, integration_id)
    try:
        config = validate_integration_config(payload.kind, payload.config)
    except IntegrationError as error:
        raise HTTPException(status_code=422, detail=error.message) from error
    integration.name = payload.name
    integration.kind = payload.kind
    integration.enabled = payload.enabled
    integration.config = config
    if payload.credentials or not payload.preserve_credentials:
        integration.encrypted_credentials = encrypt_credentials(cipher, payload.credentials)
        integration.credential_names = sorted(payload.credentials)
    integration.last_test_status = None
    integration.last_error = None
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Integration name already exists") from error
    await session.refresh(integration)
    return integration_response(integration)


@private_router.delete(
    "/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_integration(integration_id: UUID, session: SessionDep) -> Response:
    integration = await _get_integration(session, integration_id)
    referenced = await session.scalar(
        select(AutomationDelivery.id)
        .where(AutomationDelivery.integration_id == integration.id)
        .limit(1)
    )
    if referenced is not None:
        raise HTTPException(
            status_code=409,
            detail="Remove this integration from its automations before deleting it.",
        )
    await session.delete(integration)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@private_router.post(
    "/integrations/{integration_id}/test", response_model=IntegrationTestResponse
)
async def test_integration_route(
    integration_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
) -> IntegrationTestResponse:
    integration = await _get_integration(session, integration_id)
    tested_at = datetime.now(UTC)
    try:
        message = await test_integration(
            integration,
            cipher=cipher,
            timeout_seconds=settings.aster_integration_timeout_seconds,
        )
    except IntegrationError as error:
        integration.last_test_status = "failed"
        integration.last_test_at = tested_at
        integration.last_error = error.message[:500]
        await session.commit()
        raise HTTPException(status_code=502, detail=error.message) from error
    integration.last_test_status = "succeeded"
    integration.last_test_at = tested_at
    integration.last_error = None
    await session.commit()
    return IntegrationTestResponse(status="ok", message=message)


@private_router.get("/automations", response_model=list[AutomationResponse])
async def list_automations(session: SessionDep) -> list[AutomationResponse]:
    items = list(await session.scalars(select(Automation).order_by(Automation.name)))
    return [await automation_response(session, item) for item in items]


@private_router.post(
    "/automations",
    response_model=AutomationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_automation(
    payload: AutomationCreate,
    session: SessionDep,
) -> AutomationResponse:
    automation = Automation(
        name=payload.name,
        instruction=payload.instruction,
        trigger_type=payload.trigger_type,
    )
    session.add(automation)
    try:
        token = await apply_automation_write(session, automation, payload)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(automation)
    return await automation_response(session, automation, webhook_token=token)


@private_router.get("/automations/{automation_id}", response_model=AutomationResponse)
async def read_automation(automation_id: UUID, session: SessionDep) -> AutomationResponse:
    return await automation_response(session, await _get_automation(session, automation_id))


@private_router.put("/automations/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: UUID,
    payload: AutomationUpdate,
    session: SessionDep,
) -> AutomationResponse:
    automation = await _get_automation(session, automation_id)
    try:
        token = await apply_automation_write(session, automation, payload)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(automation)
    return await automation_response(session, automation, webhook_token=token)


@private_router.delete(
    "/automations/{automation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_automation(automation_id: UUID, session: SessionDep) -> Response:
    automation = await _get_automation(session, automation_id)
    await session.delete(automation)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@private_router.post(
    "/automations/{automation_id}/rotate-webhook-token",
    response_model=AutomationResponse,
)
async def rotate_webhook_token(
    automation_id: UUID, session: SessionDep
) -> AutomationResponse:
    automation = await _get_automation(session, automation_id)
    if automation.trigger_type != "webhook":
        raise HTTPException(status_code=422, detail="Only webhook automations have a token.")
    token = new_webhook_token()
    automation.webhook_token_hash = hash_webhook_token(token)
    automation.webhook_rotated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(automation)
    return await automation_response(session, automation, webhook_token=token)


@private_router.post(
    "/automations/{automation_id}/run",
    response_model=AutomationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_automation_now(
    automation_id: UUID, session: SessionDep
) -> AutomationRunResponse:
    automation = await _get_automation(session, automation_id)
    run = await enqueue_manual_run(session, automation)
    return await run_response(session, run)


@private_router.get("/automation-runs", response_model=list[AutomationRunResponse])
async def list_automation_runs(
    session: SessionDep,
    automation_id: UUID | None = None,
    run_status: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AutomationRunResponse]:
    query = select(AutomationRun)
    if automation_id is not None:
        query = query.where(AutomationRun.automation_id == automation_id)
    if run_status is not None:
        query = query.where(AutomationRun.status == run_status)
    runs = list(
        await session.scalars(
            query.order_by(AutomationRun.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return [await run_response(session, run) for run in runs]


@private_router.get("/automation-runs/{run_id}", response_model=AutomationRunResponse)
async def read_automation_run(run_id: UUID, session: SessionDep) -> AutomationRunResponse:
    return await run_response(session, await _get_run(session, run_id))


@private_router.post("/automation-runs/{run_id}/cancel", response_model=AutomationRunResponse)
async def cancel_automation_run(
    run_id: UUID, session: SessionDep
) -> AutomationRunResponse:
    run = await _get_run(session, run_id)
    if run.status != "queued":
        raise HTTPException(status_code=409, detail="Only queued runs can be cancelled.")
    run.status = "cancelled"
    run.finished_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(run)
    return await run_response(session, run)


@private_router.post(
    "/automation-runs/{run_id}/retry",
    response_model=AutomationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_automation_run(run_id: UUID, session: SessionDep) -> AutomationRunResponse:
    previous = await _get_run(session, run_id)
    if previous.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed runs can be retried.")
    automation = await _get_automation(session, previous.automation_id)
    run = await enqueue_run(
        session,
        automation,
        trigger_source="retry",
        occurrence_key=f"retry:{previous.id}:{uuid4()}",
        scheduled_for=datetime.now(UTC),
        trigger_payload=previous.trigger_payload,
    )
    if run is None:
        raise HTTPException(status_code=409, detail="The retry could not be queued.")
    await session.commit()
    await session.refresh(run)
    return await run_response(session, run)


@private_router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    session: SessionDep,
    unread_only: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> NotificationListResponse:
    query = select(Notification)
    count_query = select(func.count(Notification.id))
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
        count_query = count_query.where(Notification.read_at.is_(None))
    items = list(
        await session.scalars(
            query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        unread_count=await unread_notification_count(session),
        total=int(await session.scalar(count_query) or 0),
    )


@private_router.post(
    "/notifications/{notification_id}/read", response_model=NotificationResponse
)
async def mark_notification_read(
    notification_id: UUID, session: SessionDep
) -> NotificationResponse:
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(notification)
    return NotificationResponse.model_validate(notification)


@private_router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(session: SessionDep) -> Response:
    items = list(
        await session.scalars(select(Notification).where(Notification.read_at.is_(None)))
    )
    now = datetime.now(UTC)
    for item in items:
        item.read_at = now
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@private_router.delete(
    "/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_notification(notification_id: UUID, session: SessionDep) -> Response:
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.delete(notification)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.post("/webhooks/{token}", response_model=WebhookAcceptedResponse)
async def receive_automation_webhook(
    token: str,
    request: Request,
    session: SessionDep,
) -> WebhookAcceptedResponse:
    body = await request.body()
    if len(body) > settings.aster_webhook_max_bytes:
        raise HTTPException(status_code=413, detail="Webhook payload is too large.")
    webhook_status, run = await accept_webhook(
        session,
        token=token,
        body=body,
        headers={key.lower(): value for key, value in request.headers.items()},
    )
    return WebhookAcceptedResponse(
        status=webhook_status,
        run_id=run.id if run else None,
    )
