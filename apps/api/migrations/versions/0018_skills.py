"""Add first-class skills and audit history.

Revision ID: 0018_skills
Revises: 0017_builtin_tasks
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_skills"
down_revision: str | None = "0017_builtin_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("source_type", sa.String(length=24), server_default="manual", nullable=False),
        sa.Column("tags", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("trigger_phrases", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("test_cases", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("audit_status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("audit_score", sa.Integer(), nullable=True),
        sa.Column("audit_report", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
        sa.Column("content_revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("audited_revision", sa.Integer(), nullable=True),
        sa.Column("audited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_skills_status",
        ),
        sa.CheckConstraint(
            "source_type IN ('manual', 'imported', 'generated')",
            name="ck_skills_source_type",
        ),
        sa.CheckConstraint(
            "audit_status IN "
            "('pending', 'auditing', 'passed', 'needs_review', 'duplicate', 'trivial', 'failed')",
            name="ck_skills_audit_status",
        ),
        sa.CheckConstraint(
            "audit_score IS NULL OR (audit_score >= 0 AND audit_score <= 100)",
            name="ck_skills_audit_score",
        ),
        sa.CheckConstraint("content_revision >= 1", name="ck_skills_content_revision"),
        sa.CheckConstraint(
            "audited_revision IS NULL OR audited_revision >= 1",
            name="ck_skills_audited_revision",
        ),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["skills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_status", "skills", ["status"])
    op.create_index("ix_skills_audit_status", "skills", ["audit_status"])
    op.create_index("ix_skills_duplicate_of_id", "skills", ["duplicate_of_id"])

    op.create_table(
        "skill_audit_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auto_approve_threshold", sa.Integer(), server_default="85", nullable=False),
        sa.Column("max_self_edit_attempts", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_skills_per_run", sa.Integer(), server_default="10", nullable=False),
        sa.Column("teacher_rewrite_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("teacher_model_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("id = 1", name="ck_skill_audit_preferences_singleton"),
        sa.CheckConstraint(
            "auto_approve_threshold >= 0 AND auto_approve_threshold <= 100",
            name="ck_skill_audit_preferences_threshold",
        ),
        sa.CheckConstraint(
            "max_self_edit_attempts >= 0 AND max_self_edit_attempts <= 5",
            name="ck_skill_audit_preferences_self_edits",
        ),
        sa.CheckConstraint(
            "max_skills_per_run >= 1 AND max_skills_per_run <= 25",
            name="ck_skill_audit_preferences_batch",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_model_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "skill_audit_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("automation_run_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("provider_model_id", sa.String(length=512), nullable=True),
        sa.Column("verdict", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "stage IN ('audit', 'self_edit', 'teacher_rewrite', 'recheck')",
            name="ck_skill_audit_attempts_stage",
        ),
        sa.CheckConstraint(
            "verdict IN ('pass', 'revise', 'duplicate', 'trivial', 'failed')",
            name="ck_skill_audit_attempts_verdict",
        ),
        sa.CheckConstraint("attempt_number >= 1", name="ck_skill_audit_attempts_number"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_skill_audit_attempts_score",
        ),
        sa.CheckConstraint("passed_tests >= 0", name="ck_skill_audit_attempts_passed_tests"),
        sa.CheckConstraint("total_tests >= 0", name="ck_skill_audit_attempts_total_tests"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["automation_run_id"], ["automation_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skill_audit_attempts_skill_id", "skill_audit_attempts", ["skill_id"])
    op.create_index(
        "ix_skill_audit_attempts_automation_run_id",
        "skill_audit_attempts",
        ["automation_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_skill_audit_attempts_automation_run_id",
        table_name="skill_audit_attempts",
    )
    op.drop_index("ix_skill_audit_attempts_skill_id", table_name="skill_audit_attempts")
    op.drop_table("skill_audit_attempts")
    op.drop_table("skill_audit_preferences")
    op.drop_index("ix_skills_duplicate_of_id", table_name="skills")
    op.drop_index("ix_skills_audit_status", table_name="skills")
    op.drop_index("ix_skills_status", table_name="skills")
    op.drop_table("skills")
