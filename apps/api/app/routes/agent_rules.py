from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import AgentCommunicationRule
from app.agent_schemas import (
    AgentCommunicationRuleCreate,
    AgentCommunicationRuleResponse,
    AgentCommunicationRuleUpdate,
)
from app.agent_service import (
    communication_rule_response,
    validate_communication_rule_targets,
)
from app.db import get_session

router = APIRouter(prefix="/api", tags=["agent-rules"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_agent_rule(
    session: AsyncSession,
    rule_id: UUID,
) -> AgentCommunicationRule:
    rule = await session.get(AgentCommunicationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Agent communication rule not found")
    return rule


@router.get(
    "/agent-communication-rules",
    response_model=list[AgentCommunicationRuleResponse],
)
async def list_agent_communication_rules(
    session: SessionDep,
) -> list[AgentCommunicationRuleResponse]:
    rules = list(
        await session.scalars(select(AgentCommunicationRule).order_by(AgentCommunicationRule.name))
    )
    return [await communication_rule_response(session, item) for item in rules]


@router.post(
    "/agent-communication-rules",
    response_model=AgentCommunicationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_communication_rule(
    payload: AgentCommunicationRuleCreate,
    session: SessionDep,
) -> AgentCommunicationRuleResponse:
    await validate_communication_rule_targets(
        session,
        agent_id=payload.agent_id,
        account_id=payload.account_id,
    )
    rule = AgentCommunicationRule(**payload.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return await communication_rule_response(session, rule)


@router.put(
    "/agent-communication-rules/{rule_id}",
    response_model=AgentCommunicationRuleResponse,
)
async def update_agent_communication_rule(
    rule_id: UUID,
    payload: AgentCommunicationRuleUpdate,
    session: SessionDep,
) -> AgentCommunicationRuleResponse:
    rule = await get_agent_rule(session, rule_id)
    await validate_communication_rule_targets(
        session,
        agent_id=payload.agent_id,
        account_id=payload.account_id,
    )
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    await session.commit()
    await session.refresh(rule)
    return await communication_rule_response(session, rule)


@router.delete(
    "/agent-communication-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agent_communication_rule(
    rule_id: UUID,
    session: SessionDep,
) -> Response:
    await session.delete(await get_agent_rule(session, rule_id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
