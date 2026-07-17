from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_generation import (
    conversation_response,
    ensure_no_active_generation,
    get_conversation,
    prepare_edit_and_resend,
    prepare_new_message,
    prepare_regeneration,
    stream_response,
)
from app.chat_runtime import generation_registry
from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.models import ChatMessage, Conversation, Persona, PersonaPreferences
from app.openai_compatible import OpenAICompatibleClient
from app.schemas import (
    ConversationCreate,
    ConversationImportRequest,
    ConversationResponse,
    ConversationSummaryResponse,
    ConversationUpdate,
    SendMessageRequest,
    StopGenerationResponse,
)
from app.security import SecretCipher

router = APIRouter(prefix="/api", tags=["chat"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]
ClientDep = Annotated[OpenAICompatibleClient, Depends(get_openai_client)]


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _clear_persona_snapshot(conversation: Conversation) -> None:
    conversation.persona_id = None
    conversation.persona_name = None
    conversation.persona_description = None
    conversation.persona_instructions = None
    conversation.persona_instruction_role = None


def _apply_persona_snapshot(conversation: Conversation, persona: Persona | None) -> None:
    if persona is None:
        _clear_persona_snapshot(conversation)
        return
    conversation.persona_id = persona.id
    conversation.persona_name = persona.name
    conversation.persona_description = persona.description
    conversation.persona_instructions = persona.instructions
    conversation.persona_instruction_role = persona.instruction_role


async def _resolve_persona(
    session: AsyncSession,
    *,
    use_default_persona: bool,
    persona_id: UUID | None,
) -> Persona | None:
    if use_default_persona:
        preferences = await session.get(PersonaPreferences, 1)
        if preferences is None or preferences.default_persona_id is None:
            return None
        persona = await session.get(Persona, preferences.default_persona_id)
    elif persona_id is None:
        return None
    else:
        persona = await session.get(Persona, persona_id)
        if persona is None:
            raise HTTPException(status_code=404, detail="Persona not found")

    if persona is None or not persona.enabled:
        return None
    return persona


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
async def list_conversations(
    session: SessionDep,
    query: Annotated[str | None, Query(max_length=200)] = None,
) -> list[ConversationSummaryResponse]:
    message_count = (
        select(
            ChatMessage.conversation_id,
            func.count(ChatMessage.id).label("message_count"),
        )
        .group_by(ChatMessage.conversation_id)
        .subquery()
    )
    statement = select(Conversation, func.coalesce(message_count.c.message_count, 0)).outerjoin(
        message_count,
        message_count.c.conversation_id == Conversation.id,
    )

    normalized_query = query.strip() if query else ""
    if normalized_query:
        pattern = _contains_pattern(normalized_query)
        matching_message = exists(
            select(ChatMessage.id).where(
                ChatMessage.conversation_id == Conversation.id,
                ChatMessage.content.ilike(pattern, escape="\\"),
            )
        )
        statement = statement.where(
            or_(Conversation.title.ilike(pattern, escape="\\"), matching_message)
        )

    rows = (
        await session.execute(
            statement.order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        )
    ).all()
    return [
        ConversationSummaryResponse(
            id=conversation.id,
            title=conversation.title,
            message_count=count,
            persona_name=conversation.persona_name,
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
    persona = await _resolve_persona(
        session,
        use_default_persona=payload.use_default_persona,
        persona_id=payload.persona_id,
    )
    _apply_persona_snapshot(conversation, persona)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return await conversation_response(session, conversation)


@router.post(
    "/conversations/import",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_conversation(
    payload: ConversationImportRequest,
    session: SessionDep,
) -> ConversationResponse:
    conversation = Conversation(title=payload.title)
    if payload.persona is not None:
        source_persona = (
            await session.get(Persona, payload.persona.source_persona_id)
            if payload.persona.source_persona_id is not None
            else None
        )
        conversation.persona_id = source_persona.id if source_persona else None
        conversation.persona_name = payload.persona.name
        conversation.persona_description = payload.persona.description
        conversation.persona_instructions = payload.persona.instructions
        conversation.persona_instruction_role = payload.persona.instruction_role
    session.add(conversation)
    await session.flush()

    now = datetime.now(UTC)
    session.add_all(
        [
            ChatMessage(
                conversation_id=conversation.id,
                role=message.role,
                content=message.content,
                status=message.status,
                error_message=message.error_message,
                model_id=message.model_id,
                position=position,
                created_at=now,
                updated_at=now,
            )
            for position, message in enumerate(payload.messages)
        ]
    )
    await session.commit()
    await session.refresh(conversation)
    return await conversation_response(session, conversation)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def read_conversation(
    conversation_id: UUID,
    session: SessionDep,
) -> ConversationResponse:
    conversation = await get_conversation(session, conversation_id)
    return await conversation_response(session, conversation)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    session: SessionDep,
) -> ConversationResponse:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    if "title" in payload.model_fields_set and payload.title is not None:
        conversation.title = payload.title
    if "persona_id" in payload.model_fields_set:
        await ensure_no_active_generation(session, conversation.id)
        persona = await _resolve_persona(
            session,
            use_default_persona=False,
            persona_id=payload.persona_id,
        )
        _apply_persona_snapshot(conversation, persona)
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(conversation)
    return await conversation_response(session, conversation)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    session: SessionDep,
) -> Response:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
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
    prepared = await prepare_new_message(
        session=session,
        cipher=cipher,
        conversation_id=conversation_id,
        content=payload.content,
    )
    return stream_response(prepared=prepared, session=session, client=client)


@router.post("/conversations/{conversation_id}/messages/{message_id}/edit-and-resend")
async def edit_and_resend_message(
    conversation_id: UUID,
    message_id: UUID,
    payload: SendMessageRequest,
    session: SessionDep,
    cipher: CipherDep,
    client: ClientDep,
) -> StreamingResponse:
    prepared = await prepare_edit_and_resend(
        session=session,
        cipher=cipher,
        conversation_id=conversation_id,
        message_id=message_id,
        content=payload.content,
    )
    return stream_response(prepared=prepared, session=session, client=client)


@router.post("/conversations/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    conversation_id: UUID,
    message_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    client: ClientDep,
) -> StreamingResponse:
    prepared = await prepare_regeneration(
        session=session,
        cipher=cipher,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    return stream_response(prepared=prepared, session=session, client=client)


@router.post("/messages/{message_id}/stop", response_model=StopGenerationResponse)
async def stop_generation(
    message_id: UUID,
    session: SessionDep,
) -> StopGenerationResponse:
    message = await session.get(ChatMessage, message_id)
    if message is None or message.role != "assistant":
        raise HTTPException(status_code=404, detail="Assistant message not found")
    if message.status != "streaming":
        raise HTTPException(status_code=409, detail="The response is not currently streaming.")
    if not await generation_registry.stop(message.id):
        raise HTTPException(
            status_code=409,
            detail="The response is no longer active in this application process.",
        )
    return StopGenerationResponse(message_id=message.id)
