import hashlib
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.document_processing import DocumentProcessingError, chunk_document, extract_document_text
from app.models import ModelCacheEntry
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.retrieval_models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
)
from app.retrieval_schemas import (
    KnowledgeCollectionResponse,
    KnowledgeDocumentResponse,
)
from app.retrieval_service import collection_counts, embed_texts, get_embedding_target
from app.security import SecretCipher


async def collection_response(
    session: AsyncSession,
    collection: KnowledgeCollection,
) -> KnowledgeCollectionResponse:
    document_count, ready_document_count, chunk_count = await collection_counts(
        session, collection.id
    )
    return KnowledgeCollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        enabled=collection.enabled,
        default_enabled=collection.default_enabled,
        document_count=document_count,
        ready_document_count=ready_document_count,
        chunk_count=chunk_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


async def document_response(
    session: AsyncSession,
    document: KnowledgeDocument,
) -> KnowledgeDocumentResponse:
    collection = await session.get(KnowledgeCollection, document.collection_id)
    collection_name = collection.name if collection else "Deleted collection"
    embedded_chunk_count = await session.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.document_id == document.id,
            KnowledgeChunk.embedding.is_not(None),
        )
    )
    return KnowledgeDocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        collection_name=collection_name,
        filename=document.filename,
        media_type=document.media_type,
        size_bytes=document.size_bytes,
        content_sha256=document.content_sha256,
        status=document.status,
        error_message=document.error_message,
        chunk_count=document.chunk_count,
        embedded_chunk_count=embedded_chunk_count or 0,
        embedding_model_id=document.embedding_model_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


async def index_document(
    session: AsyncSession,
    document: KnowledgeDocument,
    *,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
    settings: Settings,
) -> None:
    document.status = "processing"
    document.error_message = None
    document.embedding_model_id = None
    await session.execute(
        delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id)
    )
    chunks = chunk_document(
        document.extracted_text,
        chunk_characters=settings.aster_document_chunk_characters,
        overlap=settings.aster_document_chunk_overlap,
        max_chunks=settings.aster_document_max_chunks,
    )
    target = await get_embedding_target(session, cipher)
    vectors: list[list[float] | None] = [None] * len(chunks)
    if target is not None:
        try:
            embedded = await embed_texts(
                client,
                target,
                chunks,
                batch_size=settings.aster_embedding_batch_size,
            )
            vectors = list(embedded)
            document.embedding_model_id = target.model_id
        except ModelEndpointError as error:
            document.error_message = (
                f"Lexical indexing completed, but embeddings failed: {error.message}"
            )[:500]

    session.add_all(
        KnowledgeChunk(
            document_id=document.id,
            position=position,
            content=content,
            character_count=len(content),
            embedding=vectors[position],
        )
        for position, content in enumerate(chunks)
    )
    document.chunk_count = len(chunks)
    document.status = "ready"
    await session.commit()
    await session.refresh(document)


async def create_document(
    session: AsyncSession,
    *,
    collection: KnowledgeCollection,
    filename: str,
    media_type: str,
    data: bytes,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
    settings: Settings,
) -> KnowledgeDocument:
    if not data:
        raise DocumentProcessingError("The uploaded document is empty.")
    if len(data) > settings.aster_document_max_bytes:
        raise DocumentProcessingError(
            f"The uploaded document exceeds the {settings.aster_document_max_bytes:,}-byte limit."
        )
    extracted_text = extract_document_text(
        data,
        filename=filename,
        media_type=media_type,
        max_characters=settings.aster_document_max_characters,
    )
    digest = hashlib.sha256(data).hexdigest()
    duplicate = await session.scalar(
        select(KnowledgeDocument.id).where(
            KnowledgeDocument.collection_id == collection.id,
            KnowledgeDocument.content_sha256 == digest,
        )
    )
    if duplicate is not None:
        raise ValueError("This collection already contains the same document content")
    document = KnowledgeDocument(
        collection_id=collection.id,
        filename=filename,
        media_type=media_type,
        size_bytes=len(data),
        content_sha256=digest,
        extracted_text=extracted_text,
        status="processing",
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    try:
        await index_document(
            session,
            document,
            client=client,
            cipher=cipher,
            settings=settings,
        )
    except Exception as error:
        document.status = "failed"
        document.error_message = str(error)[:500]
        await session.commit()
        await session.refresh(document)
        raise
    return document


async def clear_embeddings_for_model(
    session: AsyncSession,
    model_id: UUID,
) -> None:
    document_ids = list(
        await session.scalars(
            select(KnowledgeDocument.id).where(
                KnowledgeDocument.embedding_model_id == model_id
            )
        )
    )
    if document_ids:
        await session.execute(
            KnowledgeChunk.__table__.update()
            .where(KnowledgeChunk.document_id.in_(document_ids))
            .values(embedding=None)
        )
        await session.execute(
            KnowledgeDocument.__table__.update()
            .where(KnowledgeDocument.id.in_(document_ids))
            .values(embedding_model_id=None)
        )
    await session.execute(
        ModelCacheEntry.__table__.update()
        .where(ModelCacheEntry.id == model_id)
        .values(updated_at=ModelCacheEntry.updated_at)
    )
