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


class ImageModelProfile(TimestampMixin, Base):
    __tablename__ = "image_model_profiles"
    __table_args__ = (
        CheckConstraint("max_input_images >= 1", name="ck_image_model_profiles_max_inputs"),
        CheckConstraint("default_count >= 1", name="ck_image_model_profiles_default_count"),
    )

    model_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="CASCADE"), primary_key=True
    )
    supports_generation: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    supports_editing: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    supports_multiple_inputs: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    supports_masks: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    max_input_images: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    default_size: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_output_format: Mapped[str] = mapped_column(
        String(16), default="png", server_default="png", nullable=False
    )
    default_background: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_count: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    default_input_fidelity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_parameters: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, server_default="{}", nullable=False
    )


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('upload', 'generated', 'edited')",
            name="ck_media_assets_source_type",
        ),
        CheckConstraint("size_bytes > 0", name="ck_media_assets_size"),
        CheckConstraint("width > 0 AND height > 0", name="ck_media_assets_dimensions"),
        UniqueConstraint("storage_key", name="uq_media_assets_storage_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)


class ImageOperation(TimestampMixin, Base):
    __tablename__ = "image_operations"
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('generation', 'edit')",
            name="ck_image_operations_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_image_operations_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assistant_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    model_cache_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_cache_entries.id", ondelete="SET NULL"), nullable=True
    )
    operation_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_model_id: Mapped[str] = mapped_column(String(512), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    revised_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImageOperationInput(Base):
    __tablename__ = "image_operation_inputs"
    __table_args__ = (
        CheckConstraint(
            "input_type IN ('source', 'reference', 'mask')",
            name="ck_image_operation_inputs_type",
        ),
        UniqueConstraint("operation_id", "position", name="uq_image_operation_inputs_position"),
    )

    operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("image_operations.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), primary_key=True
    )
    input_type: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ImageOperationOutput(Base):
    __tablename__ = "image_operation_outputs"
    __table_args__ = (
        UniqueConstraint("operation_id", "position", name="uq_image_operation_outputs_position"),
    )

    operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("image_operations.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class MessageAttachment(Base):
    __tablename__ = "message_attachments"
    __table_args__ = (
        CheckConstraint(
            "attachment_type IN ('input', 'output')",
            name="ck_message_attachments_type",
        ),
        UniqueConstraint("message_id", "position", name="uq_message_attachments_position"),
    )

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"), primary_key=True
    )
    attachment_type: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
