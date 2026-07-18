from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

AgentTriggerType = Literal[
    "manual",
    "once",
    "interval",
    "daily",
    "weekly",
    "communication",
]
AgentRunStatus = Literal[
    "queued",
    "running",
    "waiting_approval",
    "paused",
    "completed",
    "failed",
    "cancelled",
]
ApprovalPolicy = Literal["always", "tool_default", "never"]
ReplyApprovalPolicy = Literal["always", "never"]


class AgentToolScopeInput(BaseModel):
    tool_id: UUID
    approval_policy: ApprovalPolicy = "always"


class AgentToolScopeResponse(BaseModel):
    id: UUID
    tool_id: UUID
    server_name: str
    tool_name: str
    public_name: str
    approval_policy: ApprovalPolicy
    requires_confirmation: bool
    is_available: bool


class AgentCommunicationScopeInput(BaseModel):
    account_id: UUID
    allow_read: bool = True
    allow_reply: bool = False
    reply_approval_policy: ReplyApprovalPolicy = "always"

    @model_validator(mode="after")
    def validate_permissions(self) -> "AgentCommunicationScopeInput":
        if self.allow_reply and not self.allow_read:
            raise ValueError("Communication reply access requires read access")
        return self


class AgentCommunicationScopeResponse(BaseModel):
    id: UUID
    account_id: UUID
    account_name: str
    account_kind: Literal["imap", "discord"]
    allow_read: bool
    allow_reply: bool
    reply_approval_policy: ReplyApprovalPolicy


class AgentKnowledgeScopeInput(BaseModel):
    collection_id: UUID


class AgentKnowledgeScopeResponse(BaseModel):
    id: UUID
    collection_id: UUID
    collection_name: str


class AgentWrite(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    goal: str = Field(min_length=1, max_length=100_000)
    enabled: bool = True
    paused: bool = False
    trigger_type: AgentTriggerType = "manual"
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    schedule: dict[str, object] = Field(default_factory=dict)
    model_id: UUID | None = None
    persona_id: UUID | None = None
    use_default_persona: bool = False
    memory_enabled: bool = False
    rag_enabled: bool = False
    max_steps: int = Field(default=12, ge=1, le=100)
    max_model_calls: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=20, ge=0, le=500)
    max_runtime_seconds: int = Field(default=900, ge=10, le=86_400)
    max_estimated_tokens: int = Field(default=100_000, ge=100, le=10_000_000)
    max_estimated_cost_microusd: int | None = Field(default=None, ge=0)
    input_cost_per_million_microusd: int | None = Field(default=None, ge=0)
    output_cost_per_million_microusd: int | None = Field(default=None, ge=0)
    notify_on_completion: bool = True
    notify_on_failure: bool = True
    tools: list[AgentToolScopeInput] = Field(default_factory=list, max_length=256)
    communication_scopes: list[AgentCommunicationScopeInput] = Field(
        default_factory=list, max_length=100
    )
    knowledge_scopes: list[AgentKnowledgeScopeInput] = Field(
        default_factory=list, max_length=100
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("timezone")
    @classmethod
    def normalize_timezone(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_agent(self) -> "AgentWrite":
        if self.persona_id is not None and self.use_default_persona:
            raise ValueError("Choose a persona or the default persona, not both")
        if self.rag_enabled and not self.knowledge_scopes:
            raise ValueError("RAG requires at least one explicit knowledge collection")
        if self.max_estimated_cost_microusd is not None and (
            self.input_cost_per_million_microusd is None
            or self.output_cost_per_million_microusd is None
        ):
            raise ValueError("Cost limits require explicit input and output rates")
        tool_ids = [item.tool_id for item in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("Agent tools must be unique")
        account_ids = [item.account_id for item in self.communication_scopes]
        if len(account_ids) != len(set(account_ids)):
            raise ValueError("Communication accounts must be unique")
        collection_ids = [item.collection_id for item in self.knowledge_scopes]
        if len(collection_ids) != len(set(collection_ids)):
            raise ValueError("Knowledge collections must be unique")
        return self


class AgentCreate(AgentWrite):
    pass


class AgentUpdate(AgentWrite):
    pass


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: str
    goal: str
    enabled: bool
    paused: bool
    trigger_type: AgentTriggerType
    timezone: str
    schedule: dict[str, object]
    next_run_at: datetime | None
    model_id: UUID | None
    persona_id: UUID | None
    persona_name: str | None
    persona_description: str | None
    persona_instruction_role: str | None
    memory_enabled: bool
    rag_enabled: bool
    max_steps: int
    max_model_calls: int
    max_tool_calls: int
    max_runtime_seconds: int
    max_estimated_tokens: int
    max_estimated_cost_microusd: int | None
    input_cost_per_million_microusd: int | None
    output_cost_per_million_microusd: int | None
    notify_on_completion: bool
    notify_on_failure: bool
    tools: list[AgentToolScopeResponse]
    communication_scopes: list[AgentCommunicationScopeResponse]
    knowledge_scopes: list[AgentKnowledgeScopeResponse]
    last_enqueued_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentStepResponse(BaseModel):
    id: UUID
    run_id: UUID
    position: int
    kind: Literal["system", "model", "plan", "tool", "communication", "final"]
    status: Literal[
        "running",
        "waiting_approval",
        "completed",
        "failed",
        "denied",
        "skipped",
    ]
    summary: str
    content: str | None
    provider_model_id: str | None
    tool_id: UUID | None
    tool_call_id: str | None
    tool_name: str | None
    arguments: dict[str, object]
    result: str | None
    fingerprint: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentApprovalResponse(BaseModel):
    id: UUID
    run_id: UUID
    step_id: UUID
    action_type: Literal["tool", "communication_reply"]
    status: Literal["pending", "approved", "denied", "cancelled"]
    title: str
    details: str
    payload: dict[str, object]
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentRunResponse(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str
    trigger_source: Literal["manual", "schedule", "communication", "retry"]
    status: AgentRunStatus
    scheduled_for: datetime
    available_at: datetime
    lease_owner: str | None
    lease_expires_at: datetime | None
    goal_snapshot: str
    trigger_payload: dict[str, object]
    plan: list[dict[str, object]]
    persona_name: str | None
    requested_model_id: UUID | None
    provider_model_id: str | None
    max_steps: int
    max_model_calls: int
    max_tool_calls: int
    max_runtime_seconds: int
    max_estimated_tokens: int
    max_estimated_cost_microusd: int | None
    steps_used: int
    model_calls_used: int
    tool_calls_used: int
    estimated_tokens: int
    estimated_cost_microusd: int
    final_output: str | None
    error_code: str | None
    error_message: str | None
    pause_requested: bool
    cancel_requested: bool
    deadline_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[AgentStepResponse]
    approvals: list[AgentApprovalResponse]
    created_at: datetime
    updated_at: datetime


class AgentCommunicationRuleWrite(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    agent_id: UUID
    account_id: UUID
    enabled: bool = True
    sender_pattern: str | None = Field(default=None, max_length=500)
    source_ids: list[str] = Field(default_factory=list, max_length=100)
    body_contains: str | None = Field(default=None, max_length=500)
    require_mention: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("sender_pattern", "body_contains")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("source_ids")
    @classmethod
    def normalize_source_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Source IDs must be unique")
        return normalized


class AgentCommunicationRuleCreate(AgentCommunicationRuleWrite):
    pass


class AgentCommunicationRuleUpdate(AgentCommunicationRuleWrite):
    pass


class AgentCommunicationRuleResponse(BaseModel):
    id: UUID
    name: str
    agent_id: UUID
    agent_name: str
    account_id: UUID
    account_name: str
    enabled: bool
    sender_pattern: str | None
    source_ids: list[str]
    body_contains: str | None
    require_mention: bool
    created_at: datetime
    updated_at: datetime


class AgentControlUpdate(BaseModel):
    emergency_stop: bool
    reason: str = Field(default="", max_length=500)


class AgentControlResponse(BaseModel):
    emergency_stop: bool
    reason: str
    activated_at: datetime | None
    updated_at: datetime


class AgentRunActionResponse(BaseModel):
    status: AgentRunStatus
    run_id: UUID
