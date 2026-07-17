from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_generation import get_conversation
from app.config import settings
from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.memory_service import (
    generate_memory_suggestions,
    list_memory_responses,
    memory_response,
    suggestion_response,
)
from app.models import ModelCacheEntry, ModelEndpoint, Persona
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.retrieval_models import Memory, MemorySuggestion, RetrievalPreferences
from app.retrieval_schemas import (
    MemoryCreate,
    MemoryResponse,
    MemorySuggestionAccept,
    MemorySuggestionResponse,
    MemoryTransferItem,
    MemoryTransferRequest,
    MemoryUpdate,
    RetrievalPreferencesResponse,
    RetrievalPreferencesUpdate,
)
from app.retrieval_service import embed_memory
from app.schemas import SelectedModelResponse
from app.security import SecretCipher

router = APIRouter(prefix="/api", tags=["memory"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ClientDep = Annotated[OpenAICompatibleClient, Depends(get_openai_client)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]


async def _get_memory(session: AsyncSession, memory_id: UUID) -> Memory:
    memory = await session.get(Memory, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


async def _get_suggestion(session: AsyncSession, suggestion_id: UUID) -> MemorySuggestion:
    suggestion = await session.get(MemorySuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Memory suggestion not found")
    return suggestion


async def _validate_persona(session: AsyncSession, persona_id: UUID | None) -> Persona | None:
    if persona_id is None:
        return None
    persona = await session.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status_code=422, detail="The selected persona does not exist")
    return persona


async def _try_embed(
    session: AsyncSession,
    memory: Memory,
    *,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
) -> None:
    try:
        await embed_memory(
            session,
            memory,
            client=client,
            cipher=cipher,
            settings=settings,
        )
    except ModelEndpointError:
        memory.embedding = None
        memory.embedding_model_id = None


async def _selected_model(
    session: AsyncSession,
    model_id: UUID | None,
) -> SelectedModelResponse | None:
    if model_id is None:
        return None
    row = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .where(ModelCacheEntry.id == model_id)
        )
    ).one_or_none()
    if row is None:
        return None
    model, endpoint = row
    return SelectedModelResponse(
        id=model.id,
        endpoint_id=endpoint.id,
        endpoint_name=endpoint.name,
        model_id=model.model_id,
        endpoint_enabled=endpoint.enabled,
        is_available=model.is_available,
    )


async def _get_or_create_preferences(session: AsyncSession) -> RetrievalPreferences:
    preferences = await session.get(RetrievalPreferences, 1)
    if preferences is None:
        preferences = RetrievalPreferences(id=1)
        session.add(preferences)
        await session.flush()
    return preferences


@router.get("/retrieval-preferences", response_model=RetrievalPreferencesResponse)
async def get_retrieval_preferences(session: SessionDep) -> RetrievalPreferencesResponse:
    preferences = await _get_or_create_preferences(session)
    await session.commit()
    return RetrievalPreferencesResponse(
        embedding_model=await _selected_model(session, preferences.embedding_model_id)
    )


@router.put("/retrieval-preferences", response_model=RetrievalPreferencesResponse)
async def update_retrieval_preferences(
    payload: RetrievalPreferencesUpdate,
    session: SessionDep,
) -> RetrievalPreferencesResponse:
    if payload.embedding_model_id is not None:
        row = (
            await session.execute(
                select(ModelCacheEntry, ModelEndpoint)
                .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
                .where(ModelCacheEntry.id == payload.embedding_model_id)
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(status_code=422, detail="The selected embedding model does not exist")
        model, endpoint = row
        if not endpoint.enabled or not model.is_available:
            raise HTTPException(status_code=422, detail="The selected embedding model is unavailable")
    preferences = await _get_or_create_preferences(session)
    preferences.embedding_model_id = payload.embedding_model_id
    await session.commit()
    await session.refresh(preferences)
    return RetrievalPreferencesResponse(
        embedding_model=await _selected_model(session, preferences.embedding_model_id)
    )


@router.get("/memories", response_model=list[MemoryResponse])
async def list_memories(
    session: SessionDep,
    persona_id: UUID | None = None,
) -> list[MemoryResponse]:
    return await list_memory_responses(session, persona_id=persona_id)


@router.post("/memories", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> MemoryResponse:
    persona = await _validate_persona(session, payload.persona_id)
    memory = Memory(
        persona_id=payload.persona_id,
        content=payload.content,
        category=payload.category,
        enabled=payload.enabled,
        source_type="manual",
    )
    session.add(memory)
    await session.flush()
    await _try_embed(session, memory, client=client, cipher=cipher)
    await session.commit()
    await session.refresh(memory)
    return memory_response(memory, persona.name if persona else None)


@router.put("/memories/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    payload: MemoryUpdate,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> MemoryResponse:
    memory = await _get_memory(session, memory_id)
    persona = await _validate_persona(session, payload.persona_id)
    content_changed = memory.content != payload.content
    memory.persona_id = payload.persona_id
    memory.content = payload.content
    memory.category = payload.category
    memory.enabled = payload.enabled
    if content_changed:
        await _try_embed(session, memory, client=client, cipher=cipher)
    await session.commit()
    await session.refresh(memory)
    return memory_response(memory, persona.name if persona else None)


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: UUID, session: SessionDep) -> Response:
    memory = await _get_memory(session, memory_id)
    await session.delete(memory)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/memories/reindex", response_model=list[MemoryResponse])
async def reindex_memories(
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> list[MemoryResponse]:
    memories = list(await session.scalars(select(Memory).order_by(Memory.created_at.asc())))
    for memory in memories:
        await _try_embed(session, memory, client=client, cipher=cipher)
    await session.commit()
    return await list_memory_responses(session)


@router.get("/memories/export", response_model=MemoryTransferRequest)
async def export_memories(session: SessionDep) -> MemoryTransferRequest:
    rows = (
        await session.execute(
            select(Memory, Persona.name)
            .outerjoin(Persona, Persona.id == Memory.persona_id)
            .order_by(Memory.created_at.asc())
        )
    ).all()
    return MemoryTransferRequest(
        format="aster-memories",
        version=1,
        memories=[
            MemoryTransferItem(
                content=memory.content,
                category=memory.category,
                persona_name=persona_name,
                enabled=memory.enabled,
            )
            for memory, persona_name in rows
        ],
    )


@router.post("/memories/import", response_model=list[MemoryResponse])
async def import_memories(
    payload: MemoryTransferRequest,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> list[MemoryResponse]:
    personas = {
        persona.name.casefold(): persona
        for persona in await session.scalars(select(Persona))
    }
    existing = {
        (memory.persona_id, memory.content.casefold())
        for memory in await session.scalars(select(Memory))
    }
    for item in payload.memories:
        persona = personas.get(item.persona_name.casefold()) if item.persona_name else None
        if item.persona_name and persona is None:
            raise HTTPException(
                status_code=422,
                detail=f'Persona "{item.persona_name}" does not exist on this installation',
            )
        key = (persona.id if persona else None, item.content.casefold())
        if key in existing:
            continue
        memory = Memory(
            persona_id=persona.id if persona else None,
            content=item.content,
            category=item.category,
            enabled=item.enabled,
            source_type="imported",
        )
        session.add(memory)
        await session.flush()
        await _try_embed(session, memory, client=client, cipher=cipher)
        existing.add(key)
    await session.commit()
    return await list_memory_responses(session)


@router.get("/memory-suggestions", response_model=list[MemorySuggestionResponse])
async def list_memory_suggestions(
    session: SessionDep,
    conversation_id: UUID | None = None,
    status_filter: str | None = None,
) -> list[MemorySuggestionResponse]:
    query = select(MemorySuggestion)
    if conversation_id is not None:
        query = query.where(MemorySuggestion.conversation_id == conversation_id)
    if status_filter is not None:
        if status_filter not in {"pending", "accepted", "rejected"}:
            raise HTTPException(status_code=422, detail="Invalid suggestion status")
        query = query.where(MemorySuggestion.status == status_filter)
    suggestions = list(
        await session.scalars(query.order_by(MemorySuggestion.created_at.desc()))
    )
    return [suggestion_response(suggestion) for suggestion in suggestions]


@router.post(
    "/conversations/{conversation_id}/memory-suggestions/generate",
    response_model=list[MemorySuggestionResponse],
)
async def generate_suggestions(
    conversation_id: UUID,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> list[MemorySuggestionResponse]:
    conversation = await get_conversation(session, conversation_id)
    suggestions = await generate_memory_suggestions(
        session,
        conversation=conversation,
        client=client,
        cipher=cipher,
        settings=settings,
    )
    return [suggestion_response(suggestion) for suggestion in suggestions]


@router.post(
    "/memory-suggestions/{suggestion_id}/accept",
    response_model=MemoryResponse,
)
async def accept_suggestion(
    suggestion_id: UUID,
    payload: MemorySuggestionAccept,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> MemoryResponse:
    suggestion = await _get_suggestion(session, suggestion_id)
    if suggestion.status != "pending":
        raise HTTPException(status_code=409, detail="This suggestion is no longer pending")
    persona_id = payload.persona_id if "persona_id" in payload.model_fields_set else suggestion.persona_id
    persona = await _validate_persona(session, persona_id)
    memory = Memory(
        persona_id=persona_id,
        content=payload.content or suggestion.content,
        category=payload.category or suggestion.category,
        enabled=True,
        source_type="suggested",
        source_conversation_id=suggestion.conversation_id,
    )
    session.add(memory)
    await session.flush()
    await _try_embed(session, memory, client=client, cipher=cipher)
    suggestion.status = "accepted"
    suggestion.resolved_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(memory)
    return memory_response(memory, persona.name if persona else None)


@router.post(
    "/memory-suggestions/{suggestion_id}/reject",
    response_model=MemorySuggestionResponse,
)
async def reject_suggestion(
    suggestion_id: UUID,
    session: SessionDep,
) -> MemorySuggestionResponse:
    suggestion = await _get_suggestion(session, suggestion_id)
    if suggestion.status != "pending":
        raise HTTPException(status_code=409, detail="This suggestion is no longer pending")
    suggestion.status = "rejected"
    suggestion.resolved_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(suggestion)
    return suggestion_response(suggestion)
