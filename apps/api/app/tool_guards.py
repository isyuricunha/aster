from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ToolExecution


async def ensure_no_pending_tool_confirmation(
    session: AsyncSession,
    conversation_id: UUID,
) -> None:
    pending = await session.scalar(
        select(
            exists().where(
                ToolExecution.conversation_id == conversation_id,
                ToolExecution.status == "pending_confirmation",
            )
        )
    )
    if pending:
        raise HTTPException(
            status_code=409,
            detail="Resolve the pending tool confirmation before changing this conversation.",
        )
