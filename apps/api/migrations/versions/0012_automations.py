"""Add scheduled automations and external integrations.

Revision ID: 0012_automations
Revises: 0011_images
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_automations"
down_revision: str | None = "0011_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("credential_names", sa.JSON(), nullable=False),
        sa.Column("last_test_status", sa.String(length=16), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "kind IN ('smtp', 'caldav', 'webhook')",
            name="ck_integration_connections_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "automations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("trigger_type", sa.String(length=24), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="UTC", nullable=False),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("persona_id", sa.Uuid(), nullable=True),
        sa.Column("persona_name", sa.String(length=120), nullable=True),
        sa.Column("persona_description", sa.String(length=500), nullable=True),
        sa.Column("persona_instructions", sa.Text(), nullable=True),
        sa.Column("persona_instruction_role", sa.String(length=16), nullable=True),
        sa.Column("notify_on_success", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_on_failure", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("retry_delay_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), server_default="300", nullable=False),
        sa.Column("webhook_token_hash", sa.String(length=64), nullable=True),
        sa.Column("webhook_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "trigger_type IN ('once', 'interval', 'daily', 'weekly', 'webhook')",
            name="ck_automations_trigger_type",
        ),
        sa.CheckConstraint(
            "max_attempts >= 1 AND max_attempts <= 10", name="ck_automations_attempts"
        ),
        sa.CheckConstraint("retry_delay_seconds >= 0", name="ck_automations_retry_delay"),
        sa.CheckConstraint("timeout_seconds > 0", name="ck_automations_timeout"),
        sa.ForeignKeyConstraint(["model_id"], ["model_cache_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("webhook_token_hash"),
    )
    op.create_index("ix_automations_next_run_at", "automations", ["next_run_at"])
    op.create_table(
        "automation_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("automation_id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "channel IN ('email', 'calendar', 'webhook')",
            name="ck_automation_deliveries_channel",
        ),
        sa.ForeignKeyConstraint(["automation_id"], ["automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integration_connections.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "automation_id", "position", name="uq_automation_deliveries_position"
        ),
    )
    op.create_index(
        "ix_automation_deliveries_automation_id",
        "automation_deliveries",
        ["automation_id"],
    )
    op.create_index(
        "ix_automation_deliveries_integration_id",
        "automation_deliveries",
        ["integration_id"],
    )
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("automation_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_source", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("occurrence_key", sa.String(length=256), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("retry_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("lease_owner", sa.String(length=160), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_payload", sa.JSON(), nullable=False),
        sa.Column("instruction_snapshot", sa.Text(), nullable=False),
        sa.Column("persona_name", sa.String(length=120), nullable=True),
        sa.Column("persona_instructions", sa.Text(), nullable=True),
        sa.Column("persona_instruction_role", sa.String(length=16), nullable=True),
        sa.Column("requested_model_id", sa.Uuid(), nullable=True),
        sa.Column("provider_model_id", sa.String(length=512), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("attempt_history", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "trigger_source IN ('schedule', 'manual', 'webhook', 'retry')",
            name="ck_automation_runs_trigger_source",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'delivering', 'completed', "
            "'completed_with_errors', 'failed', 'cancelled')",
            name="ck_automation_runs_status",
        ),
        sa.CheckConstraint("attempt >= 0", name="ck_automation_runs_attempt"),
        sa.CheckConstraint("max_attempts >= 1", name="ck_automation_runs_max_attempts"),
        sa.ForeignKeyConstraint(["automation_id"], ["automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requested_model_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("occurrence_key"),
    )
    op.create_index("ix_automation_runs_automation_id", "automation_runs", ["automation_id"])
    op.create_index("ix_automation_runs_status", "automation_runs", ["status"])
    op.create_index("ix_automation_runs_scheduled_for", "automation_runs", ["scheduled_for"])
    op.create_index("ix_automation_runs_available_at", "automation_runs", ["available_at"])
    op.create_index(
        "ix_automation_runs_lease_expires_at", "automation_runs", ["lease_expires_at"]
    )
    op.create_table(
        "automation_delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=True),
        sa.Column("integration_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("destination", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "channel IN ('email', 'calendar', 'webhook')",
            name="ck_automation_delivery_attempts_channel",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_automation_delivery_attempts_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["automation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["delivery_id"], ["automation_deliveries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integration_connections.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_delivery_attempts_run_id",
        "automation_delivery_attempts",
        ["run_id"],
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("automation_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "level IN ('info', 'success', 'error')", name="ck_notifications_level"
        ),
        sa.ForeignKeyConstraint(["automation_id"], ["automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["automation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_automation_id", "notifications", ["automation_id"])
    op.create_index("ix_notifications_run_id", "notifications", ["run_id"])
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("automation_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("delivery_key", sa.String(length=256), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["automation_id"], ["automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["automation_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "automation_id", "delivery_key", name="uq_webhook_deliveries_key"
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_automation_id", "webhook_deliveries", ["automation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_automation_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_notifications_run_id", table_name="notifications")
    op.drop_index("ix_notifications_automation_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(
        "ix_automation_delivery_attempts_run_id", table_name="automation_delivery_attempts"
    )
    op.drop_table("automation_delivery_attempts")
    op.drop_index("ix_automation_runs_lease_expires_at", table_name="automation_runs")
    op.drop_index("ix_automation_runs_available_at", table_name="automation_runs")
    op.drop_index("ix_automation_runs_scheduled_for", table_name="automation_runs")
    op.drop_index("ix_automation_runs_status", table_name="automation_runs")
    op.drop_index("ix_automation_runs_automation_id", table_name="automation_runs")
    op.drop_table("automation_runs")
    op.drop_index(
        "ix_automation_deliveries_integration_id", table_name="automation_deliveries"
    )
    op.drop_index(
        "ix_automation_deliveries_automation_id", table_name="automation_deliveries"
    )
    op.drop_table("automation_deliveries")
    op.drop_index("ix_automations_next_run_at", table_name="automations")
    op.drop_table("automations")
    op.drop_table("integration_connections")
