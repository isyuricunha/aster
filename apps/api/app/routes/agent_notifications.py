from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_notification_models import AgentNotification
from app.agent_notification_schemas import (
    AgentNotificationListResponse,
    AgentNotificationResponse,
)
from app.db import get_session

router = APIRouter(prefix="/api", tags=["agent-notifications"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/agent-notifications",
    response_model=AgentNotificationListResponse,
)
async def list_agent_notifications(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AgentNotificationListResponse:
    items = list(
        await session.scalars(
            select(AgentNotification).order_by(AgentNotification.created_at.desc()).limit(limit)
        )
    )
    unread = int(
        await session.scalar(
            select(func.count(AgentNotification.id)).where(AgentNotification.read_at.is_(None))
        )
        or 0
    )
    total = int(await session.scalar(select(func.count(AgentNotification.id))) or 0)
    return AgentNotificationListResponse(
        items=[AgentNotificationResponse.model_validate(item) for item in items],
        unread_count=unread,
        total=total,
    )


@router.post(
    "/agent-notifications/{notification_id}/read",
    response_model=AgentNotificationResponse,
)
async def mark_agent_notification_read(
    notification_id: UUID,
    session: SessionDep,
) -> AgentNotificationResponse:
    item = await session.get(AgentNotification, notification_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agent notification not found")
    item.read_at = item.read_at or datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return AgentNotificationResponse.model_validate(item)


@router.post(
    "/agent-notifications/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mark_all_agent_notifications_read(session: SessionDep) -> Response:
    items = list(
        await session.scalars(select(AgentNotification).where(AgentNotification.read_at.is_(None)))
    )
    now = datetime.now(UTC)
    for item in items:
        item.read_at = now
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/agent-notifications/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agent_notification(
    notification_id: UUID,
    session: SessionDep,
) -> Response:
    item = await session.get(AgentNotification, notification_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agent notification not found")
    await session.delete(item)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
