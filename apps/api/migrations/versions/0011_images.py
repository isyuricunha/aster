"""Add private image operations and media history.

Revision ID: 0011_images
Revises: 0010_memory_and_rag
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_images"
down_revision: str | None = "0010_memory_and_rag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "image_model_profiles",
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("supports_generation", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("supports_editing", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "supports_multiple_inputs", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("supports_masks", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("max_input_images", sa.Integer(), server_default="1", nullable=False),
        sa.Column("default_size", sa.String(length=32), nullable=True),
        sa.Column("default_quality", sa.String(length=32), nullable=True),
        sa.Column("default_output_format", sa.String(length=16), server_default="png", nullable=False),
        sa.Column("default_background", sa.String(length=32), nullable=True),
        sa.Column("default_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("default_input_fidelity", sa.String(length=32), nullable=True),
        sa.Column("provider_parameters", sa.JSON(), server_default="{}", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("max_input_images >= 1", name="ck_image_model_profiles_max_inputs"),
        sa.CheckConstraint("default_count >= 1", name="ck_image_model_profiles_default_count"),
        sa.ForeignKeyConstraint(["model_id"], ["model_cache_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("model_id"),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("media_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "source_type IN ('upload', 'generated', 'edited')",
            name="ck_media_assets_source_type",
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_media_assets_size"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_media_assets_dimensions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_media_assets_storage_key"),
    )
    op.create_index("ix_media_assets_content_sha256", "media_assets", ["content_sha256"])
    op.create_table(
        "image_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_message_id", sa.Uuid(), nullable=False),
        sa.Column("assistant_message_id", sa.Uuid(), nullable=False),
        sa.Column("model_cache_entry_id", sa.Uuid(), nullable=True),
        sa.Column("operation_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_model_id", sa.String(length=512), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("revised_prompt", sa.Text(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "operation_type IN ('generation', 'edit')",
            name="ck_image_operations_type",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_image_operations_status",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["model_cache_entry_id"], ["model_cache_entries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_image_operations_conversation_id", "image_operations", ["conversation_id"]
    )
    op.create_index(
        "ix_image_operations_user_message_id", "image_operations", ["user_message_id"]
    )
    op.create_index(
        "ix_image_operations_assistant_message_id", "image_operations", ["assistant_message_id"]
    )
    op.create_table(
        "image_operation_inputs",
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("input_type", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "input_type IN ('source', 'reference', 'mask')",
            name="ck_image_operation_inputs_type",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["image_operations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("operation_id", "asset_id"),
        sa.UniqueConstraint(
            "operation_id", "position", name="uq_image_operation_inputs_position"
        ),
    )
    op.create_table(
        "image_operation_outputs",
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["image_operations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("operation_id", "asset_id"),
        sa.UniqueConstraint(
            "operation_id", "position", name="uq_image_operation_outputs_position"
        ),
    )
    op.create_table(
        "message_attachments",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_type", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attachment_type IN ('input', 'output')",
            name="ck_message_attachments_type",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "asset_id"),
        sa.UniqueConstraint("message_id", "position", name="uq_message_attachments_position"),
    )


def downgrade() -> None:
    op.drop_table("message_attachments")
    op.drop_table("image_operation_outputs")
    op.drop_table("image_operation_inputs")
    op.drop_index("ix_image_operations_assistant_message_id", table_name="image_operations")
    op.drop_index("ix_image_operations_user_message_id", table_name="image_operations")
    op.drop_index("ix_image_operations_conversation_id", table_name="image_operations")
    op.drop_table("image_operations")
    op.drop_index("ix_media_assets_content_sha256", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_table("image_model_profiles")
