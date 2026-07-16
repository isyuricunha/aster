from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Endpoint name cannot be empty")
    return normalized


def _normalize_base_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Base URL must be an absolute HTTP or HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("Base URL cannot contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Base URL cannot contain a query string or fragment")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


class EndpointBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    base_url: Annotated[str, Field(min_length=1, max_length=2048)]
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_name(value)

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return _normalize_base_url(value)


class EndpointCreate(EndpointBase):
    api_key: Annotated[str | None, Field(default=None, max_length=4096)] = None

    @field_validator("api_key")
    @classmethod
    def normalize_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EndpointUpdate(BaseModel):
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=120)] = None
    base_url: Annotated[str | None, Field(default=None, min_length=1, max_length=2048)] = None
    enabled: bool | None = None
    api_key: Annotated[str | None, Field(default=None, max_length=4096)] = None
    clear_api_key: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return _normalize_name(value) if value is not None else None

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str | None) -> str | None:
        return _normalize_base_url(value) if value is not None else None

    @field_validator("api_key")
    @classmethod
    def normalize_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_key_update(self) -> "EndpointUpdate":
        if self.clear_api_key and self.api_key:
            raise ValueError("api_key and clear_api_key cannot be used together")
        return self


class EndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    base_url: str
    enabled: bool
    has_api_key: bool
    cached_model_count: int
    last_sync_status: str | None
    last_sync_at: datetime | None
    last_successful_sync_at: datetime | None
    last_sync_error: str | None
    created_at: datetime
    updated_at: datetime


class ConnectionTestResponse(BaseModel):
    success: bool = True
    models_found: int
    message: str


class ModelSyncResponse(BaseModel):
    success: bool = True
    models_found: int
    synchronized_at: datetime


class ManualModelCreate(BaseModel):
    model_id: Annotated[str, Field(min_length=1, max_length=512)]

    @field_validator("model_id")
    @classmethod
    def normalize_model_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Model ID cannot be empty")
        return normalized


class CachedModelResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    endpoint_name: str
    model_id: str
    is_manual: bool
    is_available: bool
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModelPreferencesUpdate(BaseModel):
    primary_model_id: UUID | None = None
    utility_model_id: UUID | None = None
    image_model_id: UUID | None = None


class SelectedModelResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    endpoint_name: str
    model_id: str
    endpoint_enabled: bool
    is_available: bool


class ModelPreferencesResponse(BaseModel):
    primary: SelectedModelResponse | None
    utility: SelectedModelResponse | None
    image: SelectedModelResponse | None
    resolved_utility: SelectedModelResponse | None


class PersonaUpdate(BaseModel):
    name: Annotated[str, Field(default="", max_length=120)] = ""
    instructions: Annotated[str, Field(default="", max_length=100_000)] = ""
    enabled: bool = False
    instruction_role: Literal["developer", "system"] = "developer"

    @field_validator("name")
    @classmethod
    def normalize_persona_name(cls, value: str) -> str:
        return value.strip()


class PersonaResponse(BaseModel):
    name: str
    instructions: str
    enabled: bool
    instruction_role: str
    created_at: datetime
    updated_at: datetime


class CompositionPreviewRequest(BaseModel):
    user_message: Annotated[str, Field(min_length=1, max_length=100_000)]

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("User message cannot be empty")
        return value


class CanonicalMessageResponse(BaseModel):
    role: Literal["system", "developer", "user", "assistant", "tool"]
    source: Literal["platform", "persona", "conversation", "user", "assistant", "tool"]
    content: str


class CompositionPreviewResponse(BaseModel):
    messages: list[CanonicalMessageResponse]
