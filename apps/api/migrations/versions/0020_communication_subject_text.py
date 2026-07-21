"""Allow full communication message subjects.

Revision ID: 0020_communication_subject_text
Revises: 0019_product_templates
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_communication_subject_text"
down_revision: str | None = "0019_product_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "communication_messages",
        "subject",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE communication_messages
        SET subject = LEFT(subject, 500)
        WHERE LENGTH(subject) > 500
        """
    )
    op.alter_column(
        "communication_messages",
        "subject",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
