"""Add stopped chat message status.

Revision ID: 0005_chat_controls
Revises: 0004_persistent_chat
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_chat_controls"
down_revision: str | None = "0004_persistent_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_chat_message_status", "chat_messages", type_="check")
    op.create_check_constraint(
        "ck_chat_message_status",
        "chat_messages",
        "status IN ('completed', 'streaming', 'failed', 'stopped')",
    )


def downgrade() -> None:
    op.execute("UPDATE chat_messages SET status = 'failed' WHERE status = 'stopped'")
    op.drop_constraint("ck_chat_message_status", "chat_messages", type_="check")
    op.create_check_constraint(
        "ck_chat_message_status",
        "chat_messages",
        "status IN ('completed', 'streaming', 'failed')",
    )
