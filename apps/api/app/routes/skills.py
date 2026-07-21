from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_queue import enqueue_manual_run
from app.builtin_tasks import ensure_builtin_tasks
from app.db import get_session
from app.skill_models import Skill, SkillAuditAttempt
from app.skill_schemas import (
    SkillAuditAttemptResponse,
    SkillAuditPreferencesResponse,
    SkillAuditPreferencesUpdate,
    SkillAuditQueueResponse,
    SkillCreate,
    SkillResponse,
    SkillStatusUpdate,
    SkillUpdate,
)
from app.skill_service import (
    apply_skill_preferences,
    apply_skill_write,
    get_skill_preferences,
    reset_skill_audit,
    set_skill_status,
    skill_attempt_response,
    skill_preferences_response,
    skill_response,
)

router = APIRouter(prefix="/api", tags=["skills"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_skill(session: AsyncSession, skill_id: UUID) -> Skill:
    skill = await session.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.get("/skills", response_model=list[SkillResponse])
async def list_skills(session: SessionDep) -> list[SkillResponse]:
    items = list(
        await session.scalars(
            select(Skill).order_by(Skill.status.desc(), Skill.updated_at.desc(), Skill.name)
        )
    )
    return [await skill_response(session, item) for item in items]


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(payload: SkillCreate, session: SessionDep) -> SkillResponse:
    skill = Skill(name=payload.name, instructions=payload.instructions)
    apply_skill_write(skill, payload, creating=True)
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return await skill_response(session, skill)


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def read_skill(skill_id: UUID, session: SessionDep) -> SkillResponse:
    return await skill_response(session, await _get_skill(session, skill_id))


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: UUID,
    payload: SkillUpdate,
    session: SessionDep,
) -> SkillResponse:
    skill = await _get_skill(session, skill_id)
    apply_skill_write(skill, payload)
    await session.commit()
    await session.refresh(skill)
    return await skill_response(session, skill)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(skill_id: UUID, session: SessionDep) -> Response:
    skill = await _get_skill(session, skill_id)
    await session.delete(skill)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/skills/{skill_id}/status", response_model=SkillResponse)
async def update_skill_status(
    skill_id: UUID,
    payload: SkillStatusUpdate,
    session: SessionDep,
) -> SkillResponse:
    skill = await _get_skill(session, skill_id)
    if payload.status == "published" and skill.audit_status in {"duplicate", "trivial", "failed"}:
        raise HTTPException(
            status_code=409,
            detail="Resolve or explicitly edit this skill before publishing it.",
        )
    set_skill_status(skill, payload.status)
    await session.commit()
    await session.refresh(skill)
    return await skill_response(session, skill)


@router.post(
    "/skills/{skill_id}/audit",
    response_model=SkillAuditQueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def queue_skill_audit(skill_id: UUID, session: SessionDep) -> SkillAuditQueueResponse:
    skill = await _get_skill(session, skill_id)
    reset_skill_audit(skill)
    await session.commit()
    tasks = await ensure_builtin_tasks(session)
    task = next((item for item in tasks if item.builtin_key == "skills_audit"), None)
    if task is None:
        raise HTTPException(status_code=409, detail="Skills Audit task is unavailable.")
    run = await enqueue_manual_run(
        session,
        task,
        trigger_payload={"skill_id": str(skill.id)},
    )
    return SkillAuditQueueResponse(
        skill_id=skill.id,
        task_id=task.id,
        run_id=run.id,
        status="queued",
    )


@router.get(
    "/skill-audit-attempts",
    response_model=list[SkillAuditAttemptResponse],
)
async def list_skill_audit_attempts(
    session: SessionDep,
    skill_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> list[SkillAuditAttemptResponse]:
    query = select(SkillAuditAttempt)
    if skill_id is not None:
        query = query.where(SkillAuditAttempt.skill_id == skill_id)
    items = list(
        await session.scalars(
            query.order_by(
                SkillAuditAttempt.created_at.desc(),
                SkillAuditAttempt.attempt_number.desc(),
            ).limit(limit)
        )
    )
    return [skill_attempt_response(item) for item in items]


@router.get(
    "/skill-audit-preferences",
    response_model=SkillAuditPreferencesResponse,
)
async def read_skill_audit_preferences(session: SessionDep) -> SkillAuditPreferencesResponse:
    preferences = await get_skill_preferences(session)
    return await skill_preferences_response(session, preferences)


@router.put(
    "/skill-audit-preferences",
    response_model=SkillAuditPreferencesResponse,
)
async def update_skill_audit_preferences(
    payload: SkillAuditPreferencesUpdate,
    session: SessionDep,
) -> SkillAuditPreferencesResponse:
    preferences = await get_skill_preferences(session)
    await apply_skill_preferences(session, preferences, payload)
    await session.commit()
    await session.refresh(preferences)
    return await skill_preferences_response(session, preferences)
