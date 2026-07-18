from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import AgentApproval, AgentRun, AgentStep
from app.agent_queue import enqueue_agent_retry, enqueue_manual_agent_run
from app.agent_schemas import AgentRunActionResponse, AgentRunResponse
from app.agent_service import run_response
from app.db import get_session
from app.routes.agents import get_agent

router = APIRouter(prefix="/api", tags=["agent-runs"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_agent_run(session: AsyncSession, run_id: UUID) -> AgentRun:
    run = await session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.post(
    "/agents/{agent_id}/run",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_agent_now(agent_id: UUID, session: SessionDep) -> AgentRunResponse:
    run = await enqueue_manual_agent_run(session, await get_agent(session, agent_id))
    return await run_response(session, run)


@router.get("/agent-runs", response_model=list[AgentRunResponse])
async def list_agent_runs(
    session: SessionDep,
    agent_id: UUID | None = None,
    run_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AgentRunResponse]:
    statement = select(AgentRun)
    if agent_id is not None:
        statement = statement.where(AgentRun.agent_id == agent_id)
    if run_status is not None:
        allowed = {
            "queued",
            "running",
            "waiting_approval",
            "paused",
            "completed",
            "failed",
            "cancelled",
        }
        if run_status not in allowed:
            raise HTTPException(status_code=422, detail="Unsupported agent run status")
        statement = statement.where(AgentRun.status == run_status)
    runs = list(
        await session.scalars(
            statement.order_by(AgentRun.created_at.desc()).limit(limit)
        )
    )
    return [await run_response(session, item) for item in runs]


@router.get("/agent-runs/{run_id}", response_model=AgentRunResponse)
async def read_agent_run(run_id: UUID, session: SessionDep) -> AgentRunResponse:
    return await run_response(session, await get_agent_run(session, run_id))


@router.post(
    "/agent-runs/{run_id}/pause",
    response_model=AgentRunActionResponse,
)
async def pause_agent_run(
    run_id: UUID,
    session: SessionDep,
) -> AgentRunActionResponse:
    run = await get_agent_run(session, run_id)
    if run.status not in {"queued", "running"}:
        raise HTTPException(
            status_code=409,
            detail="Only queued or running agent runs can pause.",
        )
    run.pause_requested = True
    if run.status == "queued":
        run.status = "paused"
    await session.commit()
    return AgentRunActionResponse(status=run.status, run_id=run.id)


@router.post(
    "/agent-runs/{run_id}/resume",
    response_model=AgentRunActionResponse,
)
async def resume_agent_run(
    run_id: UUID,
    session: SessionDep,
) -> AgentRunActionResponse:
    run = await get_agent_run(session, run_id)
    if run.status != "paused":
        raise HTTPException(status_code=409, detail="Only paused agent runs can resume.")
    run.pause_requested = False
    run.status = "queued"
    run.available_at = datetime.now(UTC)
    run.lease_owner = None
    run.lease_expires_at = None
    await session.commit()
    return AgentRunActionResponse(status=run.status, run_id=run.id)


@router.post(
    "/agent-runs/{run_id}/cancel",
    response_model=AgentRunActionResponse,
)
async def cancel_agent_run(
    run_id: UUID,
    session: SessionDep,
) -> AgentRunActionResponse:
    run = await get_agent_run(session, run_id)
    if run.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="The agent run already finished.")
    run.cancel_requested = True
    if run.status != "running":
        now = datetime.now(UTC)
        run.status = "cancelled"
        run.error_code = "cancelled"
        run.error_message = "The agent run was cancelled by the owner."
        run.finished_at = now
        run.lease_owner = None
        run.lease_expires_at = None
        approvals = list(
            await session.scalars(
                select(AgentApproval).where(
                    AgentApproval.run_id == run.id,
                    AgentApproval.status == "pending",
                )
            )
        )
        for approval in approvals:
            approval.status = "cancelled"
            approval.decided_at = now
    await session.commit()
    return AgentRunActionResponse(status=run.status, run_id=run.id)


@router.post(
    "/agent-runs/{run_id}/retry",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_agent_run(
    run_id: UUID,
    session: SessionDep,
) -> AgentRunResponse:
    source = await get_agent_run(session, run_id)
    agent = await get_agent(session, source.agent_id)
    run = await enqueue_agent_retry(session, source, agent)
    return await run_response(session, run)


async def _pending_approval(
    session: AsyncSession,
    approval_id: UUID,
) -> tuple[AgentApproval, AgentRun, AgentStep]:
    approval = await session.get(AgentApproval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Agent approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="The approval was already decided.")
    run = await get_agent_run(session, approval.run_id)
    step = await session.get(AgentStep, approval.step_id)
    if run.status != "waiting_approval" or step is None or step.status != "waiting_approval":
        raise HTTPException(
            status_code=409,
            detail="The action is no longer waiting for approval.",
        )
    return approval, run, step


@router.post(
    "/agent-approvals/{approval_id}/approve",
    response_model=AgentRunResponse,
)
async def approve_agent_action(
    approval_id: UUID,
    session: SessionDep,
) -> AgentRunResponse:
    approval, run, _ = await _pending_approval(session, approval_id)
    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    run.status = "queued"
    run.available_at = datetime.now(UTC)
    run.lease_owner = None
    run.lease_expires_at = None
    await session.commit()
    await session.refresh(run)
    return await run_response(session, run)


@router.post(
    "/agent-approvals/{approval_id}/deny",
    response_model=AgentRunResponse,
)
async def deny_agent_action(
    approval_id: UUID,
    session: SessionDep,
) -> AgentRunResponse:
    approval, run, step = await _pending_approval(session, approval_id)
    now = datetime.now(UTC)
    approval.status = "denied"
    approval.decided_at = now
    step.status = "denied"
    step.result = "The owner denied this action. Choose a different safe path or finish."
    step.finished_at = now
    run.status = "queued"
    run.available_at = now
    run.lease_owner = None
    run.lease_expires_at = None
    await session.commit()
    await session.refresh(run)
    return await run_response(session, run)
