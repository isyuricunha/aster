from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelCacheEntry, ModelEndpoint
from app.skill_models import Skill, SkillAuditAttempt, SkillAuditPreferences
from app.skill_schemas import (
    SkillAuditAttemptResponse,
    SkillAuditPreferencesResponse,
    SkillAuditPreferencesUpdate,
    SkillResponse,
    SkillWrite,
)


def _tests(payload: SkillWrite) -> list[dict[str, str]]:
    return [item.model_dump() for item in payload.test_cases]


def _content_changed(skill: Skill, payload: SkillWrite) -> bool:
    return any(
        [
            skill.name != payload.name,
            skill.description != payload.description,
            skill.instructions != payload.instructions,
            skill.source_type != payload.source_type,
            skill.tags != payload.tags,
            skill.trigger_phrases != payload.trigger_phrases,
            skill.test_cases != _tests(payload),
        ]
    )


def reset_skill_audit(skill: Skill) -> None:
    skill.status = "draft"
    skill.audit_status = "pending"
    skill.audit_score = None
    skill.audit_report = {}
    skill.duplicate_of_id = None
    skill.audited_revision = None
    skill.audited_at = None
    skill.published_at = None
    skill.last_error = None


def apply_skill_write(skill: Skill, payload: SkillWrite, *, creating: bool = False) -> None:
    changed = creating or _content_changed(skill, payload)
    skill.name = payload.name
    skill.description = payload.description
    skill.instructions = payload.instructions
    skill.source_type = payload.source_type
    skill.tags = payload.tags
    skill.trigger_phrases = payload.trigger_phrases
    skill.test_cases = _tests(payload)
    if changed:
        if not creating:
            skill.content_revision += 1
        reset_skill_audit(skill)


async def get_skill_preferences(session: AsyncSession) -> SkillAuditPreferences:
    preferences = await session.get(SkillAuditPreferences, 1)
    if preferences is None:
        preferences = SkillAuditPreferences(id=1)
        session.add(preferences)
        await session.commit()
        await session.refresh(preferences)
    return preferences


async def validate_teacher_model(session: AsyncSession, model_id: UUID | None) -> None:
    if model_id is None:
        return
    row = await session.scalar(select(ModelCacheEntry.id).where(ModelCacheEntry.id == model_id))
    if row is None:
        raise HTTPException(status_code=422, detail="The selected teacher model does not exist.")


async def apply_skill_preferences(
    session: AsyncSession,
    preferences: SkillAuditPreferences,
    payload: SkillAuditPreferencesUpdate,
) -> None:
    await validate_teacher_model(session, payload.teacher_model_id)
    preferences.auto_approve_threshold = payload.auto_approve_threshold
    preferences.max_self_edit_attempts = payload.max_self_edit_attempts
    preferences.max_skills_per_run = payload.max_skills_per_run
    preferences.teacher_rewrite_enabled = payload.teacher_rewrite_enabled
    preferences.teacher_model_id = payload.teacher_model_id


async def skill_response(session: AsyncSession, skill: Skill) -> SkillResponse:
    duplicate_name = None
    if skill.duplicate_of_id is not None:
        duplicate_name = await session.scalar(
            select(Skill.name).where(Skill.id == skill.duplicate_of_id)
        )
    attempt_count = int(
        await session.scalar(
            select(func.count(SkillAuditAttempt.id)).where(SkillAuditAttempt.skill_id == skill.id)
        )
        or 0
    )
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        instructions=skill.instructions,
        status=skill.status,
        source_type=skill.source_type,
        tags=skill.tags,
        trigger_phrases=skill.trigger_phrases,
        test_cases=skill.test_cases,
        audit_status=skill.audit_status,
        audit_score=skill.audit_score,
        audit_report=skill.audit_report,
        duplicate_of_id=skill.duplicate_of_id,
        duplicate_name=duplicate_name,
        content_revision=skill.content_revision,
        audited_revision=skill.audited_revision,
        audited_at=skill.audited_at,
        published_at=skill.published_at,
        last_error=skill.last_error,
        attempt_count=attempt_count,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


async def skill_preferences_response(
    session: AsyncSession,
    preferences: SkillAuditPreferences,
) -> SkillAuditPreferencesResponse:
    teacher_model_name = None
    if preferences.teacher_model_id is not None:
        teacher_model_name = await session.scalar(
            select(ModelEndpoint.name + " / " + ModelCacheEntry.model_id)
            .select_from(ModelCacheEntry)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .where(ModelCacheEntry.id == preferences.teacher_model_id)
        )
    return SkillAuditPreferencesResponse(
        auto_approve_threshold=preferences.auto_approve_threshold,
        max_self_edit_attempts=preferences.max_self_edit_attempts,
        max_skills_per_run=preferences.max_skills_per_run,
        teacher_rewrite_enabled=preferences.teacher_rewrite_enabled,
        teacher_model_id=preferences.teacher_model_id,
        teacher_model_name=teacher_model_name,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
    )


def skill_attempt_response(attempt: SkillAuditAttempt) -> SkillAuditAttemptResponse:
    return SkillAuditAttemptResponse.model_validate(attempt, from_attributes=True)


def set_skill_status(skill: Skill, status: str) -> None:
    skill.status = status
    if status == "published":
        skill.published_at = datetime.now(UTC)
    else:
        skill.published_at = None
