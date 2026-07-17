from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ToolExecution


async def recover_interrupted_tool_executions(session: AsyncSession) -> int:
    result = await session.execute(
        update(ToolExecution)
        .where(ToolExecution.status == "running")
        .values(
            status="failed",
            error_message="The tool execution was interrupted before completion.",
            finished_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return result.rowcount or 0
