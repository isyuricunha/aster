"""Add built-in task metadata.

Revision ID: 0017_builtin_tasks
Revises: 0016_autonomous_agents
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_builtin_tasks"
down_revision: str | None = "0016_autonomous_agents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("automations", sa.Column("builtin_key", sa.String(length=64), nullable=True))
    op.add_column(
        "automations",
        sa.Column(
            "state",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_automations_builtin_key",
        "automations",
        ["builtin_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_automations_builtin_key", table_name="automations")
    op.drop_column("automations", "state")
    op.drop_column("automations", "builtin_key")
