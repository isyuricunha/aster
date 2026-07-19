import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.automation_models import (
    Automation,
    AutomationDelivery,
    AutomationDeliveryAttempt,
    AutomationRun,
    IntegrationConnection,
    Notification,
)
from app.config import Settings
from app.integration_service import (
    IntegrationError,
    deliver_calendar_event,
    deliver_email,
    deliver_webhook,
)
from app.model_routing import can_fallback, resolve_automation_targets
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.prompt_library import (
    AUTOMATION_SYSTEM_PROMPT,
    automation_user_prompt,
    render_persona,
)
from app.security import SecretCipher


def _messages(run: AutomationRun) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = [
        {"role": "system", "content": AUTOMATION_SYSTEM_PROMPT}
    ]
    if run.persona_name and run.persona_instruction_role:
        persona = render_persona(run.persona_name, run.persona_instructions or "")
        if persona:
            messages.append(
                {
                    "role": run.persona_instruction_role,
                    "content": persona,
                }
            )
    messages.append(
        {
            "role": "user",
            "content": automation_user_prompt(
                instruction=run.instruction_snapshot,
                scheduled_for=run.scheduled_for,
                trigger_payload=run.trigger_payload,
            ),
        }
    )
    return messages


async def _generate(
    session: AsyncSession,
    *,
    run: AutomationRun,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
    output_limit: int,
) -> tuple[str, str]:
    targets = await resolve_automation_targets(session, cipher, run.requested_model_id)
    messages = _messages(run)
    last_error: ModelEndpointError | None = None
    for index, target in enumerate(targets):
        chunks: list[str] = []
        output_characters = 0
        try:
            parameters = target.parameters
            async with asyncio.timeout(run.timeout_seconds):
                async for chunk in client.stream_chat_completion(
                    base_url=target.base_url,
                    api_key=target.api_key,
                    model_id=target.provider_model_id,
                    messages=messages,
                    temperature=parameters.temperature,
                    top_p=parameters.top_p,
                    max_output_tokens=parameters.max_output_tokens,
                    token_parameter=parameters.token_parameter,
                    reasoning_effort=parameters.reasoning_effort,
                ):
                    chunks.append(chunk)
                    output_characters += len(chunk)
                    if output_characters > output_limit:
                        raise ModelEndpointError(
                            "output_too_large",
                            "The automation output exceeded the configured character limit.",
                        )
            if not chunks:
                raise ModelEndpointError(
                    "empty_response", "The model returned no automation output."
                )
            return "".join(chunks), target.provider_model_id
        except TimeoutError as error:
            last_error = ModelEndpointError("timeout", "The automation model call timed out.")
            if index + 1 < len(targets) and not chunks:
                continue
            raise last_error from error
        except ModelEndpointError as error:
            last_error = error
            if index + 1 < len(targets) and not chunks and can_fallback(error):
                continue
            raise
    raise last_error or ModelEndpointError("unavailable", "No automation model is available.")


async def _delivery_rows(
    session: AsyncSession, automation_id: UUID
) -> list[tuple[AutomationDelivery, IntegrationConnection]]:
    return list(
        (
            await session.execute(
                select(AutomationDelivery, IntegrationConnection)
                .join(
                    IntegrationConnection,
                    IntegrationConnection.id == AutomationDelivery.integration_id,
                )
                .where(
                    AutomationDelivery.automation_id == automation_id,
                    AutomationDelivery.enabled.is_(True),
                    IntegrationConnection.enabled.is_(True),
                )
                .order_by(AutomationDelivery.position)
            )
        ).all()
    )


async def _deliver(
    session: AsyncSession,
    *,
    run: AutomationRun,
    automation: Automation,
    cipher: SecretCipher,
    settings: Settings,
) -> bool:
    rows = await _delivery_rows(session, automation.id)
    had_error = False
    for delivery, integration in rows:
        attempt = AutomationDeliveryAttempt(
            run_id=run.id,
            delivery_id=delivery.id,
            integration_id=integration.id,
            channel=delivery.channel,
            status="running",
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
        try:
            if delivery.channel == "email":
                recipients = delivery.config.get("recipients", [])
                if not isinstance(recipients, list) or not all(
                    isinstance(item, str) for item in recipients
                ):
                    raise IntegrationError("invalid_delivery", "Email recipients are invalid.")
                subject = str(delivery.config.get("subject") or automation.name)
                result = await deliver_email(
                    integration,
                    cipher=cipher,
                    recipients=recipients,
                    subject=subject,
                    body=run.response or "",
                )
            elif delivery.channel == "calendar":
                duration = delivery.config.get("duration_minutes", 30)
                if not isinstance(duration, int) or isinstance(duration, bool):
                    raise IntegrationError("invalid_delivery", "Calendar duration is invalid.")
                result = await deliver_calendar_event(
                    integration,
                    cipher=cipher,
                    uid=run.id,
                    summary=str(delivery.config.get("summary") or automation.name),
                    description=run.response or "",
                    start=run.scheduled_for,
                    duration_minutes=duration,
                    timeout_seconds=settings.aster_integration_timeout_seconds,
                )
            else:
                result = await deliver_webhook(
                    integration,
                    cipher=cipher,
                    payload={
                        "type": "aster.automation.completed",
                        "automation_id": str(automation.id),
                        "run_id": str(run.id),
                        "scheduled_for": run.scheduled_for.isoformat(),
                        "model": run.provider_model_id,
                        "response": run.response,
                    },
                    timeout_seconds=settings.aster_integration_timeout_seconds,
                )
            attempt.status = "completed"
            attempt.destination = result.destination[:500]
        except IntegrationError as error:
            had_error = True
            attempt.status = "failed"
            attempt.error_message = error.message[:500]
        attempt.finished_at = datetime.now(UTC)
        await session.commit()
    return had_error


async def _notify(
    session: AsyncSession,
    *,
    automation: Automation,
    run: AutomationRun,
) -> None:
    failed = run.status in {"failed", "completed_with_errors"}
    if failed and not automation.notify_on_failure:
        return
    if not failed and not automation.notify_on_success:
        return
    session.add(
        Notification(
            automation_id=automation.id,
            run_id=run.id,
            level="error" if failed else "success",
            title=f"{automation.name}: {'needs attention' if failed else 'completed'}",
            body=(run.error_message or run.response or "Automation finished.")[:20_000],
        )
    )
    await session.commit()


async def execute_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    run_id: UUID,
    worker_id: str,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
    settings: Settings,
) -> None:
    async with session_factory() as session:
        run = await session.get(AutomationRun, run_id)
        if run is None or run.status != "running" or run.lease_owner != worker_id:
            return
        automation = await session.get(Automation, run.automation_id)
        if automation is None:
            run.status = "failed"
            run.error_code = "automation_missing"
            run.error_message = "The automation no longer exists."
            run.finished_at = datetime.now(UTC)
            await session.commit()
            return
        try:
            output, model_id = await _generate(
                session,
                run=run,
                client=client,
                cipher=cipher,
                output_limit=settings.aster_automation_output_max_characters,
            )
            run.response = output
            run.provider_model_id = model_id
            run.status = "delivering"
            run.error_code = None
            run.error_message = None
            await session.commit()
            delivery_error = await _deliver(
                session,
                run=run,
                automation=automation,
                cipher=cipher,
                settings=settings,
            )
            run.status = "completed_with_errors" if delivery_error else "completed"
            if delivery_error:
                run.error_code = "delivery_failed"
                run.error_message = "One or more integration deliveries failed."
            run.finished_at = datetime.now(UTC)
            run.lease_owner = None
            run.lease_expires_at = None
            automation.last_run_at = run.finished_at
            history = list(run.attempt_history)
            history.append(
                {
                    "attempt": run.attempt,
                    "status": run.status,
                    "finished_at": run.finished_at.isoformat(),
                }
            )
            run.attempt_history = history
            await session.commit()
            await _notify(session, automation=automation, run=run)
        except (ModelEndpointError, HTTPException) as error:
            now = datetime.now(UTC)
            code = getattr(error, "code", "configuration_error")
            detail = getattr(error, "detail", error)
            message = str(getattr(error, "message", detail))[:500]
            history = list(run.attempt_history)
            history.append(
                {
                    "attempt": run.attempt,
                    "status": "failed",
                    "finished_at": now.isoformat(),
                    "error": message,
                }
            )
            run.attempt_history = history
            run.error_code = code
            run.error_message = message
            run.lease_owner = None
            run.lease_expires_at = None
            if run.attempt < run.max_attempts:
                run.status = "queued"
                run.available_at = now + timedelta(seconds=run.retry_delay_seconds)
                run.started_at = None
            else:
                run.status = "failed"
                run.finished_at = now
                automation.last_run_at = now
            await session.commit()
            if run.status == "failed":
                await _notify(session, automation=automation, run=run)
        except Exception as error:
            now = datetime.now(UTC)
            run.status = "failed"
            run.error_code = "automation_failed"
            run.error_message = str(error)[:500]
            run.finished_at = now
            run.lease_owner = None
            run.lease_expires_at = None
            automation.last_run_at = now
            await session.commit()
            await _notify(session, automation=automation, run=run)
