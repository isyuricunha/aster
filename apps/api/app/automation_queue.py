from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import Automation, AutomationRun
from app.automation_schedule import next_run_at


async def enqueue_run(
    session: AsyncSession,
    automation: Automation,
    *,
    trigger_source: str,
    occurrence_key: str,
    scheduled_for: datetime,
    trigger_payload: dict[str, object] | None = None,
) -> AutomationRun | None:
    run = AutomationRun(
        automation_id=automation.id,
        trigger_source=trigger_source,
        status="queued",
        occurrence_key=occurrence_key,
        scheduled_for=scheduled_for,
        available_at=datetime.now(UTC),
        max_attempts=automation.max_attempts,
        retry_delay_seconds=automation.retry_delay_seconds,
        timeout_seconds=automation.timeout_seconds,
        trigger_payload=trigger_payload or {},
        instruction_snapshot=automation.instruction,
        persona_name=automation.persona_name,
        persona_instructions=automation.persona_instructions,
        persona_instruction_role=automation.persona_instruction_role,
        requested_model_id=automation.model_id,
    )
    try:
        async with session.begin_nested():
            session.add(run)
            await session.flush()
    except IntegrityError:
        return None
    automation.last_enqueued_at = datetime.now(UTC)
    return run


async def enqueue_due_automations(session: AsyncSession, *, limit: int) -> int:
    now = datetime.now(UTC)
    automations = list(
        await session.scalars(
            select(Automation)
            .where(
                Automation.enabled.is_(True),
                Automation.trigger_type != "webhook",
                Automation.next_run_at.is_not(None),
                Automation.next_run_at <= now,
            )
            .order_by(Automation.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    created = 0
    for automation in automations:
        scheduled_for = automation.next_run_at
        if scheduled_for is None:
            continue
        run = await enqueue_run(
            session,
            automation,
            trigger_source="schedule",
            occurrence_key=f"schedule:{automation.id}:{scheduled_for.isoformat()}",
            scheduled_for=scheduled_for,
        )
        if run is not None:
            created += 1
        automation.next_run_at = next_run_at(
            automation.trigger_type,
            automation.schedule,
            automation.timezone,
            now=now,
            after=scheduled_for,
        )
    await session.commit()
    return created


async def enqueue_manual_run(session: AsyncSession, automation: Automation) -> AutomationRun:
    now = datetime.now(UTC)
    run = await enqueue_run(
        session,
        automation,
        trigger_source="manual",
        occurrence_key=f"manual:{automation.id}:{uuid4()}",
        scheduled_for=now,
    )
    if run is None:
        raise HTTPException(status_code=409, detail="The run could not be queued.")
    await session.commit()
    await session.refresh(run)
    return run


async def recover_expired_automation_runs(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    runs = list(
        await session.scalars(
            select(AutomationRun).where(
                AutomationRun.status.in_(["running", "delivering"]),
                AutomationRun.lease_expires_at.is_not(None),
                AutomationRun.lease_expires_at < now,
            )
        )
    )
    for run in runs:
        history = list(run.attempt_history)
        history.append(
            {
                "attempt": run.attempt,
                "status": "interrupted",
                "finished_at": now.isoformat(),
                "error": "Worker lease expired.",
            }
        )
        run.attempt_history = history
        run.lease_owner = None
        run.lease_expires_at = None
        if run.status == "running" and run.response is None and run.attempt < run.max_attempts:
            run.status = "queued"
            run.available_at = now + timedelta(seconds=run.retry_delay_seconds)
            run.error_code = "worker_interrupted"
            run.error_message = "The worker lease expired before the model completed."
            run.started_at = None
        else:
            run.status = "failed" if run.response is None else "completed_with_errors"
            run.error_code = "worker_interrupted"
            run.error_message = "The worker lease expired."
            run.finished_at = now
    if runs:
        await session.commit()
    return len(runs)


async def claim_next_run(
    session: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int,
) -> AutomationRun | None:
    now = datetime.now(UTC)
    run = await session.scalar(
        select(AutomationRun)
        .where(
            AutomationRun.status == "queued",
            AutomationRun.available_at <= now,
        )
        .order_by(AutomationRun.available_at, AutomationRun.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if run is None:
        return None
    run.status = "running"
    run.attempt += 1
    run.lease_owner = worker_id
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    run.started_at = now
    run.finished_at = None
    await session.commit()
    await session.refresh(run)
    return run


async def renew_run_lease(
    session: AsyncSession,
    *,
    run_id: UUID,
    worker_id: str,
    lease_seconds: int,
) -> bool:
    now = datetime.now(UTC)
    run = await session.get(AutomationRun, run_id)
    if (
        run is None
        or run.lease_owner != worker_id
        or run.status not in {"running", "delivering"}
        or run.lease_expires_at is None
        or run.lease_expires_at <= now
    ):
        return False
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    await session.commit()
    return True
