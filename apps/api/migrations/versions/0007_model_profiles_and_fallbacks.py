"""Add model profiles and fallback routing.

Revision ID: 0007_model_profiles
Revises: 0006_single_owner_auth
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_model_profiles"
down_revision: str | None = "0006_single_owner_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_profiles",
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "token_parameter",
            sa.String(length=32),
            server_default="max_tokens",
            nullable=False,
        ),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("reasoning_effort", sa.String(length=16), nullable=True),
        sa.Column("supports_chat", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("supports_streaming", sa.Boolean(), server_default="true", nullable=False),
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
        sa.CheckConstraint(
            "context_window IS NULL OR context_window > 0",
            name="ck_model_profiles_context_window",
        ),
        sa.CheckConstraint(
            "max_output_tokens IS NULL OR max_output_tokens > 0",
            name="ck_model_profiles_max_output_tokens",
        ),
        sa.CheckConstraint(
            "temperature IS NULL OR (temperature >= 0 AND temperature <= 2)",
            name="ck_model_profiles_temperature",
        ),
        sa.CheckConstraint(
            "top_p IS NULL OR (top_p > 0 AND top_p <= 1)",
            name="ck_model_profiles_top_p",
        ),
        sa.CheckConstraint(
            "token_parameter IN ('none', 'max_tokens', 'max_completion_tokens')",
            name="ck_model_profiles_token_parameter",
        ),
        sa.CheckConstraint(
            "reasoning_effort IS NULL OR reasoning_effort IN "
            "('minimal', 'low', 'medium', 'high', 'xhigh')",
            name="ck_model_profiles_reasoning_effort",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"], ["model_cache_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("model_id"),
    )
    op.create_table(
        "model_fallback_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("position >= 0", name="ck_model_fallback_position"),
        sa.ForeignKeyConstraint(
            ["model_id"], ["model_cache_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", name="uq_model_fallback_model"),
        sa.UniqueConstraint("position", name="uq_model_fallback_position"),
    )


def downgrade() -> None:
    op.drop_table("model_fallback_entries")
    op.drop_table("model_profiles")
