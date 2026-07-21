"""Add functional starter templates.

Revision ID: 0019_product_templates
Revises: 0018_skills
Create Date: 2026-07-21
"""

import json
from collections.abc import Sequence

from alembic import op

revision: str = "0019_product_templates"
down_revision: str | None = "0018_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKILL_ID = "00000000-0000-4000-8000-000000000019"
AGENT_ID = "00000000-0000-4000-8000-00000000001a"
SKILL_DESCRIPTION = (
    "Turn supplied text into a short factual summary while preserving important names, numbers, "
    "dates, decisions, and caveats."
)
SKILL_INSTRUCTIONS = (
    "Summarize the supplied content into concise bullet points. Preserve names, numbers, dates, "
    "decisions, requirements, and material caveats exactly. Do not invent facts, recommendations, "
    "or conclusions. Separate confirmed facts from uncertainty. When the input has no usable "
    "content, say so plainly."
)
SKILL_TAGS = ["summary", "writing", "starter-template"]
SKILL_TRIGGERS = ["summarize this", "give me the key points", "resuma isso"]
SKILL_TEST_CASES = [
    {
        "input": "The maintenance starts Friday at 22:00 UTC and lasts two hours.",
        "expected": "Friday, 22:00 UTC, two-hour maintenance window",
    },
    {
        "input": "Revenue increased 8%, but customer churn also rose to 4%.",
        "expected": "Preserve both the 8% increase and the 4% churn caveat",
    },
]
AGENT_DESCRIPTION = (
    "Convert one bounded objective into a clear execution plan without using tools or performing "
    "external actions."
)
AGENT_GOAL = (
    "Analyze the owner objective, identify explicit constraints and missing information, then "
    "produce an ordered plan with concrete completion criteria. Do not call tools or perform "
    "external actions. Finish after presenting the plan, assumptions, risks, and the strongest "
    "next step."
)


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return f"CAST({_sql_string(encoded)} AS JSON)"


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO skills (
            id,
            name,
            description,
            instructions,
            status,
            source_type,
            tags,
            trigger_phrases,
            test_cases,
            audit_status,
            audit_report,
            content_revision
        )
        SELECT
            '{SKILL_ID}',
            'Concise Summarizer',
            {_sql_string(SKILL_DESCRIPTION)},
            {_sql_string(SKILL_INSTRUCTIONS)},
            'draft',
            'generated',
            {_sql_json(SKILL_TAGS)},
            {_sql_json(SKILL_TRIGGERS)},
            {_sql_json(SKILL_TEST_CASES)},
            'pending',
            {_sql_json({})},
            1
        WHERE NOT EXISTS (
            SELECT 1 FROM skills WHERE name = 'Concise Summarizer'
        )
        """
    )

    op.execute(
        f"""
        INSERT INTO agents (
            id,
            name,
            description,
            goal,
            enabled,
            paused,
            trigger_type,
            timezone,
            schedule,
            memory_enabled,
            rag_enabled,
            max_steps,
            max_model_calls,
            max_tool_calls,
            max_runtime_seconds,
            max_estimated_tokens,
            notify_on_completion,
            notify_on_failure
        )
        SELECT
            '{AGENT_ID}',
            'Task Planner',
            {_sql_string(AGENT_DESCRIPTION)},
            {_sql_string(AGENT_GOAL)},
            true,
            false,
            'manual',
            'UTC',
            {_sql_json({})},
            false,
            false,
            4,
            4,
            0,
            300,
            20000,
            false,
            true
        WHERE NOT EXISTS (
            SELECT 1 FROM agents WHERE name = 'Task Planner'
        )
        """
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM agents WHERE id = '{AGENT_ID}'")
    op.execute(f"DELETE FROM skills WHERE id = '{SKILL_ID}'")
