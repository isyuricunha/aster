"""Add multiple personas and conversation snapshots.

Revision ID: 0008_multiple_personas
Revises: 0007_model_profiles
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_multiple_personas"
down_revision: str | None = "0007_model_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_PERSONA_ID = "00000000-0000-0000-0000-000000000011"


def upgrade() -> None:
    op.create_table(
        "personas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("instructions", sa.Text(), server_default="", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "instruction_role",
            sa.String(length=16),
            server_default="developer",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "instruction_role IN ('developer', 'system')",
            name="ck_personas_instruction_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "persona_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("default_persona_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint("id = 1", name="ck_persona_preferences_singleton"),
        sa.ForeignKeyConstraint(
            ["default_persona_id"], ["personas.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("conversations", sa.Column("persona_id", sa.Uuid(), nullable=True))
    op.add_column(
        "conversations", sa.Column("persona_name", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("persona_description", sa.String(length=500), nullable=True),
    )
    op.add_column("conversations", sa.Column("persona_instructions", sa.Text(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("persona_instruction_role", sa.String(length=16), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_persona_id",
        "conversations",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_persona_id", "conversations", ["persona_id"])
    op.create_check_constraint(
        "ck_conversation_persona_role",
        "conversations",
        "persona_instruction_role IS NULL OR "
        "persona_instruction_role IN ('developer', 'system')",
    )

    op.execute(
        f"""
        INSERT INTO personas (
            id,
            name,
            description,
            instructions,
            enabled,
            instruction_role,
            created_at,
            updated_at
        )
        SELECT
            CAST('{LEGACY_PERSONA_ID}' AS UUID),
            CASE WHEN btrim(name) = '' THEN 'Personal Assistant' ELSE name END,
            'Migrated from the original global persona.',
            instructions,
            enabled,
            instruction_role,
            created_at,
            updated_at
        FROM persona_settings
        WHERE id = 1
          AND (enabled OR btrim(name) <> '' OR btrim(instructions) <> '')
        """
    )
    op.execute("INSERT INTO persona_preferences (id, default_persona_id) VALUES (1, NULL)")
    op.execute(
        f"""
        UPDATE persona_preferences
        SET default_persona_id = CAST('{LEGACY_PERSONA_ID}' AS UUID)
        WHERE id = 1
          AND EXISTS (
              SELECT 1
              FROM personas
              WHERE id = CAST('{LEGACY_PERSONA_ID}' AS UUID)
                AND enabled
          )
        """
    )
    op.execute(
        f"""
        UPDATE conversations
        SET
            persona_id = migrated.id,
            persona_name = migrated.name,
            persona_description = migrated.description,
            persona_instructions = migrated.instructions,
            persona_instruction_role = migrated.instruction_role
        FROM personas AS migrated
        WHERE migrated.id = CAST('{LEGACY_PERSONA_ID}' AS UUID)
          AND migrated.enabled
        """
    )
    op.drop_table("persona_settings")


def downgrade() -> None:
    op.create_table(
        "persona_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("instructions", sa.Text(), server_default="", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "instruction_role",
            sa.String(length=16),
            server_default="developer",
            nullable=False,
        ),
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
        sa.CheckConstraint("id = 1", name="ck_persona_settings_singleton"),
        sa.CheckConstraint(
            "instruction_role IN ('developer', 'system')",
            name="ck_persona_instruction_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO persona_settings (
            id,
            name,
            instructions,
            enabled,
            instruction_role,
            created_at,
            updated_at
        )
        SELECT
            1,
            COALESCE(personas.name, ''),
            COALESCE(personas.instructions, ''),
            COALESCE(personas.enabled, false),
            COALESCE(personas.instruction_role, 'developer'),
            COALESCE(personas.created_at, now()),
            COALESCE(personas.updated_at, now())
        FROM persona_preferences
        LEFT JOIN personas ON personas.id = persona_preferences.default_persona_id
        WHERE persona_preferences.id = 1
        """
    )

    op.drop_constraint("ck_conversation_persona_role", "conversations", type_="check")
    op.drop_index("ix_conversations_persona_id", table_name="conversations")
    op.drop_constraint("fk_conversations_persona_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "persona_instruction_role")
    op.drop_column("conversations", "persona_instructions")
    op.drop_column("conversations", "persona_description")
    op.drop_column("conversations", "persona_name")
    op.drop_column("conversations", "persona_id")
    op.drop_table("persona_preferences")
    op.drop_table("personas")
