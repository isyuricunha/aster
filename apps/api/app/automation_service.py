import hashlib
import json
import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import (
    Automation,
    AutomationDelivery,
    AutomationDeliveryAttempt,
    AutomationRun,
    IntegrationConnection,
    Notification,
    WebhookDelivery,
)
from app.automation_queue import (
    enqueue_manual_run,
    enqueue_run,
    recover_expired_automation_runs,
)
from app.automation_schedule import ScheduleValidationError, next_run_at, validate_schedule
from app.automation_schemas import (
    AutomationDeliveryAttemptResponse,
    AutomationDeliveryResponse,
    AutomationResponse,
    AutomationRunResponse,
    AutomationWrite,
    IntegrationConnectionResponse,
)
from app.models import ModelCacheEntry, Persona, PersonaPreferences

__all__ = [
    "accept_webhook",
    "apply_automation_write",
    "automation_response",
    "enqueue_manual_run",
    "enqueue_run",
    "hash_webhook_token",
    "integration_response",
    "new_webhook_token",
    "recover_expired_automation_runs",
    "run_response",
    "unread_notification_count",
]

CHANNEL_KINDS = {"email": "smtp", "calendar": "caldav", "webhook": "webhook"}


def hash_webhook_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_webhook_token() -> str:
    return secrets.token_urlsafe(32)


def integration_response(integration: IntegrationConnection) -> IntegrationConnectionResponse:
    return IntegrationConnectionResponse.model_validate(integration)


async def _persona_snapshot(
    session: AsyncSession,
    *,
    persona_id: UUID | None,
    use_default_persona: bool,
) -> Persona | None:
    selected_id = persona_id
    if use_default_persona:
        preferences = await session.get(PersonaPreferences, 1)
        selected_id = preferences.default_persona_id if preferences else None
    if selected_id is None:
        return None
    persona = await session.get(Persona, selected_id)
    if persona is None or not persona.enabled:
        raise HTTPException(status_code=422, detail="The selected persona is unavailable.")
    return persona


async def _validate_model(session: AsyncSession, model_id: UUID | None) -> None:
    if model_id is None:
        return
    if await session.get(ModelCacheEntry, model_id) is None:
        raise HTTPException(status_code=422, detail="The selected model does not exist.")


async def _delivery_responses(
    session: AsyncSession,
    automation_id: UUID,
) -> list[AutomationDeliveryResponse]:
    rows = (
        await session.execute(
            select(AutomationDelivery, IntegrationConnection)
            .join(
                IntegrationConnection,
                IntegrationConnection.id == AutomationDelivery.integration_id,
            )
            .where(AutomationDelivery.automation_id == automation_id)
            .order_by(AutomationDelivery.position)
        )
    ).all()
    return [
        AutomationDeliveryResponse(
            id=delivery.id,
            integration_id=integration.id,
            integration_name=integration.name,
            channel=delivery.channel,
            enabled=delivery.enabled,
            config=delivery.config,
            position=delivery.position,
        )
        for delivery, integration in rows
    ]


async def automation_response(
    session: AsyncSession,
    automation: Automation,
    *,
    webhook_token: str | None = None,
) -> AutomationResponse:
    return AutomationResponse(
        id=automation.id,
        builtin_key=automation.builtin_key,
        state=automation.state,
        name=automation.name,
        description=automation.description,
        instruction=automation.instruction,
        enabled=automation.enabled,
        trigger_type=automation.trigger_type,
        timezone=automation.timezone,
        schedule=automation.schedule,
        next_run_at=automation.next_run_at,
        model_id=automation.model_id,
        persona_id=automation.persona_id,
        persona_name=automation.persona_name,
        persona_description=automation.persona_description,
        persona_instruction_role=automation.persona_instruction_role,
        notify_on_success=automation.notify_on_success,
        notify_on_failure=automation.notify_on_failure,
        max_attempts=automation.max_attempts,
        retry_delay_seconds=automation.retry_delay_seconds,
        timeout_seconds=automation.timeout_seconds,
        webhook_configured=automation.webhook_token_hash is not None,
        webhook_token=webhook_token,
        webhook_path=f"/api/webhooks/{webhook_token}" if webhook_token else None,
        deliveries=await _delivery_responses(session, automation.id),
        last_enqueued_at=automation.last_enqueued_at,
        last_run_at=automation.last_run_at,
        created_at=automation.created_at,
        updated_at=automation.updated_at,
    )


async def _replace_deliveries(
    session: AsyncSession,
    automation: Automation,
    payload: AutomationWrite,
) -> None:
    existing = list(
        await session.scalars(
            select(AutomationDelivery).where(
                AutomationDelivery.automation_id == automation.id
            )
        )
    )
    for item in existing:
        await session.delete(item)
    for position, item in enumerate(payload.deliveries):
        integration = await session.get(IntegrationConnection, item.integration_id)
        if integration is None:
            raise HTTPException(status_code=422, detail="An integration no longer exists.")
        expected_kind = CHANNEL_KINDS[item.channel]
        if integration.kind != expected_kind:
            raise HTTPException(
                status_code=422,
                detail=f"The {integration.name} integration cannot deliver {item.channel}.",
            )
        session.add(
            AutomationDelivery(
                automation_id=automation.id,
                integration_id=integration.id,
                channel=item.channel,
                enabled=item.enabled,
                config=item.config,
                position=position,
            )
        )


async def apply_automation_write(
    session: AsyncSession,
    automation: Automation,
    payload: AutomationWrite,
) -> str | None:
    try:
        schedule = validate_schedule(
            payload.trigger_type,
            payload.schedule,
            payload.timezone,
        )
    except ScheduleValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    await _validate_model(session, payload.model_id)
    persona = await _persona_snapshot(
        session,
        persona_id=payload.persona_id,
        use_default_persona=payload.use_default_persona,
    )
    automation.name = payload.name
    automation.description = payload.description
    automation.instruction = payload.instruction
    automation.enabled = payload.enabled
    automation.trigger_type = payload.trigger_type
    automation.timezone = payload.timezone
    automation.schedule = schedule
    automation.next_run_at = (
        next_run_at(payload.trigger_type, schedule, payload.timezone)
        if payload.enabled
        else None
    )
    automation.model_id = payload.model_id
    automation.persona_id = persona.id if persona else None
    automation.persona_name = persona.name if persona else None
    automation.persona_description = persona.description if persona else None
    automation.persona_instructions = persona.instructions if persona else None
    automation.persona_instruction_role = persona.instruction_role if persona else None
    automation.notify_on_success = payload.notify_on_success
    automation.notify_on_failure = payload.notify_on_failure
    automation.max_attempts = payload.max_attempts
    automation.retry_delay_seconds = payload.retry_delay_seconds
    automation.timeout_seconds = payload.timeout_seconds
    webhook_token: str | None = None
    if payload.trigger_type == "webhook" and automation.webhook_token_hash is None:
        webhook_token = new_webhook_token()
        automation.webhook_token_hash = hash_webhook_token(webhook_token)
        automation.webhook_rotated_at = datetime.now(UTC)
    if payload.trigger_type != "webhook":
        automation.webhook_token_hash = None
        automation.webhook_rotated_at = None
    await session.flush()
    await _replace_deliveries(session, automation, payload)
    return webhook_token


async def run_response(session: AsyncSession, run: AutomationRun) -> AutomationRunResponse:
    automation = await session.get(Automation, run.automation_id)
    attempts = list(
        await session.scalars(
            select(AutomationDeliveryAttempt)
            .where(AutomationDeliveryAttempt.run_id == run.id)
            .order_by(AutomationDeliveryAttempt.created_at)
        )
    )
    return AutomationRunResponse(
        id=run.id,
        automation_id=run.automation_id,
        automation_name=automation.name if automation else "Deleted automation",
        trigger_source=run.trigger_source,
        status=run.status,
        scheduled_for=run.scheduled_for,
        available_at=run.available_at,
        attempt=run.attempt,
        max_attempts=run.max_attempts,
        lease_owner=run.lease_owner,
        lease_expires_at=run.lease_expires_at,
        trigger_payload=run.trigger_payload,
        instruction_snapshot=run.instruction_snapshot,
        persona_name=run.persona_name,
        provider_model_id=run.provider_model_id,
        response=run.response,
        error_code=run.error_code,
        error_message=run.error_message,
        attempt_history=run.attempt_history,
        deliveries=[
            AutomationDeliveryAttemptResponse.model_validate(item) for item in attempts
        ],
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


async def unread_notification_count(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count(Notification.id)).where(Notification.read_at.is_(None))
        )
        or 0
    )


async def accept_webhook(
    session: AsyncSession,
    *,
    token: str,
    body: bytes,
    headers: dict[str, str],
) -> tuple[str, AutomationRun | None]:
    automation = await session.scalar(
        select(Automation).where(
            Automation.webhook_token_hash == hash_webhook_token(token),
            Automation.trigger_type == "webhook",
            Automation.enabled.is_(True),
        )
    )
    if automation is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")
    try:
        decoded = json.loads(body) if body else {}
        payload = decoded if isinstance(decoded, dict) else {"value": decoded}
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {"raw": body.decode("utf-8", errors="replace")}
    supplied_key = headers.get("x-aster-delivery") or headers.get("idempotency-key")
    delivery_key = supplied_key or f"generated:{uuid4()}"
    delivery = WebhookDelivery(
        automation_id=automation.id,
        delivery_key=delivery_key[:256],
        payload=payload,
        headers={
            key: value[:500]
            for key, value in headers.items()
            if key.casefold()
            in {
                "content-type",
                "user-agent",
                "x-aster-delivery",
                "idempotency-key",
            }
        },
    )
    try:
        async with session.begin_nested():
            session.add(delivery)
            await session.flush()
    except IntegrityError:
        return "duplicate", None
    now = datetime.now(UTC)
    run = await enqueue_run(
        session,
        automation,
        trigger_source="webhook",
        occurrence_key=f"webhook:{automation.id}:{delivery.delivery_key}",
        scheduled_for=now,
        trigger_payload=payload,
    )
    if run is None:
        return "duplicate", None
    delivery.run_id = run.id
    await session.commit()
    await session.refresh(run)
    return "accepted", run
