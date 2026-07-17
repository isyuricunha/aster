from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas import SelectedModelResponse

MemoryCategory = Literal["fact", "preference", "project", "relationship", "instruction", "other"]


def _normalize_single_line(value: str, *, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


class RetrievalPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding_model_id: UUID | None = None


class RetrievalPreferencesResponse(BaseModel):
    embedding_model: SelectedModelResponse | None


class MemoryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: Annotated[str, Field(min_length=1, max_length=4_000)]
    category: MemoryCategory = "fact"
    persona_id: UUID | None = None
    enabled: bool = True

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return _normalize_single_line(value, field_name="Memory content")


class MemoryCreate(MemoryPayload):
    pass


class MemoryUpdate(MemoryPayload):
    pass


class MemoryResponse(BaseModel):
    id: UUID
    content: str
    category: MemoryCategory
    persona_id: UUID | None
    persona_name: str | None
    enabled: bool
    source_type: Literal["manual", "suggested", "imported"]
    source_conversation_id: UUID | None
    has_embedding: bool
    created_at: datetime
    updated_at: datetime


class MemoryTransferItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: Annotated[str, Field(min_length=1, max_length=4_000)]
    category: MemoryCategory = "fact"
    persona_name: Annotated[str | None, Field(default=None, max_length=120)] = None
    enabled: bool = True

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return _normalize_single_line(value, field_name="Memory content")

    @field_validator("persona_name")
    @classmethod
    def normalize_persona_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_single_line(value, field_name="Persona name")


class MemoryTransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["aster-memories"]
    version: Literal[1]
    memories: Annotated[list[MemoryTransferItem], Field(max_length=1_000)]


class MemorySuggestionResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    persona_id: UUID | None
    content: str
    category: MemoryCategory
    status: Literal["pending", "accepted", "rejected"]
    created_at: datetime
    resolved_at: datetime | None


class MemorySuggestionAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_id: UUID | None = None
    content: Annotated[str | None, Field(default=None, min_length=1, max_length=4_000)] = None
    category: MemoryCategory | None = None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_single_line(value, field_name="Memory content")


class KnowledgeCollectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(default="", max_length=500)] = ""
    enabled: bool = True
    default_enabled: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_single_line(value, field_name="Collection name")

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_default_state(self) -> "KnowledgeCollectionPayload":
        if self.default_enabled and not self.enabled:
            raise ValueError("A disabled collection cannot be enabled by default")
        return self


class KnowledgeCollectionCreate(KnowledgeCollectionPayload):
    pass


class KnowledgeCollectionUpdate(KnowledgeCollectionPayload):
    pass


class KnowledgeCollectionResponse(BaseModel):
    id: UUID
    name: str
    description: str
    enabled: bool
    default_enabled: bool
    document_count: int
    ready_document_count: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    collection_id: UUID
    collection_name: str
    filename: str
    media_type: str
    size_bytes: int
    content_sha256: str
    status: Literal["processing", "ready", "failed"]
    error_message: str | None
    chunk_count: int
    embedded_chunk_count: int
    embedding_model_id: UUID | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Annotated[str, Field(min_length=1, max_length=120)]

    @field_validator("filename", "media_type")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalize_single_line(value, field_name="Upload metadata")


class ConversationRetrievalSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_enabled: bool = True
    rag_enabled: bool = True
    collection_ids: Annotated[list[UUID], Field(max_length=128)] = []

    @field_validator("collection_ids")
    @classmethod
    def unique_collection_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Conversation collection IDs must be unique")
        return value


class ConversationRetrievalSettingsResponse(BaseModel):
    conversation_id: UUID
    memory_enabled: bool
    rag_enabled: bool
    collections: list[KnowledgeCollectionResponse]


class RetrievalSourceResponse(BaseModel):
    id: UUID
    kind: Literal["memory", "document"]
    rank: int
    score: float | None
    label: str
    content: str
    memory_id: UUID | None
    chunk_id: UUID | None


class RetrievalPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[str, Field(min_length=1, max_length=20_000)]

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Retrieval query cannot be empty")
        return value


class RetrievalPreviewResponse(BaseModel):
    sources: list[RetrievalSourceResponse]
    context: str
