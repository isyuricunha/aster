"""Add email and Discord communication hub.

Revision ID: 0015_communication_hub
Revises: 0014_model_instruction_roles
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_communication_hub"
down_revision: str | None = "0014_model_instruction_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_automations_trigger_type", "automations", type_="check")
    op.create_check_constraint(
        "ck_automations_trigger_type",
        "automations",
        "trigger_type IN ('once', 'interval', 'daily', 'weekly', 'webhook', 'communication')",
    )
    op.drop_constraint(
        "ck_automation_runs_trigger_source",
        "automation_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_automation_runs_trigger_source",
        "automation_runs",
        "trigger_source IN ('schedule', 'manual', 'webhook', 'communication', 'retry')",
    )

    op.create_table(
        "communication_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("credential_names", sa.JSON(), nullable=False),
        sa.Column("external_identity", sa.JSON(), nullable=False),
        sa.Column(
            "poll_interval_seconds",
            sa.Integer(),
            server_default="60",
            nullable=False,
        ),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_lease_owner", sa.String(length=160), nullable=True),
        sa.Column("sync_lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=24), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
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
            "kind IN ('imap', 'discord')",
            name="ck_communication_accounts_kind",
        ),
        sa.CheckConstraint(
            "poll_interval_seconds >= 10 AND poll_interval_seconds <= 86400",
            name="ck_communication_accounts_poll_interval",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_communication_accounts_next_sync_at",
        "communication_accounts",
        ["next_sync_at"],
    )
    op.create_index(
        "ix_communication_accounts_sync_lease_expires_at",
        "communication_accounts",
        ["sync_lease_expires_at"],
    )

    op.create_table(
        "communication_source_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("source_key", sa.String(length=512), nullable=False),
        sa.Column("cursor_value", sa.String(length=512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["communication_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "source_key",
            name="uq_communication_source_cursor",
        ),
    )
    op.create_index(
        "ix_communication_source_cursors_account_id",
        "communication_source_cursors",
        ["account_id"],
    )

    op.create_table(
        "communication_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("external_thread_id", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("participants", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("unread_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            "kind IN ('email', 'discord')",
            name="ck_communication_threads_kind",
        ),
        sa.CheckConstraint(
            "unread_count >= 0",
            name="ck_communication_threads_unread",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["communication_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "external_thread_id",
            name="uq_communication_thread_external",
        ),
    )
    op.create_index(
        "ix_communication_threads_account_id",
        "communication_threads",
        ["account_id"],
    )
    op.create_index(
        "ix_communication_threads_last_message_at",
        "communication_threads",
        ["last_message_at"],
    )

    op.create_table(
        "communication_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("external_message_id", sa.String(length=512), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.String(length=512), nullable=True),
        sa.Column("sender_name", sa.String(length=300), nullable=True),
        sa.Column("sender_address", sa.String(length=512), nullable=True),
        sa.Column("recipients", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("content_text", sa.Text(), server_default="", nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            "direction IN ('inbound', 'outbound')",
            name="ck_communication_messages_direction",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["communication_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["communication_threads.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "external_message_id",
            name="uq_communication_message_external",
        ),
    )
    op.create_index(
        "ix_communication_messages_account_id",
        "communication_messages",
        ["account_id"],
    )
    op.create_index(
        "ix_communication_messages_thread_id",
        "communication_messages",
        ["thread_id"],
    )
    op.create_index(
        "ix_communication_messages_sent_at",
        "communication_messages",
        ["sent_at"],
    )

    op.create_table(
        "communication_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("external_attachment_id", sa.String(length=512), nullable=True),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
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
            "size_bytes >= 0",
            name="ck_communication_attachments_size",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["communication_messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_communication_attachments_message_id",
        "communication_attachments",
        ["message_id"],
    )

    op.create_table(
        "communication_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("automation_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sender_pattern", sa.String(length=500), nullable=True),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("body_contains", sa.String(length=500), nullable=True),
        sa.Column("require_mention", sa.Boolean(), server_default="false", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["communication_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["automation_id"],
            ["automations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_communication_rules_account_id",
        "communication_rules",
        ["account_id"],
    )
    op.create_index(
        "ix_communication_rules_automation_id",
        "communication_rules",
        ["automation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_communication_rules_automation_id", table_name="communication_rules")
    op.drop_index("ix_communication_rules_account_id", table_name="communication_rules")
    op.drop_table("communication_rules")
    op.drop_index(
        "ix_communication_attachments_message_id",
        table_name="communication_attachments",
    )
    op.drop_table("communication_attachments")
    op.drop_index("ix_communication_messages_sent_at", table_name="communication_messages")
    op.drop_index("ix_communication_messages_thread_id", table_name="communication_messages")
    op.drop_index("ix_communication_messages_account_id", table_name="communication_messages")
    op.drop_table("communication_messages")
    op.drop_index("ix_communication_threads_last_message_at", table_name="communication_threads")
    op.drop_index("ix_communication_threads_account_id", table_name="communication_threads")
    op.drop_table("communication_threads")
    op.drop_index(
        "ix_communication_source_cursors_account_id",
        table_name="communication_source_cursors",
    )
    op.drop_table("communication_source_cursors")
    op.drop_index(
        "ix_communication_accounts_sync_lease_expires_at",
        table_name="communication_accounts",
    )
    op.drop_index(
        "ix_communication_accounts_next_sync_at",
        table_name="communication_accounts",
    )
    op.drop_table("communication_accounts")

    op.drop_constraint(
        "ck_automation_runs_trigger_source",
        "automation_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_automation_runs_trigger_source",
        "automation_runs",
        "trigger_source IN ('schedule', 'manual', 'webhook', 'retry')",
    )
    op.drop_constraint("ck_automations_trigger_type", "automations", type_="check")
    op.create_check_constraint(
        "ck_automations_trigger_type",
        "automations",
        "trigger_type IN ('once', 'interval', 'daily', 'weekly', 'webhook')",
    )
