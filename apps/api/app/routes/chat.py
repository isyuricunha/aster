from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
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
from app.models import ChatMessage, Conversation
from app.openai_compatible import OpenAICompatibleClient
from app.schemas import (
    ConversationCreate,
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
    conversation = await get_conversation(session, conversation_id)
    conversation.title = payload.title
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
