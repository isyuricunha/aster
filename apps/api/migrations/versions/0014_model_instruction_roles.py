"""Add provider instruction roles to model profiles.

Revision ID: 0014_model_instruction_roles
Revises: 0013_conversation_titles
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_model_instruction_roles"
down_revision: str | None = "0013_conversation_titles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "model_profiles",
        sa.Column(
            "instruction_role",
            sa.String(length=16),
            server_default="system",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_model_profiles_instruction_role",
        "model_profiles",
        "instruction_role IN ('system', 'developer')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_model_profiles_instruction_role",
        "model_profiles",
        type_="check",
    )
    op.drop_column("model_profiles", "instruction_role")
