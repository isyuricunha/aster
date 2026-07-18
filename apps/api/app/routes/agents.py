from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import Agent, AgentRun
from app.agent_schemas import (
    AgentControlResponse,
    AgentControlUpdate,
    AgentCreate,
    AgentResponse,
    AgentUpdate,
)
from app.agent_service import (
    agent_response,
    apply_agent_write,
    control_response,
    set_emergency_stop,
)
from app.db import get_session

router = APIRouter(prefix="/api", tags=["agents"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_agent(session: AsyncSession, agent_id: UUID) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents(session: SessionDep) -> list[AgentResponse]:
    agents = list(await session.scalars(select(Agent).order_by(Agent.name)))
    return [await agent_response(session, item) for item in agents]


@router.post(
    "/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent(
    payload: AgentCreate,
    session: SessionDep,
) -> AgentResponse:
    agent = Agent(name=payload.name, goal=payload.goal)
    session.add(agent)
    try:
        await apply_agent_write(session, agent, payload)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Agent name already exists") from error
    except Exception:
        await session.rollback()
        raise
    await session.refresh(agent)
    return await agent_response(session, agent)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def read_agent(agent_id: UUID, session: SessionDep) -> AgentResponse:
    return await agent_response(session, await get_agent(session, agent_id))


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    session: SessionDep,
) -> AgentResponse:
    agent = await get_agent(session, agent_id)
    try:
        await apply_agent_write(session, agent, payload)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Agent name already exists") from error
    except Exception:
        await session.rollback()
        raise
    await session.refresh(agent)
    return await agent_response(session, agent)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: UUID, session: SessionDep) -> Response:
    agent = await get_agent(session, agent_id)
    active = await session.scalar(
        select(AgentRun.id)
        .where(
            AgentRun.agent_id == agent.id,
            AgentRun.status.in_(["queued", "running", "waiting_approval", "paused"]),
        )
        .limit(1)
    )
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail="Cancel active runs before deleting the agent.",
        )
    await session.delete(agent)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/agent-control", response_model=AgentControlResponse)
async def read_agent_control(session: SessionDep) -> AgentControlResponse:
    return await control_response(session)


@router.put("/agent-control", response_model=AgentControlResponse)
async def update_agent_control(
    payload: AgentControlUpdate,
    session: SessionDep,
) -> AgentControlResponse:
    control = await set_emergency_stop(
        session,
        enabled=payload.emergency_stop,
        reason=payload.reason,
    )
    return AgentControlResponse(
        emergency_stop=control.emergency_stop,
        reason=control.reason,
        activated_at=control.activated_at,
        updated_at=control.updated_at,
    )
