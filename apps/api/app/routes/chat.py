import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.message_composition import (
    CanonicalMessage,
    MessageRole,
    MessageSource,
    PersonaConfiguration,
    compose_messages,
)
from app.models import (
    ChatMessage,
    Conversation,
    ModelCacheEntry,
    ModelEndpoint,
    ModelPreferences,
    PersonaSettings,
)
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.schemas import (
    ChatMessageResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationSummaryResponse,
    ConversationUpdate,
    SendMessageRequest,
)
from app.security import SecretCipher

router = APIRouter(prefix="/api", tags=["chat"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]
ClientDep = Annotated[OpenAICompatibleClient, Depends(get_openai_client)]


def _message_response(message: ChatMessage) -> ChatMessageResponse:
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


async def _conversation_response(
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
        messages=[_message_response(message) for message in messages],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def _get_conversation(session: AsyncSession, conversation_id: UUID) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _title_from_message(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= 60:
        return normalized
    return f"{normalized[:57].rstrip()}..."


def _persona_configuration(persona: PersonaSettings | None) -> PersonaConfiguration:
    if persona is None:
        return PersonaConfiguration(
            name="",
            instructions="",
            enabled=False,
            instruction_role=MessageRole.DEVELOPER,
        )
    return PersonaConfiguration(
        name=persona.name,
        instructions=persona.instructions,
        enabled=persona.enabled,
        instruction_role=MessageRole(persona.instruction_role),
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


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
async def list_conversations(session: SessionDep) -> list[ConversationSummaryResponse]:
    message_count = (
        select(
            ChatMessage.conversation_id,
            func.count(ChatMessage.id).label("message_count"),
        )
        .group_by(ChatMessage.conversation_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Conversation, func.coalesce(message_count.c.message_count, 0))
            .outerjoin(message_count, message_count.c.conversation_id == Conversation.id)
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        )
    ).all()
    return [
        ConversationSummaryResponse(
            id=conversation.id,
            title=conversation.title,
            message_count=count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation, count in rows
    ]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    session: SessionDep,
) -> ConversationResponse:
    conversation = Conversation(title=payload.title or "New chat")
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return await _conversation_response(session, conversation)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    session: SessionDep,
) -> ConversationResponse:
    conversation = await _get_conversation(session, conversation_id)
    return await _conversation_response(session, conversation)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    session: SessionDep,
) -> ConversationResponse:
    conversation = await _get_conversation(session, conversation_id)
    conversation.title = payload.title
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(conversation)
    return await _conversation_response(session, conversation)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    session: SessionDep,
) -> Response:
    conversation = await _get_conversation(session, conversation_id)
    await session.delete(conversation)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    session: SessionDep,
    cipher: CipherDep,
    client: ClientDep,
) -> StreamingResponse:
    conversation = await _get_conversation(session, conversation_id)
    preferences = await session.get(ModelPreferences, 1)
    if preferences is None or preferences.primary_model_id is None:
        raise HTTPException(
            status_code=409,
            detail="Configure a primary model before starting a chat.",
        )

    target = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .where(ModelCacheEntry.id == preferences.primary_model_id)
        )
    ).one_or_none()
    if target is None:
        raise HTTPException(status_code=409, detail="The primary model is no longer available.")
    model, endpoint = target
    if not endpoint.enabled:
        raise HTTPException(status_code=409, detail="The primary model endpoint is disabled.")

    existing_messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.position.asc())
        )
    )
    next_position = (existing_messages[-1].position + 1) if existing_messages else 1
    now = datetime.now(UTC)
    if not existing_messages and conversation.title == "New chat":
        conversation.title = _title_from_message(payload.content)

    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=payload.content,
        status="completed",
        position=next_position,
    )
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content="",
        status="streaming",
        model_id=model.model_id,
        position=next_position + 1,
    )
    conversation.updated_at = now
    session.add_all([user_message, assistant_message])
    await session.commit()
    await session.refresh(conversation)
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    persona = await session.get(PersonaSettings, 1)
    canonical_messages = compose_messages(
        persona=_persona_configuration(persona),
        history=_canonical_history(existing_messages),
        current_user_message=payload.content,
    )
    api_key = None
    if endpoint.encrypted_api_key is not None:
        api_key = cipher.decrypt(endpoint.encrypted_api_key)

    async def event_stream() -> AsyncIterator[str]:
        yield _sse(
            "meta",
            {
                "conversation_id": str(conversation.id),
                "title": conversation.title,
                "user_message": _message_response(user_message).model_dump(mode="json"),
                "assistant_message": _message_response(assistant_message).model_dump(mode="json"),
            },
        )
        chunks: list[str] = []
        try:
            async for delta in client.stream_chat_completion(
                base_url=endpoint.base_url,
                api_key=api_key,
                model_id=model.model_id,
                messages=_provider_messages(canonical_messages),
            ):
                chunks.append(delta)
                yield _sse("delta", {"content": delta})

            assistant_message.content = "".join(chunks)
            assistant_message.status = "completed"
            assistant_message.error_message = None
            conversation.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(assistant_message)
            yield _sse(
                "done",
                {"message": _message_response(assistant_message).model_dump(mode="json")},
            )
        except ModelEndpointError as error:
            assistant_message.content = "".join(chunks)
            assistant_message.status = "failed"
            assistant_message.error_message = error.message[:500]
            conversation.updated_at = datetime.now(UTC)
            await session.commit()
            yield _sse("error", {"code": error.code, "message": error.message})
        except asyncio.CancelledError:
            assistant_message.content = "".join(chunks)
            assistant_message.status = "failed"
            assistant_message.error_message = "The response stream was interrupted."
            conversation.updated_at = datetime.now(UTC)
            await session.commit()
            raise
        except Exception:
            assistant_message.content = "".join(chunks)
            assistant_message.status = "failed"
            assistant_message.error_message = "The response stream failed."
            conversation.updated_at = datetime.now(UTC)
            await session.commit()
            yield _sse(
                "error",
                {"code": "stream_failed", "message": "The response stream failed."},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
