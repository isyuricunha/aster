import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_actions import prepare_external_action, resume_approved_action
from app.agent_models import Agent, AgentRun, AgentStep
from app.agent_retrieval import agent_retrieval_context
from app.agent_runtime import (
    FINISH_TOOL,
    UPDATE_PLAN_TOOL,
    AgentExecutionError,
    ModelRound,
    ToolCallBuffer,
    agent_instruction,
    merge_tool_deltas,
    parse_arguments,
    provider_tools,
    scoped_communications,
    scoped_tool_runtimes,
    step_history,
)
from app.agent_service import create_agent_notification
from app.agent_step_service import (
    check_run_controls,
    complete_run,
    create_step,
    fail_run,
    record_model_usage,
)
from app.agent_time import aware_datetime
from app.config import Settings
from app.mcp_client import McpClient
from app.model_routing import can_fallback, resolve_automation_targets
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.prompt_library import render_persona
from app.security import SecretCipher


async def build_agent_messages(
    session: AsyncSession,
    *,
    run: AgentRun,
    settings: Settings,
) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = [
        {"role": "system", "content": agent_instruction()}
    ]
    if run.persona_name and run.persona_instruction_role:
        persona = render_persona(run.persona_name, run.persona_instructions or "")
        if persona:
            messages.append(
                {
                    "role": run.persona_instruction_role,
                    "content": persona,
                }
            )
    retrieval = await agent_retrieval_context(
        session,
        run=run,
        max_characters=settings.aster_agent_retrieval_max_characters,
        memory_limit=settings.aster_memory_max_items,
        document_limit=settings.aster_rag_max_sources,
    )
    if retrieval:
        messages.append({"role": "system", "content": retrieval})
    steps = list(
        await session.scalars(
            select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.position)
        )
    )
    content = (
        "[OWNER_SAVED_GOAL]\n"
        f"{run.goal_snapshot}\n"
        "[/OWNER_SAVED_GOAL]"
    )
    if run.trigger_payload:
        content += (
            "\n\n[UNTRUSTED_TRIGGER_PAYLOAD]\n"
            f"{json.dumps(run.trigger_payload, ensure_ascii=False, indent=2)}\n"
            "[/UNTRUSTED_TRIGGER_PAYLOAD]"
        )
    if run.plan:
        content += (
            "\n\n[PERSISTED_PLAN_STATE]\n"
            f"{json.dumps(run.plan, ensure_ascii=False, indent=2)}\n"
            "[/PERSISTED_PLAN_STATE]"
        )
    history = step_history(steps, settings.aster_agent_history_max_characters)
    if history:
        content += (
            "\n\n[UNTRUSTED_PERSISTED_EXECUTION_HISTORY]\n"
            f"{history}\n"
            "[/UNTRUSTED_PERSISTED_EXECUTION_HISTORY]"
        )
    content += (
        "\n\nChoose exactly one next bounded action, update the plan when materially useful, "
        "or finish the run."
    )
    messages.append({"role": "user", "content": content})
    return messages


async def run_model_round(
    session: AsyncSession,
    *,
    run: AgentRun,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
    tools: list[dict[str, object]],
    settings: Settings,
) -> ModelRound:
    messages = await build_agent_messages(session, run=run, settings=settings)
    input_characters = len(json.dumps(messages, ensure_ascii=False)) + len(
        json.dumps(tools, ensure_ascii=False)
    )
    targets = await resolve_automation_targets(session, cipher, run.requested_model_id)
    last_error: ModelEndpointError | None = None
    for index, target in enumerate(targets):
        content: list[str] = []
        buffers: dict[int, ToolCallBuffer] = {}
        try:
            remaining = (
                max(
                    1.0,
                    (aware_datetime(run.deadline_at) - datetime.now(UTC)).total_seconds(),
                )
                if run.deadline_at
                else float(run.max_runtime_seconds)
            )
            async with asyncio.timeout(remaining):
                async for delta in client.stream_chat_completion_events(
                    base_url=target.base_url,
                    api_key=target.api_key,
                    model_id=target.provider_model_id,
                    messages=messages,
                    tools=tools,
                    temperature=target.parameters.temperature,
                    top_p=target.parameters.top_p,
                    max_output_tokens=target.parameters.max_output_tokens,
                    token_parameter=target.parameters.token_parameter,
                    reasoning_effort=target.parameters.reasoning_effort,
                ):
                    if delta.content:
                        content.append(delta.content)
                        if (
                            sum(len(item) for item in content)
                            > settings.aster_agent_output_max_characters
                        ):
                            raise AgentExecutionError(
                                "output_too_large",
                                "The agent model output exceeded the configured character limit.",
                            )
                    merge_tool_deltas(buffers, delta)
            if not content and not buffers:
                raise ModelEndpointError(
                    "empty_response",
                    "The agent model returned no output.",
                )
            return ModelRound(
                content="".join(content),
                calls=tuple(buffers[key] for key in sorted(buffers)),
                provider_model_id=target.provider_model_id,
                input_characters=input_characters,
                output_characters=sum(len(item) for item in content)
                + sum(len("".join(item.arguments)) for item in buffers.values()),
            )
        except TimeoutError as error:
            last_error = ModelEndpointError("timeout", "The agent model call timed out.")
            if index + 1 < len(targets) and not content and not buffers:
                continue
            raise AgentExecutionError(last_error.code, last_error.message) from error
        except ModelEndpointError as error:
            last_error = error
            if index + 1 < len(targets) and not content and not buffers and can_fallback(error):
                continue
            raise AgentExecutionError(error.code, error.message) from error
    raise AgentExecutionError(
        last_error.code if last_error else "unavailable",
        last_error.message if last_error else "No agent model is available.",
    )


def normalize_plan(arguments: dict[str, object]) -> list[dict[str, object]]:
    items = arguments.get("items")
    if not isinstance(items, list) or len(items) > 50:
        raise AgentExecutionError("invalid_plan", "The proposed plan is invalid.")
    normalized: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            raise AgentExecutionError("invalid_plan", "Every plan item must be an object.")
        title = item.get("title")
        status = item.get("status")
        note = item.get("note", "")
        if (
            not isinstance(title, str)
            or not title.strip()
            or status not in {"pending", "active", "completed", "blocked"}
            or not isinstance(note, str)
        ):
            raise AgentExecutionError("invalid_plan", "A plan item contains invalid values.")
        normalized.append(
            {
                "title": title.strip()[:500],
                "status": status,
                "note": note.strip()[:2_000],
            }
        )
    return normalized


async def handle_model_action(
    session: AsyncSession,
    *,
    run: AgentRun,
    buffer: ToolCallBuffer,
    runtimes,
    communications,
    mcp_client: McpClient,
    cipher: SecretCipher,
    settings: Settings,
) -> bool:
    if not buffer.name or not buffer.call_id:
        raise AgentExecutionError("invalid_action", "The model produced an incomplete action.")
    arguments = parse_arguments(buffer, settings.aster_tool_argument_max_characters)
    if buffer.name == UPDATE_PLAN_TOOL:
        run.plan = normalize_plan(arguments)
        await create_step(
            session,
            run,
            kind="plan",
            status="completed",
            summary="Updated the execution plan",
            tool_call_id=buffer.call_id,
            tool_name=buffer.name,
            arguments=arguments,
        )
        await session.commit()
        return False
    if buffer.name == FINISH_TOOL:
        result = arguments.get("result")
        if not isinstance(result, str) or not result.strip():
            raise AgentExecutionError("invalid_final_result", "The final result is empty.")
        await create_step(
            session,
            run,
            kind="final",
            status="completed",
            summary="Completed the saved goal",
            content=result.strip(),
            tool_call_id=buffer.call_id,
            tool_name=buffer.name,
            arguments=arguments,
        )
        await complete_run(session, run=run, result=result.strip())
        return True
    return await prepare_external_action(
        session,
        run=run,
        name=buffer.name,
        call_id=buffer.call_id,
        arguments=arguments,
        runtimes=runtimes,
        communications=communications,
        mcp_client=mcp_client,
        cipher=cipher,
        settings=settings,
    )


async def finish_with_text(
    session: AsyncSession,
    *,
    run: AgentRun,
    content: str,
    provider_model_id: str,
) -> None:
    result = content.strip() or "The agent stopped without a final result."
    await create_step(
        session,
        run,
        kind="final",
        status="completed",
        summary="Completed with a direct model response",
        content=result,
        provider_model_id=provider_model_id,
    )
    await complete_run(session, run=run, result=result)


async def execute_agent_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    run_id: UUID,
    worker_id: str,
    client: OpenAICompatibleClient,
    mcp_client: McpClient,
    cipher: SecretCipher,
    settings: Settings,
) -> None:
    async with session_factory() as session:
        run = await session.get(AgentRun, run_id)
        if run is None or run.status != "running" or run.lease_owner != worker_id:
            return
        agent = await session.get(Agent, run.agent_id)
        if agent is None:
            await fail_run(
                session,
                run=run,
                code="agent_missing",
                message="The agent no longer exists.",
            )
            return
        try:
            runtimes = await scoped_tool_runtimes(
                session,
                run_id=run.id,
                cipher=cipher,
                settings=settings,
            )
            communications = await scoped_communications(session, run.id)
            await resume_approved_action(
                session,
                run=run,
                runtimes=runtimes,
                communications=communications,
                mcp_client=mcp_client,
                cipher=cipher,
                settings=settings,
            )
            while run.status == "running":
                await check_run_controls(session, run)
                result = await run_model_round(
                    session,
                    run=run,
                    client=client,
                    cipher=cipher,
                    tools=provider_tools(runtimes, communications),
                    settings=settings,
                )
                record_model_usage(run, result)
                if len(result.calls) > 1:
                    raise AgentExecutionError(
                        "multiple_actions",
                        "The model proposed more than one action in a single round.",
                    )
                if not result.calls:
                    await finish_with_text(
                        session,
                        run=run,
                        content=result.content,
                        provider_model_id=result.provider_model_id,
                    )
                    break
                await create_step(
                    session,
                    run,
                    kind="model",
                    status="completed",
                    summary=f"Proposed {result.calls[0].name or 'an action'}",
                    content=result.content or None,
                    provider_model_id=result.provider_model_id,
                )
                stopped = await handle_model_action(
                    session,
                    run=run,
                    buffer=result.calls[0],
                    runtimes=runtimes,
                    communications=communications,
                    mcp_client=mcp_client,
                    cipher=cipher,
                    settings=settings,
                )
                if stopped:
                    break
            if run.status in {"completed", "failed", "cancelled"}:
                agent.last_run_at = run.finished_at or datetime.now(UTC)
                await session.commit()
                await create_agent_notification(session, agent=agent, run=run)
        except AgentExecutionError as error:
            await fail_run(
                session,
                run=run,
                code=error.code,
                message=error.message,
            )
            if run.status in {"failed", "cancelled"}:
                agent.last_run_at = run.finished_at
                await session.commit()
                await create_agent_notification(session, agent=agent, run=run)
        except Exception as error:
            await fail_run(
                session,
                run=run,
                code="agent_failed",
                message=str(error),
            )
            agent.last_run_at = run.finished_at
            await session.commit()
            await create_agent_notification(session, agent=agent, run=run)
