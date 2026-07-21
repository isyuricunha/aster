"""Add functional starter templates.

Revision ID: 0019_product_templates
Revises: 0018_skills
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "0019_product_templates"
down_revision: str | None = "0018_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKILL_ID = UUID("00000000-0000-4000-8000-000000000019")
AGENT_ID = UUID("00000000-0000-4000-8000-00000000001a")


def upgrade() -> None:
    connection = op.get_bind()
    skills = sa.table(
        "skills",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("instructions", sa.Text()),
        sa.column("status", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("tags", sa.JSON()),
        sa.column("trigger_phrases", sa.JSON()),
        sa.column("test_cases", sa.JSON()),
        sa.column("audit_status", sa.String()),
        sa.column("audit_report", sa.JSON()),
        sa.column("content_revision", sa.Integer()),
    )
    skill_exists = connection.scalar(
        sa.select(sa.literal(True)).where(skills.c.name == "Concise Summarizer").limit(1)
    )
    if not skill_exists:
        connection.execute(
            skills.insert().values(
                id=SKILL_ID,
                name="Concise Summarizer",
                description=(
                    "Turn supplied text into a short factual summary while preserving important "
                    "names, numbers, dates, decisions, and caveats."
                ),
                instructions=(
                    "Summarize the supplied content into concise bullet points. Preserve names, "
                    "numbers, dates, decisions, requirements, and material caveats exactly. Do not "
                    "invent facts, recommendations, or conclusions. Separate confirmed facts from "
                    "uncertainty. When the input has no usable content, say so plainly."
                ),
                status="draft",
                source_type="generated",
                tags=["summary", "writing", "starter-template"],
                trigger_phrases=[
                    "summarize this",
                    "give me the key points",
                    "resuma isso",
                ],
                test_cases=[
                    {
                        "input": "The maintenance starts Friday at 22:00 UTC and lasts two hours.",
                        "expected": "Friday, 22:00 UTC, two-hour maintenance window",
                    },
                    {
                        "input": "Revenue increased 8%, but customer churn also rose to 4%.",
                        "expected": "Preserve both the 8% increase and the 4% churn caveat",
                    },
                ],
                audit_status="pending",
                audit_report={"template": True},
                content_revision=1,
            )
        )

    agents = sa.table(
        "agents",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("goal", sa.Text()),
        sa.column("enabled", sa.Boolean()),
        sa.column("paused", sa.Boolean()),
        sa.column("trigger_type", sa.String()),
        sa.column("timezone", sa.String()),
        sa.column("schedule", sa.JSON()),
        sa.column("memory_enabled", sa.Boolean()),
        sa.column("rag_enabled", sa.Boolean()),
        sa.column("max_steps", sa.Integer()),
        sa.column("max_model_calls", sa.Integer()),
        sa.column("max_tool_calls", sa.Integer()),
        sa.column("max_runtime_seconds", sa.Integer()),
        sa.column("max_estimated_tokens", sa.Integer()),
        sa.column("notify_on_completion", sa.Boolean()),
        sa.column("notify_on_failure", sa.Boolean()),
    )
    agent_exists = connection.scalar(
        sa.select(sa.literal(True)).where(agents.c.name == "Task Planner").limit(1)
    )
    if not agent_exists:
        connection.execute(
            agents.insert().values(
                id=AGENT_ID,
                name="Task Planner",
                description=(
                    "Convert one bounded objective into a clear execution plan without using tools "
                    "or performing external actions."
                ),
                goal=(
                    "Analyze the owner's objective, identify explicit constraints and missing "
                    "information, then produce an ordered plan with concrete completion criteria. "
                    "Do not call tools or perform external actions. Finish after presenting the "
                    "plan, assumptions, risks, and the strongest next step."
                ),
                enabled=True,
                paused=False,
                trigger_type="manual",
                timezone="UTC",
                schedule={},
                memory_enabled=False,
                rag_enabled=False,
                max_steps=4,
                max_model_calls=4,
                max_tool_calls=0,
                max_runtime_seconds=300,
                max_estimated_tokens=20_000,
                notify_on_completion=False,
                notify_on_failure=True,
            )
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM agents WHERE id = :id").bindparams(id=AGENT_ID))
    op.execute(sa.text("DELETE FROM skills WHERE id = :id").bindparams(id=SKILL_ID))
