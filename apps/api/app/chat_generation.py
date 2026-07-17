import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_runtime import generation_registry
from app.message_composition import (
    CanonicalMessage,
    MessageRole,
    MessageSource,
    PersonaConfiguration,
    compose_messages,
)
from app.model_routing import ModelTarget, can_fallback, resolve_chat_targets
from app.models import ChatMessage, Conversation
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.schemas import (
    ChatMessageResponse,
    ConversationPersonaResponse,
    ConversationResponse,
)
from app.security import SecretCipher

GenerationOperation = Literal["send", "edit", "regenerate"]


@dataclass(slots=True)
class PreparedGeneration:
    operation: GenerationOperation
    conversation: Conversation
    history: list[ChatMessage]
    current_user_message: ChatMessage
    assistant_message: ChatMessage
    replace_from_position: int | None
    model_targets: list[ModelTarget]
    stop_event: asyncio.Event


def message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        status=message.status,
        error_message=message.error_message,
        model_id=message.model_id,
        position=message.position,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def conversation_persona_response(
    conversation: Conversation,
) -> ConversationPersonaResponse | None:
    if conversation.persona_name is None or conversation.persona_instruction_role is None:
        return None
    return ConversationPersonaResponse(
        source_persona_id=conversation.persona_id,
        name=conversation.persona_name,
        description=conversation.persona_description or "",
        instructions=conversation.persona_instructions or "",
        instruction_role=conversation.persona_instruction_role,
    )


async def conversation_response(
    session: AsyncSession, conversation: Conversation
) -> ConversationResponse:
    messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.position.asc())
        )
    )
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        persona=conversation_persona_response(conversation),
        messages=[message_response(message) for message in messages],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
    *,
    for_update: bool = False,
) -> Conversation:
    query = select(Conversation).where(Conversation.id == conversation_id)
    if for_update:
        query = query.with_for_update()
    conversation = await session.scalar(query)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _title_from_message(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= 60:
        return normalized
    return f"{normalized[:57].rstrip()}..."


def _persona_configuration(conversation: Conversation) -> PersonaConfiguration:
    if conversation.persona_name is None or conversation.persona_instruction_role is None:
        return PersonaConfiguration(
            name="",
            instructions="",
            enabled=False,
            instruction_role=MessageRole.DEVELOPER,
        )
    return PersonaConfiguration(
        name=conversation.persona_name,
        instructions=conversation.persona_instructions or "",
        enabled=True,
        instruction_role=MessageRole(conversation.persona_instruction_role),
    )


def _canonical_history(messages: Sequence[ChatMessage]) -> list[CanonicalMessage]:
    history: list[CanonicalMessage] = []
    for message in messages:
        if message.status != "completed":
            continue
        if message.role == "user":
            history.append(
                CanonicalMessage(
                    role=MessageRole.USER,
                    source=MessageSource.USER,
                    content=message.content,
                )
            )
        elif message.role == "assistant":
            history.append(
                CanonicalMessage(
                    role=MessageRole.ASSISTANT,
                    source=MessageSource.ASSISTANT,
                    content=message.content,
                )
            )
    return history


def _provider_messages(messages: Sequence[CanonicalMessage]) -> list[dict[str, str]]:
    return [{"role": message.role.value, "content": message.content} for message in messages]


def _sse(event: str, payload: object) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def ensure_no_active_generation(session: AsyncSession, conversation_id: UUID) -> None:
    active_message = await session.scalar(
        select(ChatMessage.id).where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.status == "streaming",
        )
    )
    if active_message is not None:
        raise HTTPException(
            status_code=409,
            detail="A response is already being generated for this conversation.",
        )


async def _messages_before(
    session: AsyncSession,
    conversation_id: UUID,
    position: int,
) -> list[ChatMessage]:
    return list(
        await session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.position < position,
            )
            .order_by(ChatMessage.position.asc())
        )
    )


async def _create_assistant_message(
    session: AsyncSession,
    *,
    conversation: Conversation,
    position: int,
    target: ModelTarget,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content="",
        status="streaming",
        model_id=target.provider_model_id,
        position=position,
    )
    session.add(message)
    await session.flush()
    return message


async def prepare_new_message(
    *,
    session: AsyncSession,
    cipher: SecretCipher,
    conversation_id: UUID,
    content: str,
) -> PreparedGeneration:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    targets = await resolve_chat_targets(session, cipher)
    existing_messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.position.asc())
        )
    )
    next_position = (existing_messages[-1].position + 1) if existing_messages else 1
    if not existing_messages and conversation.title == "New chat":
        conversation.title = _title_from_message(content)

    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=content,
        status="completed",
        position=next_position,
    )
    session.add(user_message)
    assistant_message = await _create_assistant_message(
        session,
        conversation=conversation,
        position=next_position + 1,
        target=targets[0],
    )
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(conversation)
    await session.refresh(user_message)
    await session.refresh(assistant_message)
    stop_event = await generation_registry.register(assistant_message.id)
    return PreparedGeneration(
        operation="send",
        conversation=conversation,
        history=existing_messages,
        current_user_message=user_message,
        assistant_message=assistant_message,
        replace_from_position=None,
        model_targets=targets,
        stop_event=stop_event,
    )


async def prepare_edit_and_resend(
    *,
    session: AsyncSession,
    cipher: SecretCipher,
    conversation_id: UUID,
    message_id: UUID,
    content: str,
) -> PreparedGeneration:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    targets = await resolve_chat_targets(session, cipher)
    user_message = await session.get(ChatMessage, message_id)
    if user_message is None or user_message.conversation_id != conversation.id:
        raise HTTPException(status_code=404, detail="Message not found")
    if user_message.role != "user" or user_message.status != "completed":
        raise HTTPException(status_code=422, detail="Only completed user messages can be edited.")

    previous_auto_title = _title_from_message(user_message.content)
    history = await _messages_before(session, conversation.id, user_message.position)
    await session.execute(
        delete(ChatMessage).where(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.position > user_message.position,
        )
    )
    user_message.content = content
    user_message.updated_at = datetime.now(UTC)
    if user_message.position == 1 and conversation.title == previous_auto_title:
        conversation.title = _title_from_message(content)
    assistant_message = await _create_assistant_message(
        session,
        conversation=conversation,
        position=user_message.position + 1,
        target=targets[0],
    )
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(conversation)
    await session.refresh(user_message)
    await session.refresh(assistant_message)
    stop_event = await generation_registry.register(assistant_message.id)
    return PreparedGeneration(
        operation="edit",
        conversation=conversation,
        history=history,
        current_user_message=user_message,
        assistant_message=assistant_message,
        replace_from_position=user_message.position,
        model_targets=targets,
        stop_event=stop_event,
    )


async def prepare_regeneration(
    *,
    session: AsyncSession,
    cipher: SecretCipher,
    conversation_id: UUID,
    message_id: UUID,
) -> PreparedGeneration:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    targets = await resolve_chat_targets(session, cipher)
    old_assistant = await session.get(ChatMessage, message_id)
    if old_assistant is None or old_assistant.conversation_id != conversation.id:
        raise HTTPException(status_code=404, detail="Message not found")
    if old_assistant.role != "assistant" or old_assistant.status == "streaming":
        raise HTTPException(
            status_code=422,
            detail="Only finished assistant messages can be regenerated.",
        )

    user_message = await session.scalar(
        select(ChatMessage).where(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.position == old_assistant.position - 1,
            ChatMessage.role == "user",
            ChatMessage.status == "completed",
        )
    )
    if user_message is None:
        raise HTTPException(
            status_code=409,
            detail="The assistant message does not have a valid user message before it.",
        )

    history = await _messages_before(session, conversation.id, user_message.position)
    await session.execute(
        delete(ChatMessage).where(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.position >= old_assistant.position,
        )
    )
    assistant_message = await _create_assistant_message(
        session,
        conversation=conversation,
        position=old_assistant.position,
        target=targets[0],
    )
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(conversation)
    await session.refresh(assistant_message)
    stop_event = await generation_registry.register(assistant_message.id)
    return PreparedGeneration(
        operation="regenerate",
        conversation=conversation,
        history=history,
        current_user_message=user_message,
        assistant_message=assistant_message,
        replace_from_position=old_assistant.position,
        model_targets=targets,
        stop_event=stop_event,
    )


async def next_delta_or_stop(
    iterator: AsyncIterator[str],
    stop_event: asyncio.Event,
) -> tuple[str | None, bool, bool]:
    next_task = asyncio.create_task(anext(iterator))
    stop_task = asyncio.create_task(stop_event.wait())
    done, _ = await asyncio.wait({next_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)

    if stop_task in done and stop_event.is_set():
        next_task.cancel()
        with suppress(asyncio.CancelledError, StopAsyncIteration):
            await next_task
        with suppress(asyncio.CancelledError, Exception):
            await iterator.aclose()
        return None, True, False

    stop_task.cancel()
    with suppress(asyncio.CancelledError):
        await stop_task
    try:
        return next_task.result(), False, False
    except StopAsyncIteration:
        return None, False, True


async def _persist_progress(
    session: AsyncSession,
    message: ChatMessage,
    content: str,
) -> None:
    message.content = content
    await session.commit()


async def _select_target(
    session: AsyncSession,
    message: ChatMessage,
    target: ModelTarget,
) -> None:
    message.model_id = target.provider_model_id
    await session.commit()
    await session.refresh(message)


async def _finalize_message(
    *,
    session: AsyncSession,
    conversation: Conversation,
    message: ChatMessage,
    content: str,
    status_value: Literal["completed", "failed", "stopped"],
    error_message: str | None,
) -> None:
    message.content = content
    message.status = status_value
    message.error_message = error_message
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(message)


def _target_payload(target: ModelTarget) -> dict[str, str]:
    return {
        "endpoint_id": str(target.endpoint_id),
        "endpoint_name": target.endpoint_name,
        "model_id": target.provider_model_id,
    }


def stream_response(
    *,
    prepared: PreparedGeneration,
    session: AsyncSession,
    client: OpenAICompatibleClient,
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        yield _sse(
            "meta",
            {
                "operation": prepared.operation,
                "conversation_id": str(prepared.conversation.id),
                "title": prepared.conversation.title,
                "replace_from_position": prepared.replace_from_position,
                "messages": [
                    message_response(message).model_dump(mode="json")
                    for message in (
                        [prepared.current_user_message, prepared.assistant_message]
                        if prepared.operation != "regenerate"
                        else [prepared.assistant_message]
                    )
                ],
                "assistant_message_id": str(prepared.assistant_message.id),
                "model": _target_payload(prepared.model_targets[0]),
            },
        )
        chunks: list[str] = []
        persisted_length = 0
        last_checkpoint = asyncio.get_running_loop().time()
        last_error: ModelEndpointError | None = None
        try:
            canonical_messages = compose_messages(
                persona=_persona_configuration(prepared.conversation),
                history=_canonical_history(prepared.history),
                current_user_message=prepared.current_user_message.content,
            )
            provider_messages = _provider_messages(canonical_messages)

            for target_index, target in enumerate(prepared.model_targets):
                if target_index > 0:
                    previous_target = prepared.model_targets[target_index - 1]
                    await _select_target(session, prepared.assistant_message, target)
                    yield _sse(
                        "fallback",
                        {
                            "from": _target_payload(previous_target),
                            "to": _target_payload(target),
                            "code": last_error.code if last_error else "unavailable",
                            "message": (
                                last_error.message
                                if last_error
                                else "The previous model was unavailable."
                            ),
                        },
                    )

                parameters = target.parameters
                iterator = client.stream_chat_completion(
                    base_url=target.base_url,
                    api_key=target.api_key,
                    model_id=target.provider_model_id,
                    messages=provider_messages,
                    temperature=parameters.temperature,
                    top_p=parameters.top_p,
                    max_output_tokens=parameters.max_output_tokens,
                    token_parameter=parameters.token_parameter,
                    reasoning_effort=parameters.reasoning_effort,
                )
                try:
                    while True:
                        delta, stopped, finished = await next_delta_or_stop(
                            iterator, prepared.stop_event
                        )
                        if stopped:
                            content = "".join(chunks)
                            await _finalize_message(
                                session=session,
                                conversation=prepared.conversation,
                                message=prepared.assistant_message,
                                content=content,
                                status_value="stopped",
                                error_message=None,
                            )
                            yield _sse(
                                "stopped",
                                {
                                    "message": message_response(
                                        prepared.assistant_message
                                    ).model_dump(mode="json")
                                },
                            )
                            return
                        if finished:
                            break
                        if delta is None:
                            continue

                        chunks.append(delta)
                        yield _sse("delta", {"content": delta})
                        content = "".join(chunks)
                        now = asyncio.get_running_loop().time()
                        if len(content) - persisted_length >= 512 or now - last_checkpoint >= 0.5:
                            await _persist_progress(session, prepared.assistant_message, content)
                            persisted_length = len(content)
                            last_checkpoint = now

                    if not chunks:
                        raise ModelEndpointError(
                            "empty_response",
                            "The endpoint completed without returning any content.",
                        )
                    break
                except ModelEndpointError as error:
                    has_next_target = target_index + 1 < len(prepared.model_targets)
                    if not chunks and has_next_target and can_fallback(error):
                        last_error = error
                        continue
                    raise

            content = "".join(chunks)
            await _finalize_message(
                session=session,
                conversation=prepared.conversation,
                message=prepared.assistant_message,
                content=content,
                status_value="completed",
                error_message=None,
            )
            yield _sse(
                "done",
                {
                    "message": message_response(prepared.assistant_message).model_dump(
                        mode="json"
                    )
                },
            )
        except ModelEndpointError as error:
            await _finalize_message(
                session=session,
                conversation=prepared.conversation,
                message=prepared.assistant_message,
                content="".join(chunks),
                status_value="failed",
                error_message=error.message[:500],
            )
            yield _sse("error", {"code": error.code, "message": error.message})
        except asyncio.CancelledError:
            status_value = "stopped" if prepared.stop_event.is_set() else "failed"
            error_message = (
                None if status_value == "stopped" else "The response stream was interrupted."
            )
            with suppress(Exception):
                await _finalize_message(
                    session=session,
                    conversation=prepared.conversation,
                    message=prepared.assistant_message,
                    content="".join(chunks),
                    status_value=status_value,
                    error_message=error_message,
                )
            raise
        except Exception:
            with suppress(Exception):
                await _finalize_message(
                    session=session,
                    conversation=prepared.conversation,
                    message=prepared.assistant_message,
                    content="".join(chunks),
                    status_value="failed",
                    error_message="The response stream failed.",
                )
            yield _sse(
                "error",
                {"code": "stream_failed", "message": "The response stream failed."},
            )
        finally:
            await generation_registry.unregister(prepared.assistant_message.id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


async def recover_interrupted_streams(session: AsyncSession) -> int:
    result = await session.execute(
        update(ChatMessage)
        .where(ChatMessage.status == "streaming")
        .values(
            status="failed",
            error_message="The response was interrupted before completion.",
            updated_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return result.rowcount or 0
