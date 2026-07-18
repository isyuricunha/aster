import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_models import AgentApproval, AgentRun, AgentStep
from app.agent_runtime import (
    LIST_COMMUNICATIONS_TOOL,
    READ_COMMUNICATION_TOOL,
    REPLY_COMMUNICATION_TOOL,
    AgentExecutionError,
    ScopedCommunication,
    ScopedToolRuntime,
    parse_uuid,
)
from app.agent_step_service import create_step, register_action
from app.communication_models import CommunicationThread
from app.communication_service import reply_to_thread, thread_detail
from app.config import Settings
from app.mcp_client import McpClient, McpClientError
from app.security import SecretCipher
from app.tool_service import execute_runtime_tool


async def communication_for_thread(
    session: AsyncSession,
    *,
    thread_id: UUID,
    communications: dict[UUID, ScopedCommunication],
    require_reply: bool,
) -> tuple[CommunicationThread, ScopedCommunication]:
    thread = await session.get(CommunicationThread, thread_id)
    if thread is None:
        raise AgentExecutionError("thread_missing", "The communication thread no longer exists.")
    scoped = communications.get(thread.account_id)
    if scoped is None or not scoped.scope.allow_read:
        raise AgentExecutionError(
            "scope_denied",
            "The thread is outside the agent communication scope.",
        )
    if require_reply and not scoped.scope.allow_reply:
        raise AgentExecutionError(
            "scope_denied",
            "The agent is not allowed to reply through this account.",
        )
    return thread, scoped


async def list_communications(
    session: AsyncSession,
    *,
    arguments: dict[str, object],
    communications: dict[UUID, ScopedCommunication],
) -> str:
    readable = {
        account_id: item for account_id, item in communications.items() if item.scope.allow_read
    }
    account_ids = list(readable)
    raw_account_id = arguments.get("account_id")
    if raw_account_id is not None:
        account_id = parse_uuid(raw_account_id, "account_id")
        if account_id not in readable:
            raise AgentExecutionError(
                "scope_denied",
                "The account is outside the readable scope.",
            )
        account_ids = [account_id]
    limit = arguments.get("limit", 20)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise AgentExecutionError("invalid_arguments", "limit must be between 1 and 50.")
    unread_only = bool(arguments.get("unread_only", False))
    if not account_ids:
        return "[]"
    statement = select(CommunicationThread).where(CommunicationThread.account_id.in_(account_ids))
    if unread_only:
        statement = statement.where(CommunicationThread.unread_count > 0)
    threads = list(
        await session.scalars(
            statement.order_by(CommunicationThread.last_message_at.desc()).limit(limit)
        )
    )
    return json.dumps(
        [
            {
                "id": str(thread.id),
                "account_id": str(thread.account_id),
                "account_name": readable[thread.account_id].account.name,
                "kind": thread.kind,
                "title": thread.title,
                "unread_count": thread.unread_count,
                "last_message_at": thread.last_message_at.isoformat(),
            }
            for thread in threads
        ],
        ensure_ascii=False,
    )


async def read_communication(
    session: AsyncSession,
    *,
    arguments: dict[str, object],
    communications: dict[UUID, ScopedCommunication],
) -> str:
    thread_id = parse_uuid(arguments.get("thread_id"), "thread_id")
    thread, scoped = await communication_for_thread(
        session,
        thread_id=thread_id,
        communications=communications,
        require_reply=False,
    )
    detail = await thread_detail(session, thread, scoped.account.name)
    return json.dumps(detail.model_dump(mode="json"), ensure_ascii=False)


async def reply_communication(
    session: AsyncSession,
    *,
    step: AgentStep,
    communications: dict[UUID, ScopedCommunication],
    cipher: SecretCipher,
    settings: Settings,
) -> None:
    thread_id = parse_uuid(step.arguments.get("thread_id"), "thread_id")
    content = step.arguments.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AgentExecutionError("invalid_arguments", "Reply content is required.")
    thread, scoped = await communication_for_thread(
        session,
        thread_id=thread_id,
        communications=communications,
        require_reply=True,
    )
    message = await reply_to_thread(
        session,
        thread=thread,
        account=scoped.account,
        content=content.strip(),
        cipher=cipher,
        settings=settings,
    )
    step.result = json.dumps(
        {
            "status": "sent",
            "message_id": str(message.id),
            "thread_id": str(thread.id),
        }
    )
    step.status = "completed"
    step.finished_at = datetime.now(UTC)
    await session.commit()


async def execute_mcp(
    session: AsyncSession,
    *,
    step: AgentStep,
    scoped: ScopedToolRuntime,
    client: McpClient,
    settings: Settings,
) -> None:
    try:
        result = await execute_runtime_tool(
            client,
            scoped.runtime,
            arguments=step.arguments,
            result_limit=settings.aster_tool_result_max_characters,
        )
        step.result = result.content
        step.status = "failed" if result.is_error else "completed"
        if result.is_error and not step.result:
            step.result = "The MCP tool reported an error."
    except McpClientError as error:
        step.status = "failed"
        step.result = error.message[:500]
    step.finished_at = datetime.now(UTC)
    await session.commit()


async def execute_action(
    session: AsyncSession,
    *,
    step: AgentStep,
    runtimes: dict[str, ScopedToolRuntime],
    communications: dict[UUID, ScopedCommunication],
    mcp_client: McpClient,
    cipher: SecretCipher,
    settings: Settings,
) -> None:
    name = step.tool_name or ""
    if name in runtimes:
        await execute_mcp(
            session,
            step=step,
            scoped=runtimes[name],
            client=mcp_client,
            settings=settings,
        )
        return
    if name == LIST_COMMUNICATIONS_TOOL:
        step.result = await list_communications(
            session,
            arguments=step.arguments,
            communications=communications,
        )
        step.status = "completed"
    elif name == READ_COMMUNICATION_TOOL:
        step.result = await read_communication(
            session,
            arguments=step.arguments,
            communications=communications,
        )
        step.status = "completed"
    elif name == REPLY_COMMUNICATION_TOOL:
        await reply_communication(
            session,
            step=step,
            communications=communications,
            cipher=cipher,
            settings=settings,
        )
        return
    else:
        step.status = "failed"
        step.result = "The proposed action is not available in this run."
    step.finished_at = datetime.now(UTC)
    await session.commit()


async def create_approval(
    session: AsyncSession,
    *,
    run: AgentRun,
    step: AgentStep,
    action_type: str,
    title: str,
    details: str,
) -> None:
    session.add(
        AgentApproval(
            run_id=run.id,
            step_id=step.id,
            action_type=action_type,
            status="pending",
            title=title[:200],
            details=details,
            payload={"name": step.tool_name, "arguments": step.arguments},
        )
    )
    step.status = "waiting_approval"
    run.status = "waiting_approval"
    run.lease_owner = None
    run.lease_expires_at = None
    await session.commit()


async def resume_approved_action(
    session: AsyncSession,
    *,
    run: AgentRun,
    runtimes: dict[str, ScopedToolRuntime],
    communications: dict[UUID, ScopedCommunication],
    mcp_client: McpClient,
    cipher: SecretCipher,
    settings: Settings,
) -> None:
    row = (
        await session.execute(
            select(AgentApproval, AgentStep)
            .join(AgentStep, AgentStep.id == AgentApproval.step_id)
            .where(
                AgentApproval.run_id == run.id,
                AgentApproval.status == "approved",
                AgentStep.status == "waiting_approval",
            )
            .order_by(AgentApproval.created_at)
            .limit(1)
        )
    ).one_or_none()
    if row is None:
        return
    _, step = row
    step.status = "running"
    await session.commit()
    await execute_action(
        session,
        step=step,
        runtimes=runtimes,
        communications=communications,
        mcp_client=mcp_client,
        cipher=cipher,
        settings=settings,
    )


async def prepare_external_action(
    session: AsyncSession,
    *,
    run: AgentRun,
    name: str,
    call_id: str,
    arguments: dict[str, object],
    runtimes: dict[str, ScopedToolRuntime],
    communications: dict[UUID, ScopedCommunication],
    mcp_client: McpClient,
    cipher: SecretCipher,
    settings: Settings,
) -> bool:
    fingerprint = await register_action(
        run,
        name=name,
        arguments=arguments,
        repeat_limit=settings.aster_agent_loop_repeat_limit,
    )
    kind = "communication" if name.startswith("aster_") else "tool"
    tool_id = runtimes[name].runtime.tool.id if name in runtimes else None
    step = await create_step(
        session,
        run,
        kind=kind,
        status="running",
        summary=f"Execute {name}",
        tool_id=tool_id,
        tool_call_id=call_id,
        tool_name=name,
        arguments=arguments,
        fingerprint=fingerprint,
    )
    approval_required = False
    action_type = "tool"
    title = f"Approve {name}"
    details = json.dumps(arguments, ensure_ascii=False, indent=2)
    if name in runtimes:
        scoped = runtimes[name]
        approval_required = scoped.scope.approval_policy == "always" or (
            scoped.scope.approval_policy == "tool_default"
            and scoped.runtime.tool.requires_confirmation
        )
    elif name == REPLY_COMMUNICATION_TOOL:
        thread_id = parse_uuid(arguments.get("thread_id"), "thread_id")
        _, scoped = await communication_for_thread(
            session,
            thread_id=thread_id,
            communications=communications,
            require_reply=True,
        )
        approval_required = scoped.scope.reply_approval_policy == "always"
        action_type = "communication_reply"
        title = f"Approve reply through {scoped.account.name}"
    elif name not in {LIST_COMMUNICATIONS_TOOL, READ_COMMUNICATION_TOOL}:
        step.status = "failed"
        step.result = "The proposed action is not exposed to this run."
        step.finished_at = datetime.now(UTC)
        await session.commit()
        return False
    if approval_required:
        await create_approval(
            session,
            run=run,
            step=step,
            action_type=action_type,
            title=title,
            details=details,
        )
        return True
    await execute_action(
        session,
        step=step,
        runtimes=runtimes,
        communications=communications,
        mcp_client=mcp_client,
        cipher=cipher,
        settings=settings,
    )
    return False
