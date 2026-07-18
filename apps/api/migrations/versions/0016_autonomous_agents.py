"""Add bounded autonomous agents.

Revision ID: 0016_autonomous_agents
Revises: 0015_communication_hub
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_autonomous_agents"
down_revision: str | None = "0015_communication_hub"
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
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("paused", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("trigger_type", sa.String(length=24), server_default="manual", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="UTC", nullable=False),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("persona_id", sa.Uuid(), nullable=True),
        sa.Column("persona_name", sa.String(length=120), nullable=True),
        sa.Column("persona_description", sa.String(length=500), nullable=True),
        sa.Column("persona_instructions", sa.Text(), nullable=True),
        sa.Column("persona_instruction_role", sa.String(length=16), nullable=True),
        sa.Column("memory_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rag_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("max_steps", sa.Integer(), server_default="12", nullable=False),
        sa.Column("max_model_calls", sa.Integer(), server_default="12", nullable=False),
        sa.Column("max_tool_calls", sa.Integer(), server_default="20", nullable=False),
        sa.Column("max_runtime_seconds", sa.Integer(), server_default="900", nullable=False),
        sa.Column("max_estimated_tokens", sa.Integer(), server_default="100000", nullable=False),
        sa.Column("max_estimated_cost_microusd", sa.Integer(), nullable=True),
        sa.Column("input_cost_per_million_microusd", sa.Integer(), nullable=True),
        sa.Column("output_cost_per_million_microusd", sa.Integer(), nullable=True),
        sa.Column("notify_on_completion", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_on_failure", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "trigger_type IN ('manual', 'once', 'interval', 'daily', 'weekly', 'communication')",
            name="ck_agents_trigger_type",
        ),
        sa.CheckConstraint("max_steps >= 1 AND max_steps <= 100", name="ck_agents_max_steps"),
        sa.CheckConstraint(
            "max_model_calls >= 1 AND max_model_calls <= 100",
            name="ck_agents_max_model_calls",
        ),
        sa.CheckConstraint(
            "max_tool_calls >= 0 AND max_tool_calls <= 500",
            name="ck_agents_max_tool_calls",
        ),
        sa.CheckConstraint(
            "max_runtime_seconds >= 10 AND max_runtime_seconds <= 86400",
            name="ck_agents_max_runtime",
        ),
        sa.CheckConstraint(
            "max_estimated_tokens >= 100 AND max_estimated_tokens <= 10000000",
            name="ck_agents_token_budget",
        ),
        sa.CheckConstraint(
            "max_estimated_cost_microusd IS NULL OR max_estimated_cost_microusd >= 0",
            name="ck_agents_cost_budget",
        ),
        sa.CheckConstraint(
            "input_cost_per_million_microusd IS NULL OR input_cost_per_million_microusd >= 0",
            name="ck_agents_input_cost",
        ),
        sa.CheckConstraint(
            "output_cost_per_million_microusd IS NULL OR output_cost_per_million_microusd >= 0",
            name="ck_agents_output_cost",
        ),
        sa.ForeignKeyConstraint(["model_id"], ["model_cache_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_agents_next_run_at", "agents", ["next_run_at"])

    op.create_table(
        "agent_tool_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.Column("approval_policy", sa.String(length=24), server_default="always", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "approval_policy IN ('always', 'tool_default', 'never')",
            name="ck_agent_tool_scopes_approval",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool_scope"),
    )
    op.create_index("ix_agent_tool_scopes_agent_id", "agent_tool_scopes", ["agent_id"])
    op.create_index("ix_agent_tool_scopes_tool_id", "agent_tool_scopes", ["tool_id"])

    op.create_table(
        "agent_communication_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("allow_read", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("allow_reply", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "reply_approval_policy", sa.String(length=16), server_default="always", nullable=False
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "reply_approval_policy IN ('always', 'never')",
            name="ck_agent_communication_reply_approval",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["communication_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "account_id", name="uq_agent_communication_scope"),
    )
    op.create_index(
        "ix_agent_communication_scopes_agent_id",
        "agent_communication_scopes",
        ["agent_id"],
    )
    op.create_index(
        "ix_agent_communication_scopes_account_id",
        "agent_communication_scopes",
        ["account_id"],
    )

    op.create_table(
        "agent_knowledge_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["knowledge_collections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "collection_id", name="uq_agent_knowledge_scope"),
    )
    op.create_index("ix_agent_knowledge_scopes_agent_id", "agent_knowledge_scopes", ["agent_id"])
    op.create_index(
        "ix_agent_knowledge_scopes_collection_id",
        "agent_knowledge_scopes",
        ["collection_id"],
    )

    op.create_table(
        "agent_communication_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sender_pattern", sa.String(length=500), nullable=True),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("body_contains", sa.String(length=500), nullable=True),
        sa.Column("require_mention", sa.Boolean(), server_default="false", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["communication_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_communication_rules_agent_id", "agent_communication_rules", ["agent_id"]
    )
    op.create_index(
        "ix_agent_communication_rules_account_id",
        "agent_communication_rules",
        ["account_id"],
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_source", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("occurrence_key", sa.String(length=256), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=160), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("goal_snapshot", sa.Text(), nullable=False),
        sa.Column("trigger_payload", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("persona_name", sa.String(length=120), nullable=True),
        sa.Column("persona_instructions", sa.Text(), nullable=True),
        sa.Column("persona_instruction_role", sa.String(length=16), nullable=True),
        sa.Column("requested_model_id", sa.Uuid(), nullable=True),
        sa.Column("provider_model_id", sa.String(length=512), nullable=True),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("max_model_calls", sa.Integer(), nullable=False),
        sa.Column("max_tool_calls", sa.Integer(), nullable=False),
        sa.Column("max_runtime_seconds", sa.Integer(), nullable=False),
        sa.Column("max_estimated_tokens", sa.Integer(), nullable=False),
        sa.Column("max_estimated_cost_microusd", sa.Integer(), nullable=True),
        sa.Column("input_cost_per_million_microusd", sa.Integer(), nullable=True),
        sa.Column("output_cost_per_million_microusd", sa.Integer(), nullable=True),
        sa.Column("steps_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("model_calls_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tool_calls_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_microusd", sa.Integer(), server_default="0", nullable=False),
        sa.Column("action_fingerprints", sa.JSON(), nullable=False),
        sa.Column("final_output", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("pause_requested", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "trigger_source IN ('manual', 'schedule', 'communication', 'retry')",
            name="ck_agent_runs_trigger_source",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'waiting_approval', 'paused', "
            "'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        sa.CheckConstraint("steps_used >= 0", name="ck_agent_runs_steps_used"),
        sa.CheckConstraint("model_calls_used >= 0", name="ck_agent_runs_model_calls_used"),
        sa.CheckConstraint("tool_calls_used >= 0", name="ck_agent_runs_tool_calls_used"),
        sa.CheckConstraint("estimated_tokens >= 0", name="ck_agent_runs_estimated_tokens"),
        sa.CheckConstraint("estimated_cost_microusd >= 0", name="ck_agent_runs_estimated_cost"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requested_model_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("occurrence_key"),
    )
    op.create_index("ix_agent_runs_agent_id", "agent_runs", ["agent_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_scheduled_for", "agent_runs", ["scheduled_for"])
    op.create_index("ix_agent_runs_available_at", "agent_runs", ["available_at"])
    op.create_index("ix_agent_runs_lease_expires_at", "agent_runs", ["lease_expires_at"])

    op.create_table(
        "agent_run_context_scopes",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("persona_id", sa.Uuid(), nullable=True),
        sa.Column("memory_enabled", sa.Boolean(), nullable=False),
        sa.Column("rag_enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("run_id"),
    )

    op.create_table(
        "agent_run_tool_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.Column("approval_policy", sa.String(length=24), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "approval_policy IN ('always', 'tool_default', 'never')",
            name="ck_agent_run_tool_scopes_approval",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "tool_id", name="uq_agent_run_tool_scope"),
    )
    op.create_index("ix_agent_run_tool_scopes_run_id", "agent_run_tool_scopes", ["run_id"])
    op.create_index("ix_agent_run_tool_scopes_tool_id", "agent_run_tool_scopes", ["tool_id"])

    op.create_table(
        "agent_run_communication_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("allow_read", sa.Boolean(), nullable=False),
        sa.Column("allow_reply", sa.Boolean(), nullable=False),
        sa.Column("reply_approval_policy", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "reply_approval_policy IN ('always', 'never')",
            name="ck_agent_run_communication_reply_approval",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["communication_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "account_id", name="uq_agent_run_communication_scope"),
    )
    op.create_index(
        "ix_agent_run_communication_scopes_run_id",
        "agent_run_communication_scopes",
        ["run_id"],
    )
    op.create_index(
        "ix_agent_run_communication_scopes_account_id",
        "agent_run_communication_scopes",
        ["account_id"],
    )

    op.create_table(
        "agent_run_knowledge_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["knowledge_collections.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "collection_id", name="uq_agent_run_knowledge_scope"),
    )
    op.create_index(
        "ix_agent_run_knowledge_scopes_run_id", "agent_run_knowledge_scopes", ["run_id"]
    )
    op.create_index(
        "ix_agent_run_knowledge_scopes_collection_id",
        "agent_run_knowledge_scopes",
        ["collection_id"],
    )

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("summary", sa.String(length=500), server_default="", nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("provider_model_id", sa.String(length=512), nullable=True),
        sa.Column("tool_id", sa.Uuid(), nullable=True),
        sa.Column("tool_call_id", sa.String(length=256), nullable=True),
        sa.Column("tool_name", sa.String(length=256), nullable=True),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "kind IN ('system', 'model', 'plan', 'tool', 'communication', 'final')",
            name="ck_agent_steps_kind",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'waiting_approval', 'completed', 'failed', 'denied', 'skipped')",
            name="ck_agent_steps_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "position", name="uq_agent_steps_position"),
    )
    op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"])

    op.create_table(
        "agent_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "action_type IN ('tool', 'communication_reply')",
            name="ck_agent_approvals_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'denied', 'cancelled')",
            name="ck_agent_approvals_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["agent_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_id"),
    )
    op.create_index("ix_agent_approvals_run_id", "agent_approvals", ["run_id"])

    op.create_table(
        "agent_control",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("emergency_stop", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reason", sa.String(length=500), server_default="", nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("id = 1", name="ck_agent_control_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "level IN ('info', 'success', 'error')",
            name="ck_agent_notifications_level",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_notifications_agent_id", "agent_notifications", ["agent_id"])
    op.create_index("ix_agent_notifications_run_id", "agent_notifications", ["run_id"])

    op.create_table(
        "agent_message_dispatches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["rule_id"], ["agent_communication_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["communication_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "message_id", name="uq_agent_message_dispatch"),
    )
    op.create_index("ix_agent_message_dispatches_rule_id", "agent_message_dispatches", ["rule_id"])
    op.create_index(
        "ix_agent_message_dispatches_message_id",
        "agent_message_dispatches",
        ["message_id"],
    )
    op.create_index("ix_agent_message_dispatches_run_id", "agent_message_dispatches", ["run_id"])


def downgrade() -> None:
    op.drop_table("agent_message_dispatches")
    op.drop_table("agent_notifications")
    op.drop_table("agent_control")
    op.drop_table("agent_approvals")
    op.drop_table("agent_steps")
    op.drop_table("agent_run_knowledge_scopes")
    op.drop_table("agent_run_communication_scopes")
    op.drop_table("agent_run_tool_scopes")
    op.drop_table("agent_run_context_scopes")
    op.drop_table("agent_runs")
    op.drop_table("agent_communication_rules")
    op.drop_table("agent_knowledge_scopes")
    op.drop_table("agent_communication_scopes")
    op.drop_table("agent_tool_scopes")
    op.drop_index("ix_agents_next_run_at", table_name="agents")
    op.drop_table("agents")
