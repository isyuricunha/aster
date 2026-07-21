from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import Automation
from app.automation_queue import enqueue_manual_run
from app.automation_schedule import next_run_at
from app.automation_schemas import (
    AutomationEnabledUpdate,
    AutomationResponse,
    AutomationRunResponse,
)
from app.automation_service import automation_response, run_response
from app.builtin_tasks import builtin_task_available, ensure_builtin_tasks
from app.db import get_session

router = APIRouter(prefix="/api", tags=["tasks"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_task(session: AsyncSession, task_id: UUID) -> Automation:
    task = await session.get(Automation, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks", response_model=list[AutomationResponse])
async def list_tasks(session: SessionDep) -> list[AutomationResponse]:
    await ensure_builtin_tasks(session)
    items = list(
        await session.scalars(
            select(Automation).order_by(
                Automation.builtin_key.is_(None),
                Automation.created_at,
                Automation.name,
            )
        )
    )
    return [await automation_response(session, item) for item in items]


@router.post("/tasks/{task_id}/enabled", response_model=AutomationResponse)
async def set_task_enabled(
    task_id: UUID,
    payload: AutomationEnabledUpdate,
    session: SessionDep,
) -> AutomationResponse:
    task = await _get_task(session, task_id)
    if payload.enabled and task.builtin_key and not builtin_task_available(task):
        raise HTTPException(
            status_code=409,
            detail="This built-in task requires a first-class Skills system that is not available yet.",
        )
    task.enabled = payload.enabled
    task.next_run_at = (
        next_run_at(task.trigger_type, task.schedule, task.timezone)
        if payload.enabled
        else None
    )
    await session.commit()
    await session.refresh(task)
    return await automation_response(session, task)


@router.post(
    "/tasks/{task_id}/run",
    response_model=AutomationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_task_now(
    task_id: UUID,
    session: SessionDep,
) -> AutomationRunResponse:
    task = await _get_task(session, task_id)
    if task.builtin_key and not builtin_task_available(task):
        raise HTTPException(
            status_code=409,
            detail="This built-in task is waiting for Aster's future Skills system.",
        )
    run = await enqueue_manual_run(session, task)
    return await run_response(session, run)
