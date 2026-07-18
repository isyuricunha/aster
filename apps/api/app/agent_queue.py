from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import (
    Agent,
    AgentCommunicationScope,
    AgentControl,
    AgentKnowledgeScope,
    AgentRun,
    AgentToolScope,
)
from app.agent_run_scope_models import (
    AgentRunCommunicationScope,
    AgentRunContextScope,
    AgentRunKnowledgeScope,
    AgentRunToolScope,
)
from app.agent_schedule import next_agent_run_at


async def agent_control(session: AsyncSession) -> AgentControl:
    control = await session.get(AgentControl, 1)
    if control is None:
        control = AgentControl(id=1)
        session.add(control)
        await session.flush()
    return control


async def _snapshot_run_scopes(
    session: AsyncSession,
    *,
    agent: Agent,
    run_id: UUID,
) -> None:
    tools = list(
        await session.scalars(select(AgentToolScope).where(AgentToolScope.agent_id == agent.id))
    )
    communications = list(
        await session.scalars(
            select(AgentCommunicationScope).where(AgentCommunicationScope.agent_id == agent.id)
        )
    )
    collections = list(
        await session.scalars(
            select(AgentKnowledgeScope).where(AgentKnowledgeScope.agent_id == agent.id)
        )
    )
    session.add(
        AgentRunContextScope(
            run_id=run_id,
            persona_id=agent.persona_id,
            memory_enabled=agent.memory_enabled,
            rag_enabled=agent.rag_enabled,
        )
    )
    session.add_all(
        AgentRunToolScope(
            run_id=run_id,
            tool_id=item.tool_id,
            approval_policy=item.approval_policy,
        )
        for item in tools
    )
    session.add_all(
        AgentRunCommunicationScope(
            run_id=run_id,
            account_id=item.account_id,
            allow_read=item.allow_read,
            allow_reply=item.allow_reply,
            reply_approval_policy=item.reply_approval_policy,
        )
        for item in communications
    )
    session.add_all(
        AgentRunKnowledgeScope(
            run_id=run_id,
            collection_id=item.collection_id,
        )
        for item in collections
    )
    await session.flush()


async def enqueue_agent_run(
    session: AsyncSession,
    agent: Agent,
    *,
    trigger_source: str,
    occurrence_key: str,
    scheduled_for: datetime,
    trigger_payload: dict[str, object] | None = None,
) -> AgentRun | None:
    control = await agent_control(session)
    if control.emergency_stop or not agent.enabled or agent.paused:
        return None
    now = datetime.now(UTC)
    run = AgentRun(
        agent_id=agent.id,
        trigger_source=trigger_source,
        status="queued",
        occurrence_key=occurrence_key,
        scheduled_for=scheduled_for,
        available_at=now,
        goal_snapshot=agent.goal,
        trigger_payload=trigger_payload or {},
        persona_name=agent.persona_name,
        persona_instructions=agent.persona_instructions,
        persona_instruction_role=agent.persona_instruction_role,
        requested_model_id=agent.model_id,
        max_steps=agent.max_steps,
        max_model_calls=agent.max_model_calls,
        max_tool_calls=agent.max_tool_calls,
        max_runtime_seconds=agent.max_runtime_seconds,
        max_estimated_tokens=agent.max_estimated_tokens,
        max_estimated_cost_microusd=agent.max_estimated_cost_microusd,
        input_cost_per_million_microusd=agent.input_cost_per_million_microusd,
        output_cost_per_million_microusd=agent.output_cost_per_million_microusd,
    )
    try:
        async with session.begin_nested():
            session.add(run)
            await session.flush()
            await _snapshot_run_scopes(session, agent=agent, run_id=run.id)
    except IntegrityError:
        return None
    agent.last_enqueued_at = now
    return run


async def enqueue_due_agents(session: AsyncSession, *, limit: int) -> int:
    control = await agent_control(session)
    if control.emergency_stop:
        await session.commit()
        return 0
    now = datetime.now(UTC)
    agents = list(
        await session.scalars(
            select(Agent)
            .where(
                Agent.enabled.is_(True),
                Agent.paused.is_(False),
                Agent.next_run_at.is_not(None),
                Agent.next_run_at <= now,
            )
            .order_by(Agent.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    created = 0
    for agent in agents:
        scheduled_for = agent.next_run_at
        if scheduled_for is None:
            continue
        run = await enqueue_agent_run(
            session,
            agent,
            trigger_source="schedule",
            occurrence_key=f"schedule:{agent.id}:{scheduled_for.isoformat()}",
            scheduled_for=scheduled_for,
        )
        if run is not None:
            created += 1
        agent.next_run_at = next_agent_run_at(
            agent.trigger_type,
            agent.schedule,
            agent.timezone,
            now=now,
            after=now,
        )
    await session.commit()
    return created


async def enqueue_manual_agent_run(session: AsyncSession, agent: Agent) -> AgentRun:
    control = await agent_control(session)
    if control.emergency_stop:
        raise HTTPException(
            status_code=409,
            detail="The autonomous agent emergency stop is active.",
        )
    if not agent.enabled or agent.paused:
        raise HTTPException(status_code=409, detail="The agent is disabled or paused.")
    now = datetime.now(UTC)
    run = await enqueue_agent_run(
        session,
        agent,
        trigger_source="manual",
        occurrence_key=f"manual:{agent.id}:{uuid4()}",
        scheduled_for=now,
    )
    if run is None:
        raise HTTPException(status_code=409, detail="The agent run could not be queued.")
    await session.commit()
    await session.refresh(run)
    return run


async def enqueue_agent_retry(
    session: AsyncSession,
    source: AgentRun,
    agent: Agent,
) -> AgentRun:
    if source.status not in {"failed", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="Only failed or cancelled runs can be retried.",
        )
    now = datetime.now(UTC)
    run = await enqueue_agent_run(
        session,
        agent,
        trigger_source="retry",
        occurrence_key=f"retry:{source.id}:{uuid4()}",
        scheduled_for=now,
        trigger_payload=source.trigger_payload,
    )
    if run is None:
        raise HTTPException(status_code=409, detail="The agent retry could not be queued.")
    await session.commit()
    await session.refresh(run)
    return run


async def recover_expired_agent_runs(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    runs = list(
        await session.scalars(
            select(AgentRun).where(
                AgentRun.status == "running",
                AgentRun.lease_expires_at.is_not(None),
                AgentRun.lease_expires_at < now,
            )
        )
    )
    for run in runs:
        run.status = "failed"
        run.error_code = "worker_interrupted"
        run.error_message = (
            "The worker lease expired. The run was stopped instead of replaying an "
            "uncertain external action."
        )
        run.finished_at = now
        run.lease_owner = None
        run.lease_expires_at = None
    if runs:
        await session.commit()
    return len(runs)


async def claim_next_agent_run(
    session: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int,
) -> AgentRun | None:
    control = await agent_control(session)
    if control.emergency_stop:
        await session.commit()
        return None
    now = datetime.now(UTC)
    run = await session.scalar(
        select(AgentRun)
        .join(Agent, Agent.id == AgentRun.agent_id)
        .where(
            AgentRun.status == "queued",
            AgentRun.available_at <= now,
            Agent.enabled.is_(True),
            Agent.paused.is_(False),
        )
        .order_by(AgentRun.available_at, AgentRun.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if run is None:
        await session.commit()
        return None
    run.status = "running"
    run.lease_owner = worker_id
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    if run.started_at is None:
        run.started_at = now
        run.deadline_at = now + timedelta(seconds=run.max_runtime_seconds)
    run.finished_at = None
    await session.commit()
    await session.refresh(run)
    return run


async def renew_agent_run_lease(
    session: AsyncSession,
    *,
    run_id: UUID,
    worker_id: str,
    lease_seconds: int,
) -> bool:
    now = datetime.now(UTC)
    control = await agent_control(session)
    run = await session.get(AgentRun, run_id)
    if (
        control.emergency_stop
        or run is None
        or run.lease_owner != worker_id
        or run.status != "running"
        or run.lease_expires_at is None
        or run.lease_expires_at <= now
    ):
        return False
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    await session.commit()
    return True


async def release_agent_run(
    session: AsyncSession,
    run: AgentRun,
    *,
    status: str,
    available_at: datetime | None = None,
) -> None:
    run.status = status
    run.lease_owner = None
    run.lease_expires_at = None
    if available_at is not None:
        run.available_at = available_at
    await session.commit()
