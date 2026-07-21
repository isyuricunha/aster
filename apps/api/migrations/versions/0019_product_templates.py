"""Add functional starter templates.

Revision ID: 0019_product_templates
Revises: 0018_skills
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019_product_templates"
down_revision: str | None = "0018_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKILL_ID = "00000000-0000-4000-8000-000000000019"
AGENT_ID = "00000000-0000-4000-8000-00000000001a"


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
            'Turn supplied text into a short factual summary while preserving important names, numbers, dates, decisions, and caveats.',
            'Summarize the supplied content into concise bullet points. Preserve names, numbers, dates, decisions, requirements, and material caveats exactly. Do not invent facts, recommendations, or conclusions. Separate confirmed facts from uncertainty. When the input has no usable content, say so plainly.',
            'draft',
            'generated',
            CAST('["summary","writing","starter-template"]' AS JSON),
            CAST('["summarize this","give me the key points","resuma isso"]' AS JSON),
            CAST('[{{"input":"The maintenance starts Friday at 22:00 UTC and lasts two hours.","expected":"Friday, 22:00 UTC, two-hour maintenance window"}},{{"input":"Revenue increased 8%, but customer churn also rose to 4%.","expected":"Preserve both the 8% increase and the 4% churn caveat"}}]' AS JSON),
            'pending',
            CAST('{{"template":true}}' AS JSON),
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
            'Convert one bounded objective into a clear execution plan without using tools or performing external actions.',
            'Analyze the owner objective, identify explicit constraints and missing information, then produce an ordered plan with concrete completion criteria. Do not call tools or perform external actions. Finish after presenting the plan, assumptions, risks, and the strongest next step.',
            true,
            false,
            'manual',
            'UTC',
            CAST('{{}}' AS JSON),
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
