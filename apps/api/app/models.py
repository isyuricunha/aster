from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("id = 1", name="ck_users_single_owner"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModelEndpoint(TimestampMixin, Base):
    __tablename__ = "model_endpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class ModelCacheEntry(TimestampMixin, Base):
    __tablename__ = "model_cache_entries"
    __table_args__ = (
        UniqueConstraint("endpoint_id", "model_id", name="uq_model_cache_endpoint_model"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_endpoints.id", ondelete="CASCADE"), index=True, nullable=False
    )
    model_id: Mapped[str] = mapped_column(String(512), nullable=False)
    is_manual: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModelProfile(TimestampMixin, Base):
    __tablename__ = "model_profiles"
    __table_args__ = (
        CheckConstraint(
            "context_window IS NULL OR context_window > 0",
            name="ck_model_profiles_context_window",
        ),
        CheckConstraint(
            "max_output_tokens IS NULL OR max_output_tokens > 0",
            name="ck_model_profiles_max_output_tokens",
        ),
        CheckConstraint(
            "temperature IS NULL OR (temperature >= 0 AND temperature <= 2)",
            name="ck_model_profiles_temperature",
        ),
        CheckConstraint(
            "top_p IS NULL OR (top_p > 0 AND top_p <= 1)",
            name="ck_model_profiles_top_p",
        ),
        CheckConstraint(
            "token_parameter IN ('none', 'max_tokens', 'max_completion_tokens')",
            name="ck_model_profiles_token_parameter",
        ),
        CheckConstraint(
            "reasoning_effort IS NULL OR reasoning_effort IN "
            "('minimal', 'low', 'medium', 'high', 'xhigh')",
            name="ck_model_profiles_reasoning_effort",
        ),
        CheckConstraint(
            "instruction_role IN ('system', 'developer')",
            name="ck_model_profiles_instruction_role",
        ),
    )

    model_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_parameter: Mapped[str] = mapped_column(
        String(32), default="max_tokens", server_default="max_tokens", nullable=False
    )
    instruction_role: Mapped[str] = mapped_column(
        String(16), default="system", server_default="system", nullable=False
    )
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning_effort: Mapped[str | None] = mapped_column(String(16), nullable=True)
    supports_chat: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    supports_streaming: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class ModelSyncRun(Base):
    __tablename__ = "model_sync_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_model_sync_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_endpoints.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    models_found: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModelPreferences(TimestampMixin, Base):
    __tablename__ = "model_preferences"
    __table_args__ = (CheckConstraint("id = 1", name="ck_model_preferences_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    primary_model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )
    utility_model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )
    image_model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )


class ModelFallbackEntry(TimestampMixin, Base):
    __tablename__ = "model_fallback_entries"
    __table_args__ = (
        UniqueConstraint("model_id", name="uq_model_fallback_model"),
        UniqueConstraint("position", name="uq_model_fallback_position"),
        CheckConstraint("position >= 0", name="ck_model_fallback_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Persona(TimestampMixin, Base):
    __tablename__ = "personas"
    __table_args__ = (
        CheckConstraint(
            "instruction_role IN ('developer', 'system')",
            name="ck_personas_instruction_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(
        String(500), default="", server_default="", nullable=False
    )
    instructions: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    instruction_role: Mapped[str] = mapped_column(
        String(16), default="developer", server_default="developer", nullable=False
    )


class PersonaPreferences(TimestampMixin, Base):
    __tablename__ = "persona_preferences"
    __table_args__ = (CheckConstraint("id = 1", name="ck_persona_preferences_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )


class McpServer(TimestampMixin, Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (
        CheckConstraint(
            "transport IN ('streamable_http', 'stdio')",
            name="ck_mcp_servers_transport",
        ),
        CheckConstraint("timeout_seconds > 0", name="ck_mcp_servers_timeout"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    transport: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    command: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    arguments: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    encrypted_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    header_names: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    encrypted_environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment_names: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30", nullable=False
    )
    last_sync_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class McpTool(TimestampMixin, Base):
    __tablename__ = "mcp_tools"
    __table_args__ = (
        UniqueConstraint("server_id", "name", name="uq_mcp_tools_server_name"),
        UniqueConstraint("public_name", name="uq_mcp_tools_public_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    server_id: Mapped[UUID] = mapped_column(
        ForeignKey("mcp_servers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    public_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    input_schema: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    default_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "persona_instruction_role IS NULL OR "
            "persona_instruction_role IN ('developer', 'system')",
            name="ck_conversation_persona_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(
        String(200), default="New chat", server_default="New chat", nullable=False
    )
    persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"), index=True, nullable=True
    )
    persona_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    persona_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    persona_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_instruction_role: Mapped[str | None] = mapped_column(String(16), nullable=True)


class ConversationTool(Base):
    __tablename__ = "conversation_tools"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    tool_id: Mapped[UUID] = mapped_column(
        ForeignKey("mcp_tools.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "position", name="uq_chat_message_position"),
        CheckConstraint("role IN ('user', 'assistant', 'tool')", name="ck_chat_message_role"),
        CheckConstraint(
            "status IN ('completed', 'streaming', 'failed', 'stopped')",
            name="ck_chat_message_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tool_calls: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ToolExecution(TimestampMixin, Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "tool_call_id", name="uq_tool_execution_conversation_call"
        ),
        CheckConstraint(
            "status IN ('pending_confirmation', 'running', 'completed', 'failed', 'denied')",
            name="ck_tool_executions_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assistant_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tool_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True
    )
    tool_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mcp_tools.id", ondelete="SET NULL"), nullable=True
    )
    tool_call_id: Mapped[str] = mapped_column(String(256), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(256), nullable=False)
    arguments: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
