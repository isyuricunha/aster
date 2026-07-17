import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ImageOutputFormat = Literal["png", "jpeg", "webp"]
ImageAttachmentType = Literal["input", "output"]
ImageOperationType = Literal["generation", "edit"]
ImageOperationStatus = Literal["running", "completed", "failed"]

_RESERVED_PROVIDER_PARAMETERS = {
    "background",
    "image",
    "input_fidelity",
    "mask",
    "model",
    "n",
    "output_format",
    "prompt",
    "quality",
    "response_format",
    "size",
    "stream",
}


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_provider_value(value: object, *, depth: int = 0) -> None:
    if depth > 3:
        raise ValueError("Provider parameters cannot be nested more than three levels")
    if value is None or isinstance(value, bool | int | float | str):
        return
    if isinstance(value, list):
        if len(value) > 32:
            raise ValueError("Provider parameter arrays cannot contain more than 32 items")
        for item in value:
            _validate_provider_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 32:
            raise ValueError("Provider parameter objects cannot contain more than 32 keys")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 64:
                raise ValueError("Provider parameter keys must contain 1 to 64 characters")
            _validate_provider_value(item, depth=depth + 1)
        return
    raise ValueError("Provider parameters contain an unsupported value")


def validate_provider_parameters(value: dict[str, object]) -> dict[str, object]:
    for key in value:
        if key.casefold() in _RESERVED_PROVIDER_PARAMETERS:
            raise ValueError(f"Provider parameter '{key}' is controlled by Aster")
    _validate_provider_value(value)
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) > 20_000:
        raise ValueError("Provider parameters exceed 20,000 characters")
    return value


class ImageModelProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supports_generation: bool = False
    supports_editing: bool = False
    supports_multiple_inputs: bool = False
    supports_masks: bool = False
    max_input_images: Annotated[int, Field(default=1, ge=1, le=16)] = 1
    default_size: Annotated[str | None, Field(default=None, max_length=32)] = None
    default_quality: Annotated[str | None, Field(default=None, max_length=32)] = None
    default_output_format: ImageOutputFormat = "png"
    default_background: Annotated[str | None, Field(default=None, max_length=32)] = None
    default_count: Annotated[int, Field(default=1, ge=1, le=4)] = 1
    default_input_fidelity: Annotated[str | None, Field(default=None, max_length=32)] = None
    provider_parameters: dict[str, object] = Field(default_factory=dict)

    @field_validator(
        "default_size",
        "default_quality",
        "default_background",
        "default_input_fidelity",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_optional(value)

    @field_validator("provider_parameters")
    @classmethod
    def validate_extra_parameters(cls, value: dict[str, object]) -> dict[str, object]:
        return validate_provider_parameters(value)

    @model_validator(mode="after")
    def validate_capabilities(self) -> "ImageModelProfileUpdate":
        if self.supports_multiple_inputs and not self.supports_editing:
            raise ValueError("Multiple image inputs require editing support")
        if self.supports_masks and not self.supports_editing:
            raise ValueError("Masks require editing support")
        if not self.supports_multiple_inputs and self.max_input_images != 1:
            raise ValueError("Models without multiple-input support must use max_input_images=1")
        return self


class ImageModelProfileResponse(ImageModelProfileUpdate):
    model_id: UUID
    endpoint_id: UUID
    endpoint_name: str
    provider_model_id: str
    endpoint_enabled: bool
    is_available: bool
    created_at: datetime | None
    updated_at: datetime | None


class MediaAssetResponse(BaseModel):
    id: UUID
    source_type: Literal["upload", "generated", "edited"]
    original_filename: str | None
    media_type: str
    size_bytes: int
    content_sha256: str
    width: int
    height: int
    content_url: str
    created_at: datetime
    updated_at: datetime


class MessageAttachmentResponse(MediaAssetResponse):
    attachment_type: ImageAttachmentType
    position: int


class ImageOperationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: Annotated[str, Field(min_length=1, max_length=20_000)]
    input_asset_ids: Annotated[list[UUID], Field(default_factory=list, max_length=16)]
    mask_asset_id: UUID | None = None
    model_id: UUID | None = None
    size: Annotated[str | None, Field(default=None, max_length=32)] = None
    quality: Annotated[str | None, Field(default=None, max_length=32)] = None
    output_format: ImageOutputFormat | None = None
    background: Annotated[str | None, Field(default=None, max_length=32)] = None
    count: Annotated[int | None, Field(default=None, ge=1, le=4)] = None
    input_fidelity: Annotated[str | None, Field(default=None, max_length=32)] = None
    provider_parameters: dict[str, object] = Field(default_factory=dict)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Image prompts cannot be empty")
        return normalized

    @field_validator("size", "quality", "background", "input_fidelity")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_optional(value)

    @field_validator("input_asset_ids")
    @classmethod
    def validate_unique_inputs(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Input images cannot contain duplicates")
        return value

    @field_validator("provider_parameters")
    @classmethod
    def validate_extra_parameters(cls, value: dict[str, object]) -> dict[str, object]:
        return validate_provider_parameters(value)

    @model_validator(mode="after")
    def validate_edit_inputs(self) -> "ImageOperationCreate":
        if self.mask_asset_id is not None and not self.input_asset_ids:
            raise ValueError("A mask requires at least one input image")
        if self.mask_asset_id in self.input_asset_ids:
            raise ValueError("The mask must be separate from the input images")
        return self


class ImageOperationResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    operation_type: ImageOperationType
    status: ImageOperationStatus
    model_cache_entry_id: UUID | None
    provider_model_id: str
    prompt: str
    revised_prompt: str | None
    parameters: dict[str, object]
    error_code: str | None
    error_message: str | None
    inputs: list[MessageAttachmentResponse]
    outputs: list[MessageAttachmentResponse]
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ImageGalleryResponse(BaseModel):
    items: list[ImageOperationResponse]
    total: int
    offset: int
    limit: int
