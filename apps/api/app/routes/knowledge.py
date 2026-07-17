from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_generation import ensure_no_active_generation, get_conversation
from app.config import settings
from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.document_processing import DocumentProcessingError
from app.knowledge_service import (
    collection_response,
    create_document,
    document_response,
    index_document,
)
from app.openai_compatible import OpenAICompatibleClient
from app.retrieval_models import (
    ConversationCollection,
    KnowledgeCollection,
    KnowledgeDocument,
)
from app.retrieval_schemas import (
    ConversationRetrievalSettingsResponse,
    ConversationRetrievalSettingsUpdate,
    KnowledgeCollectionCreate,
    KnowledgeCollectionResponse,
    KnowledgeCollectionUpdate,
    KnowledgeDocumentResponse,
)
from app.retrieval_service import (
    get_or_create_conversation_settings,
    replace_conversation_retrieval_settings,
    selected_collection_ids,
)
from app.security import SecretCipher
from app.tool_guards import ensure_no_pending_tool_confirmation

router = APIRouter(prefix="/api", tags=["knowledge"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ClientDep = Annotated[OpenAICompatibleClient, Depends(get_openai_client)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]


async def _get_collection(
    session: AsyncSession,
    collection_id: UUID,
) -> KnowledgeCollection:
    collection = await session.get(KnowledgeCollection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Knowledge collection not found")
    return collection


async def _get_document(session: AsyncSession, document_id: UUID) -> KnowledgeDocument:
    document = await session.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return document


async def _conversation_settings_response(
    session: AsyncSession,
    conversation_id: UUID,
) -> ConversationRetrievalSettingsResponse:
    retrieval_settings = await get_or_create_conversation_settings(session, conversation_id)
    collection_ids = await selected_collection_ids(session, conversation_id)
    collections = list(
        await session.scalars(
            select(KnowledgeCollection)
            .where(KnowledgeCollection.id.in_(collection_ids))
            .order_by(KnowledgeCollection.name.asc())
        )
    ) if collection_ids else []
    await session.commit()
    return ConversationRetrievalSettingsResponse(
        conversation_id=conversation_id,
        memory_enabled=retrieval_settings.memory_enabled,
        rag_enabled=retrieval_settings.rag_enabled,
        collections=[await collection_response(session, item) for item in collections],
    )


@router.get("/knowledge-collections", response_model=list[KnowledgeCollectionResponse])
async def list_collections(session: SessionDep) -> list[KnowledgeCollectionResponse]:
    collections = list(
        await session.scalars(select(KnowledgeCollection).order_by(KnowledgeCollection.name.asc()))
    )
    return [await collection_response(session, collection) for collection in collections]


@router.post(
    "/knowledge-collections",
    response_model=KnowledgeCollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    payload: KnowledgeCollectionCreate,
    session: SessionDep,
) -> KnowledgeCollectionResponse:
    collection = KnowledgeCollection(**payload.model_dump())
    session.add(collection)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Collection name already exists") from error
    await session.refresh(collection)
    return await collection_response(session, collection)


@router.put(
    "/knowledge-collections/{collection_id}",
    response_model=KnowledgeCollectionResponse,
)
async def update_collection(
    collection_id: UUID,
    payload: KnowledgeCollectionUpdate,
    session: SessionDep,
) -> KnowledgeCollectionResponse:
    collection = await _get_collection(session, collection_id)
    collection.name = payload.name
    collection.description = payload.description
    collection.enabled = payload.enabled
    collection.default_enabled = payload.default_enabled if payload.enabled else False
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Collection name already exists") from error
    await session.refresh(collection)
    return await collection_response(session, collection)


@router.delete(
    "/knowledge-collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_collection(collection_id: UUID, session: SessionDep) -> Response:
    collection = await _get_collection(session, collection_id)
    await session.delete(collection)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/knowledge-documents", response_model=list[KnowledgeDocumentResponse])
async def list_documents(
    session: SessionDep,
    collection_id: UUID | None = None,
) -> list[KnowledgeDocumentResponse]:
    query = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    if collection_id is not None:
        query = query.where(KnowledgeDocument.collection_id == collection_id)
    documents = list(await session.scalars(query))
    return [await document_response(session, document) for document in documents]


@router.post(
    "/knowledge-collections/{collection_id}/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    collection_id: UUID,
    request: Request,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
    filename: Annotated[str, Query(min_length=1, max_length=255)],
) -> KnowledgeDocumentResponse:
    collection = await _get_collection(session, collection_id)
    if not collection.enabled:
        raise HTTPException(status_code=422, detail="Documents cannot be added to a disabled collection")
    data = await request.body()
    media_type = request.headers.get("content-type", "application/octet-stream")
    try:
        document = await create_document(
            session,
            collection=collection,
            filename=filename,
            media_type=media_type,
            data=data,
            client=client,
            cipher=cipher,
            settings=settings,
        )
    except DocumentProcessingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return await document_response(session, document)


@router.post(
    "/knowledge-documents/{document_id}/reindex",
    response_model=KnowledgeDocumentResponse,
)
async def reindex_document(
    document_id: UUID,
    session: SessionDep,
    client: ClientDep,
    cipher: CipherDep,
) -> KnowledgeDocumentResponse:
    document = await _get_document(session, document_id)
    try:
        await index_document(
            session,
            document,
            client=client,
            cipher=cipher,
            settings=settings,
        )
    except DocumentProcessingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return await document_response(session, document)


@router.delete(
    "/knowledge-documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(document_id: UUID, session: SessionDep) -> Response:
    document = await _get_document(session, document_id)
    await session.delete(document)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/retrieval-settings",
    response_model=ConversationRetrievalSettingsResponse,
)
async def read_conversation_retrieval_settings(
    conversation_id: UUID,
    session: SessionDep,
) -> ConversationRetrievalSettingsResponse:
    await get_conversation(session, conversation_id)
    return await _conversation_settings_response(session, conversation_id)


@router.put(
    "/conversations/{conversation_id}/retrieval-settings",
    response_model=ConversationRetrievalSettingsResponse,
)
async def update_conversation_retrieval_settings(
    conversation_id: UUID,
    payload: ConversationRetrievalSettingsUpdate,
    session: SessionDep,
) -> ConversationRetrievalSettingsResponse:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    await ensure_no_pending_tool_confirmation(session, conversation.id)
    try:
        await replace_conversation_retrieval_settings(
            session,
            conversation_id=conversation.id,
            memory_enabled=payload.memory_enabled,
            rag_enabled=payload.rag_enabled,
            collection_ids=payload.collection_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return await _conversation_settings_response(session, conversation.id)


@router.delete(
    "/conversations/{conversation_id}/retrieval-settings/collections",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_conversation_collections(
    conversation_id: UUID,
    session: SessionDep,
) -> Response:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    await ensure_no_pending_tool_confirmation(session, conversation.id)
    await session.execute(
        delete(ConversationCollection).where(
            ConversationCollection.conversation_id == conversation.id
        )
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
