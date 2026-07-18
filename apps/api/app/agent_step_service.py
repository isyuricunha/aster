from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import AgentControl, AgentRun, AgentStep
from app.agent_queue import release_agent_run
from app.agent_runtime import (
    AgentExecutionError,
    ModelRound,
    action_fingerprint,
    estimated_cost,
    estimated_tokens,
)


async def next_step_position(session: AsyncSession, run_id: UUID) -> int:
    current = await session.scalar(
        select(func.max(AgentStep.position)).where(AgentStep.run_id == run_id)
    )
    return int(current or 0) + 1


async def create_step(
    session: AsyncSession,
    run: AgentRun,
    *,
    kind: str,
    status: str,
    summary: str,
    content: str | None = None,
    provider_model_id: str | None = None,
    tool_id: UUID | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
    arguments: dict[str, object] | None = None,
    fingerprint: str | None = None,
) -> AgentStep:
    if run.steps_used >= run.max_steps:
        raise AgentExecutionError("step_budget_exceeded", "The agent exhausted its step budget.")
    now = datetime.now(UTC)
    step = AgentStep(
        run_id=run.id,
        position=await next_step_position(session, run.id),
        kind=kind,
        status=status,
        summary=summary[:500],
        content=content,
        provider_model_id=provider_model_id,
        tool_id=tool_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=arguments or {},
        fingerprint=fingerprint,
        started_at=now,
        finished_at=now if status not in {"running", "waiting_approval"} else None,
    )
    session.add(step)
    run.steps_used += 1
    await session.commit()
    await session.refresh(step)
    return step


def record_model_usage(run: AgentRun, result: ModelRound) -> None:
    input_tokens = estimated_tokens(result.input_characters)
    output_tokens = estimated_tokens(result.output_characters)
    run.model_calls_used += 1
    run.estimated_tokens += input_tokens + output_tokens
    run.estimated_cost_microusd += estimated_cost(run, input_tokens, output_tokens)
    run.provider_model_id = result.provider_model_id
    if run.estimated_tokens > run.max_estimated_tokens:
        raise AgentExecutionError(
            "token_budget_exceeded",
            "The agent exceeded its estimated token budget.",
        )
    if (
        run.max_estimated_cost_microusd is not None
        and run.estimated_cost_microusd > run.max_estimated_cost_microusd
    ):
        raise AgentExecutionError(
            "cost_budget_exceeded",
            "The agent exceeded its estimated cost budget.",
        )


async def register_action(
    run: AgentRun,
    *,
    name: str,
    arguments: dict[str, object],
    repeat_limit: int,
) -> str:
    if run.tool_calls_used >= run.max_tool_calls:
        raise AgentExecutionError("tool_budget_exceeded", "The agent exhausted its action budget.")
    fingerprint = action_fingerprint(name, arguments)
    fingerprints = list(run.action_fingerprints)
    if fingerprints.count(fingerprint) >= repeat_limit:
        raise AgentExecutionError(
            "repeated_action",
            "The agent repeated the same action too many times and was stopped.",
        )
    fingerprints.append(fingerprint)
    run.action_fingerprints = fingerprints
    run.tool_calls_used += 1
    return fingerprint


async def check_run_controls(session: AsyncSession, run: AgentRun) -> None:
    await session.refresh(run)
    control = await session.get(AgentControl, 1)
    if control and control.emergency_stop:
        raise AgentExecutionError(
            "emergency_stop",
            control.reason or "The autonomous agent emergency stop is active.",
        )
    if run.cancel_requested:
        raise AgentExecutionError("cancelled", "The agent run was cancelled by the owner.")
    if run.pause_requested:
        await release_agent_run(session, run, status="paused")
        raise AgentExecutionError("paused", "The agent run was paused by the owner.")
    if run.deadline_at and datetime.now(UTC) >= run.deadline_at:
        raise AgentExecutionError(
            "runtime_budget_exceeded",
            "The agent exceeded its runtime budget.",
        )
    if run.model_calls_used >= run.max_model_calls:
        raise AgentExecutionError(
            "model_budget_exceeded",
            "The agent exhausted its model-call budget.",
        )


async def complete_run(
    session: AsyncSession,
    *,
    run: AgentRun,
    result: str,
) -> None:
    run.final_output = result
    run.status = "completed"
    run.finished_at = datetime.now(UTC)
    run.lease_owner = None
    run.lease_expires_at = None
    await session.commit()


async def fail_run(
    session: AsyncSession,
    *,
    run: AgentRun,
    code: str,
    message: str,
) -> None:
    if code == "paused" and run.status == "paused":
        return
    run.status = "cancelled" if code in {"cancelled", "emergency_stop"} else "failed"
    run.error_code = code
    run.error_message = message[:500]
    run.finished_at = datetime.now(UTC)
    run.lease_owner = None
    run.lease_expires_at = None
    await session.commit()
