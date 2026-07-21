from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SkillStatus = Literal["draft", "published", "archived"]
SkillSourceType = Literal["manual", "imported", "generated"]
SkillAuditStatus = Literal[
    "pending",
    "auditing",
    "passed",
    "needs_review",
    "duplicate",
    "trivial",
    "failed",
]
SkillAuditVerdict = Literal["pass", "revise", "duplicate", "trivial", "failed"]
SkillAuditStage = Literal["audit", "self_edit", "teacher_rewrite", "recheck"]


class SkillTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str = Field(min_length=1, max_length=2_000)
    expected: str = Field(min_length=1, max_length=2_000)

    @field_validator("input", "expected")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class SkillWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(min_length=1, max_length=100_000)
    source_type: SkillSourceType = "manual"
    tags: list[str] = Field(default_factory=list, max_length=16)
    trigger_phrases: list[str] = Field(default_factory=list, max_length=24)
    test_cases: list[SkillTestCase] = Field(default_factory=list, max_length=12)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description", "instructions")
    @classmethod
    def normalize_block(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags", "trigger_phrases")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = " ".join(value.split())
            key = item.casefold()
            if not item or key in seen:
                continue
            if len(item) > 120:
                raise ValueError("Skill metadata entries cannot exceed 120 characters")
            seen.add(key)
            normalized.append(item)
        return normalized


class SkillCreate(SkillWrite):
    pass


class SkillUpdate(SkillWrite):
    pass


class SkillStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SkillStatus


class SkillAuditQueueResponse(BaseModel):
    skill_id: UUID
    task_id: UUID
    run_id: UUID
    status: Literal["queued"]


class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: str
    instructions: str
    status: SkillStatus
    source_type: SkillSourceType
    tags: list[str]
    trigger_phrases: list[str]
    test_cases: list[SkillTestCase]
    audit_status: SkillAuditStatus
    audit_score: int | None
    audit_report: dict[str, object]
    duplicate_of_id: UUID | None
    duplicate_name: str | None
    content_revision: int
    audited_revision: int | None
    audited_at: datetime | None
    published_at: datetime | None
    last_error: str | None
    attempt_count: int
    created_at: datetime
    updated_at: datetime


class SkillAuditPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    auto_approve_threshold: int = Field(default=85, ge=0, le=100)
    max_self_edit_attempts: int = Field(default=2, ge=0, le=5)
    max_skills_per_run: int = Field(default=10, ge=1, le=25)
    teacher_rewrite_enabled: bool = False
    teacher_model_id: UUID | None = None

    @model_validator(mode="after")
    def validate_teacher(self) -> "SkillAuditPreferencesUpdate":
        if self.teacher_rewrite_enabled and self.teacher_model_id is None:
            raise ValueError("Teacher rewrite requires a teacher model")
        return self


class SkillAuditPreferencesResponse(BaseModel):
    auto_approve_threshold: int
    max_self_edit_attempts: int
    max_skills_per_run: int
    teacher_rewrite_enabled: bool
    teacher_model_id: UUID | None
    teacher_model_name: str | None
    created_at: datetime
    updated_at: datetime


class SkillAuditAttemptResponse(BaseModel):
    id: UUID
    skill_id: UUID
    automation_run_id: UUID | None
    attempt_number: int
    stage: SkillAuditStage
    provider_model_id: str | None
    verdict: SkillAuditVerdict
    score: int | None
    passed_tests: int
    total_tests: int
    details: dict[str, object]
    created_at: datetime
