"""Add model endpoints, cache, sync history, and preferences.

Revision ID: 0002_model_endpoints
Revises: 0001_baseline
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_model_endpoints"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_endpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "model_cache_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.String(length=512), nullable=False),
        sa.Column("is_manual", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["model_endpoints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "endpoint_id", "model_id", name="uq_model_cache_endpoint_model"
        ),
    )
    op.create_index(
        op.f("ix_model_cache_entries_endpoint_id"),
        "model_cache_entries",
        ["endpoint_id"],
        unique=False,
    )

    op.create_table(
        "model_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("models_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_model_sync_status"
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["model_endpoints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_sync_runs_endpoint_id"),
        "model_sync_runs",
        ["endpoint_id"],
        unique=False,
    )

    op.create_table(
        "model_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("primary_model_id", sa.Uuid(), nullable=True),
        sa.Column("utility_model_id", sa.Uuid(), nullable=True),
        sa.Column("image_model_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("id = 1", name="ck_model_preferences_singleton"),
        sa.ForeignKeyConstraint(
            ["image_model_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["primary_model_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["utility_model_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("model_preferences")
    op.drop_index(op.f("ix_model_sync_runs_endpoint_id"), table_name="model_sync_runs")
    op.drop_table("model_sync_runs")
    op.drop_index(op.f("ix_model_cache_entries_endpoint_id"), table_name="model_cache_entries")
    op.drop_table("model_cache_entries")
    op.drop_table("model_endpoints")
