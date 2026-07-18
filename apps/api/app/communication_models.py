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


class CommunicationAccount(TimestampMixin, Base):
    __tablename__ = "communication_accounts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('imap', 'discord')",
            name="ck_communication_accounts_kind",
        ),
        CheckConstraint(
            "poll_interval_seconds >= 10 AND poll_interval_seconds <= 86400",
            name="ck_communication_accounts_poll_interval",
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
    external_identity: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    poll_interval_seconds: Mapped[int] = mapped_column(
        Integer, default=60, server_default="60", nullable=False
    )
    next_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    sync_lease_owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sync_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    last_sync_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CommunicationSourceCursor(TimestampMixin, Base):
    __tablename__ = "communication_source_cursors"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "source_key",
            name="uq_communication_source_cursor",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cursor_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )


class CommunicationThread(TimestampMixin, Base):
    __tablename__ = "communication_threads"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('email', 'discord')",
            name="ck_communication_threads_kind",
        ),
        CheckConstraint("unread_count >= 0", name="ck_communication_threads_unread"),
        UniqueConstraint(
            "account_id",
            "external_thread_id",
            name="uq_communication_thread_external",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    external_thread_id: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    participants: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    details: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    unread_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )


class CommunicationMessage(TimestampMixin, Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_communication_messages_direction",
        ),
        UniqueConstraint(
            "account_id",
            "external_message_id",
            name="uq_communication_message_external",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_threads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    external_message_id: Mapped[str] = mapped_column(String(512), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sender_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recipients: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_text: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CommunicationAttachment(TimestampMixin, Base):
    __tablename__ = "communication_attachments"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_communication_attachments_size"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    external_attachment_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)


class CommunicationRule(TimestampMixin, Base):
    __tablename__ = "communication_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"),
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
