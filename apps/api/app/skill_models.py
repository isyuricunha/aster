from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import TimestampMixin


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_skills_status",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'imported', 'generated')",
            name="ck_skills_source_type",
        ),
        CheckConstraint(
            "audit_status IN "
            "('pending', 'auditing', 'passed', 'needs_review', 'duplicate', 'trivial', 'failed')",
            name="ck_skills_audit_status",
        ),
        CheckConstraint(
            "audit_score IS NULL OR (audit_score >= 0 AND audit_score <= 100)",
            name="ck_skills_audit_score",
        ),
        CheckConstraint("content_revision >= 1", name="ck_skills_content_revision"),
        CheckConstraint(
            "audited_revision IS NULL OR audited_revision >= 1",
            name="ck_skills_audited_revision",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(
        String(500), default="", server_default="", nullable=False
    )
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default="draft", server_default="draft", index=True, nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(24), default="manual", server_default="manual", nullable=False
    )
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    trigger_phrases: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default="[]", nullable=False
    )
    test_cases: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list, server_default="[]", nullable=False
    )
    audit_status: Mapped[str] = mapped_column(
        String(24), default="pending", server_default="pending", index=True, nullable=False
    )
    audit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audit_report: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, server_default="{}", nullable=False
    )
    duplicate_of_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), index=True, nullable=True
    )
    content_revision: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    audited_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SkillAuditPreferences(TimestampMixin, Base):
    __tablename__ = "skill_audit_preferences"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_skill_audit_preferences_singleton"),
        CheckConstraint(
            "auto_approve_threshold >= 0 AND auto_approve_threshold <= 100",
            name="ck_skill_audit_preferences_threshold",
        ),
        CheckConstraint(
            "max_self_edit_attempts >= 0 AND max_self_edit_attempts <= 5",
            name="ck_skill_audit_preferences_self_edits",
        ),
        CheckConstraint(
            "max_skills_per_run >= 1 AND max_skills_per_run <= 25",
            name="ck_skill_audit_preferences_batch",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    auto_approve_threshold: Mapped[int] = mapped_column(
        Integer, default=85, server_default="85", nullable=False
    )
    max_self_edit_attempts: Mapped[int] = mapped_column(
        Integer, default=2, server_default="2", nullable=False
    )
    max_skills_per_run: Mapped[int] = mapped_column(
        Integer, default=10, server_default="10", nullable=False
    )
    teacher_rewrite_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    teacher_model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )


class SkillAuditAttempt(Base):
    __tablename__ = "skill_audit_attempts"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('audit', 'self_edit', 'teacher_rewrite', 'recheck')",
            name="ck_skill_audit_attempts_stage",
        ),
        CheckConstraint(
            "verdict IN ('pass', 'revise', 'duplicate', 'trivial', 'failed')",
            name="ck_skill_audit_attempts_verdict",
        ),
        CheckConstraint("attempt_number >= 1", name="ck_skill_audit_attempts_number"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_skill_audit_attempts_score",
        ),
        CheckConstraint("passed_tests >= 0", name="ck_skill_audit_attempts_passed_tests"),
        CheckConstraint("total_tests >= 0", name="ck_skill_audit_attempts_total_tests"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    automation_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("automation_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_model_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_tests: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    total_tests: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, server_default="{}", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
