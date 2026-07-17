"""Add tool calling and MCP configuration.

Revision ID: 0009_tools_and_mcp
Revises: 0008_multiple_personas
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_tools_and_mcp"
down_revision: str | None = "0008_multiple_personas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("command", sa.String(length=1024), nullable=True),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("encrypted_headers", sa.Text(), nullable=True),
        sa.Column("header_names", sa.JSON(), nullable=False),
        sa.Column("encrypted_environment", sa.Text(), nullable=True),
        sa.Column("environment_names", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), server_default="30", nullable=False),
        sa.Column("last_sync_status", sa.String(length=16), nullable=True),
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
            "transport IN ('streamable_http', 'stdio')",
            name="ck_mcp_servers_transport",
        ),
        sa.CheckConstraint("timeout_seconds > 0", name="ck_mcp_servers_timeout"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "mcp_tools",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("public_name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("default_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("requires_confirmation", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_name", name="uq_mcp_tools_public_name"),
        sa.UniqueConstraint("server_id", "name", name="uq_mcp_tools_server_name"),
    )
    op.create_index("ix_mcp_tools_server_id", "mcp_tools", ["server_id"])
    op.create_table(
        "conversation_tools",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "tool_id"),
    )

    op.drop_constraint("ck_chat_message_role", "chat_messages", type_="check")
    op.create_check_constraint(
        "ck_chat_message_role",
        "chat_messages",
        "role IN ('user', 'assistant', 'tool')",
    )
    op.add_column("chat_messages", sa.Column("tool_calls", sa.JSON(), nullable=True))
    op.add_column(
        "chat_messages", sa.Column("tool_call_id", sa.String(length=256), nullable=True)
    )
    op.add_column("chat_messages", sa.Column("tool_name", sa.String(length=256), nullable=True))

    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("assistant_message_id", sa.Uuid(), nullable=False),
        sa.Column("tool_message_id", sa.Uuid(), nullable=True),
        sa.Column("tool_id", sa.Uuid(), nullable=True),
        sa.Column("tool_call_id", sa.String(length=256), nullable=False),
        sa.Column("tool_name", sa.String(length=256), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('pending_confirmation', 'running', 'completed', 'failed', 'denied')",
            name="ck_tool_executions_status",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tool_message_id"], ["chat_messages.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id", "tool_call_id", name="uq_tool_execution_conversation_call"
        ),
    )
    op.create_index(
        "ix_tool_executions_assistant_message_id",
        "tool_executions",
        ["assistant_message_id"],
    )
    op.create_index(
        "ix_tool_executions_conversation_id", "tool_executions", ["conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tool_executions_conversation_id", table_name="tool_executions")
    op.drop_index("ix_tool_executions_assistant_message_id", table_name="tool_executions")
    op.drop_table("tool_executions")
    op.execute("DELETE FROM chat_messages WHERE role = 'tool'")
    op.drop_column("chat_messages", "tool_name")
    op.drop_column("chat_messages", "tool_call_id")
    op.drop_column("chat_messages", "tool_calls")
    op.drop_constraint("ck_chat_message_role", "chat_messages", type_="check")
    op.create_check_constraint(
        "ck_chat_message_role",
        "chat_messages",
        "role IN ('user', 'assistant')",
    )
    op.drop_table("conversation_tools")
    op.drop_index("ix_mcp_tools_server_id", table_name="mcp_tools")
    op.drop_table("mcp_tools")
    op.drop_table("mcp_servers")
