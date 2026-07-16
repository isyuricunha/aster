from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
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


class PersonaSettings(TimestampMixin, Base):
    __tablename__ = "persona_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_persona_settings_singleton"),
        CheckConstraint(
            "instruction_role IN ('developer', 'system')",
            name="ck_persona_instruction_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(120), default="", server_default="", nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    instruction_role: Mapped[str] = mapped_column(
        String(16), default="developer", server_default="developer", nullable=False
    )


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(
        String(200), default="New chat", server_default="New chat", nullable=False
    )


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "position", name="uq_chat_message_position"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_message_role"),
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
    position: Mapped[int] = mapped_column(Integer, nullable=False)
