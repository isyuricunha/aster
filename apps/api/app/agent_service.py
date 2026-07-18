from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import (
    Agent,
    AgentApproval,
    AgentCommunicationRule,
    AgentCommunicationScope,
    AgentControl,
    AgentKnowledgeScope,
    AgentRun,
    AgentStep,
    AgentToolScope,
)
from app.agent_notification_models import AgentNotification
from app.agent_queue import agent_control
from app.agent_schedule import (
    ScheduleValidationError,
    next_agent_run_at,
    validate_agent_schedule,
)
from app.agent_schemas import (
    AgentApprovalResponse,
    AgentCommunicationRuleResponse,
    AgentCommunicationScopeResponse,
    AgentControlResponse,
    AgentKnowledgeScopeResponse,
    AgentResponse,
    AgentRunResponse,
    AgentStepResponse,
    AgentToolScopeResponse,
    AgentWrite,
)
from app.communication_models import CommunicationAccount
from app.models import (
    McpServer,
    McpTool,
    ModelCacheEntry,
    Persona,
    PersonaPreferences,
)
from app.retrieval_models import KnowledgeCollection


async def _persona_snapshot(
    session: AsyncSession,
    *,
    persona_id: UUID | None,
    use_default_persona: bool,
) -> Persona | None:
    selected_id = persona_id
    if use_default_persona:
        preferences = await session.get(PersonaPreferences, 1)
        selected_id = preferences.default_persona_id if preferences else None
    if selected_id is None:
        return None
    persona = await session.get(Persona, selected_id)
    if persona is None or not persona.enabled:
        raise HTTPException(status_code=422, detail="The selected persona is unavailable.")
    return persona


async def _validate_model(session: AsyncSession, model_id: UUID | None) -> None:
    if model_id is None:
        return
    model = await session.get(ModelCacheEntry, model_id)
    if model is None or not model.is_available:
        raise HTTPException(status_code=422, detail="The selected model is unavailable.")


async def _replace_tool_scopes(
    session: AsyncSession,
    agent: Agent,
    payload: AgentWrite,
) -> None:
    await session.execute(delete(AgentToolScope).where(AgentToolScope.agent_id == agent.id))
    for item in payload.tools:
        row = (
            await session.execute(
                select(McpTool, McpServer)
                .join(McpServer, McpServer.id == McpTool.server_id)
                .where(McpTool.id == item.tool_id)
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(status_code=422, detail="An selected MCP tool no longer exists.")
        tool, server = row
        if not tool.enabled or not tool.is_available or not server.enabled:
            raise HTTPException(
                status_code=422,
                detail=f"The {server.name} · {tool.name} tool is unavailable.",
            )
        session.add(
            AgentToolScope(
                agent_id=agent.id,
                tool_id=tool.id,
                approval_policy=item.approval_policy,
            )
        )


async def _replace_communication_scopes(
    session: AsyncSession,
    agent: Agent,
    payload: AgentWrite,
) -> None:
    await session.execute(
        delete(AgentCommunicationScope).where(AgentCommunicationScope.agent_id == agent.id)
    )
    for item in payload.communication_scopes:
        account = await session.get(CommunicationAccount, item.account_id)
        if account is None:
            raise HTTPException(status_code=422, detail="A communication account no longer exists.")
        session.add(
            AgentCommunicationScope(
                agent_id=agent.id,
                account_id=account.id,
                allow_read=item.allow_read,
                allow_reply=item.allow_reply,
                reply_approval_policy=item.reply_approval_policy,
            )
        )


async def _replace_knowledge_scopes(
    session: AsyncSession,
    agent: Agent,
    payload: AgentWrite,
) -> None:
    await session.execute(
        delete(AgentKnowledgeScope).where(AgentKnowledgeScope.agent_id == agent.id)
    )
    for item in payload.knowledge_scopes:
        collection = await session.get(KnowledgeCollection, item.collection_id)
        if collection is None or not collection.enabled:
            raise HTTPException(status_code=422, detail="A knowledge collection is unavailable.")
        session.add(
            AgentKnowledgeScope(agent_id=agent.id, collection_id=collection.id)
        )


async def apply_agent_write(
    session: AsyncSession,
    agent: Agent,
    payload: AgentWrite,
) -> None:
    try:
        schedule = validate_agent_schedule(
            payload.trigger_type,
            payload.schedule,
            payload.timezone,
        )
    except ScheduleValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    await _validate_model(session, payload.model_id)
    persona = await _persona_snapshot(
        session,
        persona_id=payload.persona_id,
        use_default_persona=payload.use_default_persona,
    )
    agent.name = payload.name
    agent.description = payload.description
    agent.goal = payload.goal
    agent.enabled = payload.enabled
    agent.paused = payload.paused
    agent.trigger_type = payload.trigger_type
    agent.timezone = payload.timezone
    agent.schedule = schedule
    agent.next_run_at = (
        next_agent_run_at(payload.trigger_type, schedule, payload.timezone)
        if payload.enabled and not payload.paused
        else None
    )
    agent.model_id = payload.model_id
    agent.persona_id = persona.id if persona else None
    agent.persona_name = persona.name if persona else None
    agent.persona_description = persona.description if persona else None
    agent.persona_instructions = persona.instructions if persona else None
    agent.persona_instruction_role = persona.instruction_role if persona else None
    agent.memory_enabled = payload.memory_enabled
    agent.rag_enabled = payload.rag_enabled
    agent.max_steps = payload.max_steps
    agent.max_model_calls = payload.max_model_calls
    agent.max_tool_calls = payload.max_tool_calls
    agent.max_runtime_seconds = payload.max_runtime_seconds
    agent.max_estimated_tokens = payload.max_estimated_tokens
    agent.max_estimated_cost_microusd = payload.max_estimated_cost_microusd
    agent.input_cost_per_million_microusd = payload.input_cost_per_million_microusd
    agent.output_cost_per_million_microusd = payload.output_cost_per_million_microusd
    agent.notify_on_completion = payload.notify_on_completion
    agent.notify_on_failure = payload.notify_on_failure
    await session.flush()
    await _replace_tool_scopes(session, agent, payload)
    await _replace_communication_scopes(session, agent, payload)
    await _replace_knowledge_scopes(session, agent, payload)


async def _tool_scope_responses(
    session: AsyncSession,
    agent_id: UUID,
) -> list[AgentToolScopeResponse]:
    rows = (
        await session.execute(
            select(AgentToolScope, McpTool, McpServer)
            .join(McpTool, McpTool.id == AgentToolScope.tool_id)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(AgentToolScope.agent_id == agent_id)
            .order_by(McpServer.name, McpTool.name)
        )
    ).all()
    return [
        AgentToolScopeResponse(
            id=scope.id,
            tool_id=tool.id,
            server_name=server.name,
            tool_name=tool.name,
            public_name=tool.public_name,
            approval_policy=scope.approval_policy,
            requires_confirmation=tool.requires_confirmation,
            is_available=tool.is_available and tool.enabled and server.enabled,
        )
        for scope, tool, server in rows
    ]


async def _communication_scope_responses(
    session: AsyncSession,
    agent_id: UUID,
) -> list[AgentCommunicationScopeResponse]:
    rows = (
        await session.execute(
            select(AgentCommunicationScope, CommunicationAccount)
            .join(
                CommunicationAccount,
                CommunicationAccount.id == AgentCommunicationScope.account_id,
            )
            .where(AgentCommunicationScope.agent_id == agent_id)
            .order_by(CommunicationAccount.name)
        )
    ).all()
    return [
        AgentCommunicationScopeResponse(
            id=scope.id,
            account_id=account.id,
            account_name=account.name,
            account_kind=account.kind,
            allow_read=scope.allow_read,
            allow_reply=scope.allow_reply,
            reply_approval_policy=scope.reply_approval_policy,
        )
        for scope, account in rows
    ]


async def _knowledge_scope_responses(
    session: AsyncSession,
    agent_id: UUID,
) -> list[AgentKnowledgeScopeResponse]:
    rows = (
        await session.execute(
            select(AgentKnowledgeScope, KnowledgeCollection)
            .join(
                KnowledgeCollection,
                KnowledgeCollection.id == AgentKnowledgeScope.collection_id,
            )
            .where(AgentKnowledgeScope.agent_id == agent_id)
            .order_by(KnowledgeCollection.name)
        )
    ).all()
    return [
        AgentKnowledgeScopeResponse(
            id=scope.id,
            collection_id=collection.id,
            collection_name=collection.name,
        )
        for scope, collection in rows
    ]


async def agent_response(session: AsyncSession, agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        goal=agent.goal,
        enabled=agent.enabled,
        paused=agent.paused,
        trigger_type=agent.trigger_type,
        timezone=agent.timezone,
        schedule=agent.schedule,
        next_run_at=agent.next_run_at,
        model_id=agent.model_id,
        persona_id=agent.persona_id,
        persona_name=agent.persona_name,
        persona_description=agent.persona_description,
        persona_instruction_role=agent.persona_instruction_role,
        memory_enabled=agent.memory_enabled,
        rag_enabled=agent.rag_enabled,
        max_steps=agent.max_steps,
        max_model_calls=agent.max_model_calls,
        max_tool_calls=agent.max_tool_calls,
        max_runtime_seconds=agent.max_runtime_seconds,
        max_estimated_tokens=agent.max_estimated_tokens,
        max_estimated_cost_microusd=agent.max_estimated_cost_microusd,
        input_cost_per_million_microusd=agent.input_cost_per_million_microusd,
        output_cost_per_million_microusd=agent.output_cost_per_million_microusd,
        notify_on_completion=agent.notify_on_completion,
        notify_on_failure=agent.notify_on_failure,
        tools=await _tool_scope_responses(session, agent.id),
        communication_scopes=await _communication_scope_responses(session, agent.id),
        knowledge_scopes=await _knowledge_scope_responses(session, agent.id),
        last_enqueued_at=agent.last_enqueued_at,
        last_run_at=agent.last_run_at,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def step_response(step: AgentStep) -> AgentStepResponse:
    return AgentStepResponse.model_validate(step, from_attributes=True)


def approval_response(approval: AgentApproval) -> AgentApprovalResponse:
    return AgentApprovalResponse.model_validate(approval, from_attributes=True)


async def run_response(session: AsyncSession, run: AgentRun) -> AgentRunResponse:
    agent = await session.get(Agent, run.agent_id)
    steps = list(
        await session.scalars(
            select(AgentStep)
            .where(AgentStep.run_id == run.id)
            .order_by(AgentStep.position)
        )
    )
    approvals = list(
        await session.scalars(
            select(AgentApproval)
            .where(AgentApproval.run_id == run.id)
            .order_by(AgentApproval.created_at)
        )
    )
    return AgentRunResponse(
        id=run.id,
        agent_id=run.agent_id,
        agent_name=agent.name if agent else "Deleted agent",
        trigger_source=run.trigger_source,
        status=run.status,
        scheduled_for=run.scheduled_for,
        available_at=run.available_at,
        lease_owner=run.lease_owner,
        lease_expires_at=run.lease_expires_at,
        goal_snapshot=run.goal_snapshot,
        trigger_payload=run.trigger_payload,
        plan=run.plan,
        persona_name=run.persona_name,
        requested_model_id=run.requested_model_id,
        provider_model_id=run.provider_model_id,
        max_steps=run.max_steps,
        max_model_calls=run.max_model_calls,
        max_tool_calls=run.max_tool_calls,
        max_runtime_seconds=run.max_runtime_seconds,
        max_estimated_tokens=run.max_estimated_tokens,
        max_estimated_cost_microusd=run.max_estimated_cost_microusd,
        steps_used=run.steps_used,
        model_calls_used=run.model_calls_used,
        tool_calls_used=run.tool_calls_used,
        estimated_tokens=run.estimated_tokens,
        estimated_cost_microusd=run.estimated_cost_microusd,
        final_output=run.final_output,
        error_code=run.error_code,
        error_message=run.error_message,
        pause_requested=run.pause_requested,
        cancel_requested=run.cancel_requested,
        deadline_at=run.deadline_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=[step_response(item) for item in steps],
        approvals=[approval_response(item) for item in approvals],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


async def communication_rule_response(
    session: AsyncSession,
    rule: AgentCommunicationRule,
) -> AgentCommunicationRuleResponse:
    agent = await session.get(Agent, rule.agent_id)
    account = await session.get(CommunicationAccount, rule.account_id)
    return AgentCommunicationRuleResponse(
        id=rule.id,
        name=rule.name,
        agent_id=rule.agent_id,
        agent_name=agent.name if agent else "Deleted agent",
        account_id=rule.account_id,
        account_name=account.name if account else "Deleted account",
        enabled=rule.enabled,
        sender_pattern=rule.sender_pattern,
        source_ids=rule.source_ids,
        body_contains=rule.body_contains,
        require_mention=rule.require_mention,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


async def validate_communication_rule_targets(
    session: AsyncSession,
    *,
    agent_id: UUID,
    account_id: UUID,
) -> tuple[Agent, CommunicationAccount]:
    agent = await session.get(Agent, agent_id)
    account = await session.get(CommunicationAccount, account_id)
    if agent is None or account is None:
        raise HTTPException(status_code=422, detail="The selected agent or account is unavailable.")
    if agent.trigger_type != "communication":
        raise HTTPException(status_code=422, detail="The selected agent does not use communication events.")
    scope = await session.scalar(
        select(AgentCommunicationScope).where(
            AgentCommunicationScope.agent_id == agent.id,
            AgentCommunicationScope.account_id == account.id,
            AgentCommunicationScope.allow_read.is_(True),
        )
    )
    if scope is None:
        raise HTTPException(
            status_code=422,
            detail="The communication account must be an explicit readable agent scope.",
        )
    return agent, account


async def control_response(session: AsyncSession) -> AgentControlResponse:
    control = await agent_control(session)
    await session.commit()
    await session.refresh(control)
    return AgentControlResponse(
        emergency_stop=control.emergency_stop,
        reason=control.reason,
        activated_at=control.activated_at,
        updated_at=control.updated_at,
    )


async def set_emergency_stop(
    session: AsyncSession,
    *,
    enabled: bool,
    reason: str,
) -> AgentControl:
    control = await agent_control(session)
    control.emergency_stop = enabled
    control.reason = reason.strip() if enabled else ""
    control.activated_at = datetime.now(UTC) if enabled else None
    if enabled:
        runs = list(
            await session.scalars(
                select(AgentRun).where(
                    AgentRun.status.in_(["queued", "running", "waiting_approval", "paused"])
                )
            )
        )
        now = datetime.now(UTC)
        for run in runs:
            run.status = "cancelled"
            run.cancel_requested = True
            run.error_code = "emergency_stop"
            run.error_message = control.reason or "The autonomous agent emergency stop was activated."
            run.finished_at = now
            run.lease_owner = None
            run.lease_expires_at = None
        approvals = list(
            await session.scalars(
                select(AgentApproval).where(AgentApproval.status == "pending")
            )
        )
        for approval in approvals:
            approval.status = "cancelled"
            approval.decided_at = now
    await session.commit()
    await session.refresh(control)
    return control


async def create_agent_notification(
    session: AsyncSession,
    *,
    agent: Agent,
    run: AgentRun,
) -> None:
    failed = run.status in {"failed", "cancelled"}
    if failed and not agent.notify_on_failure:
        return
    if not failed and not agent.notify_on_completion:
        return
    session.add(
        AgentNotification(
            agent_id=agent.id,
            run_id=run.id,
            level="error" if failed else "success",
            title=f"{agent.name}: {'needs attention' if failed else 'completed'}",
            body=(run.error_message or run.final_output or "Agent run finished.")[:20_000],
        )
    )
    await session.commit()


async def unread_agent_notification_count(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count(AgentNotification.id)).where(
                AgentNotification.read_at.is_(None)
            )
        )
        or 0
    )
