from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID | None
    run_id: UUID | None
    level: Literal["info", "success", "error"]
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentNotificationListResponse(BaseModel):
    items: list[AgentNotificationResponse]
    unread_count: int
    total: int
