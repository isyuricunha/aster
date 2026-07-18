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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import TimestampMixin


class IntegrationConnection(TimestampMixin, Base):
    __tablename__ = "integration_connections"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('smtp', 'caldav', 'webhook')",
            name="ck_integration_connections_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_names: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    last_test_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Automation(TimestampMixin, Base):
    __tablename__ = "automations"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('once', 'interval', 'daily', 'weekly', 'webhook', "
            "'communication')",
            name="ck_automations_trigger_type",
        ),
        CheckConstraint("max_attempts >= 1 AND max_attempts <= 10", name="ck_automations_attempts"),
        CheckConstraint("retry_delay_seconds >= 0", name="ck_automations_retry_delay"),
        CheckConstraint("timeout_seconds > 0", name="ck_automations_timeout"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(
        String(500), default="", server_default="", nullable=False
    )
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(24), nullable=False)
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
    notify_on_success: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    notify_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3", nullable=False
    )
    retry_delay_seconds: Mapped[int] = mapped_column(
        Integer, default=60, server_default="60", nullable=False
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=300, server_default="300", nullable=False
    )
    webhook_token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    webhook_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_enqueued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutomationDelivery(TimestampMixin, Base):
    __tablename__ = "automation_deliveries"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'calendar', 'webhook')",
            name="ck_automation_deliveries_channel",
        ),
        UniqueConstraint(
            "automation_id", "position", name="uq_automation_deliveries_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class AutomationRun(TimestampMixin, Base):
    __tablename__ = "automation_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_source IN ('schedule', 'manual', 'webhook', 'communication', 'retry')",
            name="ck_automation_runs_trigger_source",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'delivering', 'completed', "
            "'completed_with_errors', 'failed', 'cancelled')",
            name="ck_automation_runs_status",
        ),
        CheckConstraint("attempt >= 0", name="ck_automation_runs_attempt"),
        CheckConstraint("max_attempts >= 1", name="ck_automation_runs_max_attempts"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"), index=True, nullable=False
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
    attempt: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    trigger_payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    instruction_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    persona_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    persona_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_instruction_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requested_model_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )
    provider_model_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_history: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutomationDeliveryAttempt(TimestampMixin, Base):
    __tablename__ = "automation_delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'calendar', 'webhook')",
            name="ck_automation_delivery_attempts_channel",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_automation_delivery_attempts_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("automation_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    delivery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("automation_deliveries.id", ondelete="SET NULL"), nullable=True
    )
    integration_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "level IN ('info', 'success', 'error')", name="ck_notifications_level"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    automation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("automation_runs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "automation_id", "delivery_key", name="uq_webhook_deliveries_key"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("automation_runs.id", ondelete="SET NULL"), nullable=True
    )
    delivery_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    headers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
