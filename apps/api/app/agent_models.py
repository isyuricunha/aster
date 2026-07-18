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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import TimestampMixin


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('manual', 'once', 'interval', 'daily', 'weekly', 'communication')",
            name="ck_agents_trigger_type",
        ),
        CheckConstraint("max_steps >= 1 AND max_steps <= 100", name="ck_agents_max_steps"),
        CheckConstraint(
            "max_model_calls >= 1 AND max_model_calls <= 100",
            name="ck_agents_max_model_calls",
        ),
        CheckConstraint(
            "max_tool_calls >= 0 AND max_tool_calls <= 500",
            name="ck_agents_max_tool_calls",
        ),
        CheckConstraint(
            "max_runtime_seconds >= 10 AND max_runtime_seconds <= 86400",
            name="ck_agents_max_runtime",
        ),
        CheckConstraint(
            "max_estimated_tokens >= 100 AND max_estimated_tokens <= 10000000",
            name="ck_agents_token_budget",
        ),
        CheckConstraint(
            "max_estimated_cost_microusd IS NULL OR max_estimated_cost_microusd >= 0",
            name="ck_agents_cost_budget",
        ),
        CheckConstraint(
            "input_cost_per_million_microusd IS NULL OR input_cost_per_million_microusd >= 0",
            name="ck_agents_input_cost",
        ),
        CheckConstraint(
            "output_cost_per_million_microusd IS NULL OR output_cost_per_million_microusd >= 0",
            name="ck_agents_output_cost",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(
        String(500), default="", server_default="", nullable=False
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    paused: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(
        String(24), default="manual", server_default="manual", nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String(64), default="UTC", server_default="UTC", nullable=False
    )
    schedule: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )
    persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    persona_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    persona_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    persona_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_instruction_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    memory_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    rag_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    max_steps: Mapped[int] = mapped_column(Integer, default=12, server_default="12", nullable=False)
    max_model_calls: Mapped[int] = mapped_column(
        Integer, default=12, server_default="12", nullable=False
    )
    max_tool_calls: Mapped[int] = mapped_column(
        Integer, default=20, server_default="20", nullable=False
    )
    max_runtime_seconds: Mapped[int] = mapped_column(
        Integer, default=900, server_default="900", nullable=False
    )
    max_estimated_tokens: Mapped[int] = mapped_column(
        Integer, default=100000, server_default="100000", nullable=False
    )
    max_estimated_cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_cost_per_million_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_cost_per_million_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notify_on_completion: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    notify_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    last_enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentToolScope(TimestampMixin, Base):
    __tablename__ = "agent_tool_scopes"
    __table_args__ = (
        UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool_scope"),
        CheckConstraint(
            "approval_policy IN ('always', 'tool_default', 'never')",
            name="ck_agent_tool_scopes_approval",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tool_id: Mapped[UUID] = mapped_column(
        ForeignKey("mcp_tools.id", ondelete="CASCADE"), index=True, nullable=False
    )
    approval_policy: Mapped[str] = mapped_column(
        String(24), default="always", server_default="always", nullable=False
    )


class AgentCommunicationScope(TimestampMixin, Base):
    __tablename__ = "agent_communication_scopes"
    __table_args__ = (
        UniqueConstraint("agent_id", "account_id", name="uq_agent_communication_scope"),
        CheckConstraint(
            "reply_approval_policy IN ('always', 'never')",
            name="ck_agent_communication_reply_approval",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    allow_read: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    allow_reply: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    reply_approval_policy: Mapped[str] = mapped_column(
        String(16), default="always", server_default="always", nullable=False
    )


class AgentKnowledgeScope(TimestampMixin, Base):
    __tablename__ = "agent_knowledge_scopes"
    __table_args__ = (
        UniqueConstraint("agent_id", "collection_id", name="uq_agent_knowledge_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )


class AgentCommunicationRule(TimestampMixin, Base):
    __tablename__ = "agent_communication_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    sender_pattern: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    body_contains: Mapped[str | None] = mapped_column(String(500), nullable=True)
    require_mention: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_source IN ('manual', 'schedule', 'communication', 'retry')",
            name="ck_agent_runs_trigger_source",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'waiting_approval', 'paused', "
            "'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        CheckConstraint("steps_used >= 0", name="ck_agent_runs_steps_used"),
        CheckConstraint("model_calls_used >= 0", name="ck_agent_runs_model_calls_used"),
        CheckConstraint("tool_calls_used >= 0", name="ck_agent_runs_tool_calls_used"),
        CheckConstraint("estimated_tokens >= 0", name="ck_agent_runs_estimated_tokens"),
        CheckConstraint("estimated_cost_microusd >= 0", name="ck_agent_runs_estimated_cost"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    trigger_source: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    occurrence_key: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    lease_owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    goal_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    plan: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    persona_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    persona_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_instruction_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requested_model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )
    provider_model_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    max_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    max_model_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_estimated_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_estimated_cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_cost_per_million_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_cost_per_million_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    model_calls_used: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    tool_calls_used: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    estimated_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    estimated_cost_microusd: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    action_fingerprints: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pause_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentStep(TimestampMixin, Base):
    __tablename__ = "agent_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "position", name="uq_agent_steps_position"),
        CheckConstraint(
            "kind IN ('system', 'model', 'plan', 'tool', 'communication', 'final')",
            name="ck_agent_steps_kind",
        ),
        CheckConstraint(
            "status IN ('running', 'waiting_approval', 'completed', 'failed', 'denied', 'skipped')",
            name="ck_agent_steps_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_model_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tool_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mcp_tools.id", ondelete="SET NULL"), nullable=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    arguments: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentApproval(TimestampMixin, Base):
    __tablename__ = "agent_approvals"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('tool', 'communication_reply')",
            name="ck_agent_approvals_action_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'denied', 'cancelled')",
            name="ck_agent_approvals_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_steps.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending", nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentControl(TimestampMixin, Base):
    __tablename__ = "agent_control"
    __table_args__ = (CheckConstraint("id = 1", name="ck_agent_control_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    emergency_stop: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    reason: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
