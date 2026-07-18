from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TokenParameter = Literal["none", "max_tokens", "max_completion_tokens"]
ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]
InstructionRole = Literal["system", "developer"]


class ModelProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Annotated[str | None, Field(default=None, max_length=120)] = None
    context_window: Annotated[int | None, Field(default=None, ge=1, le=10_000_000)] = None
    max_output_tokens: Annotated[int | None, Field(default=None, ge=1, le=1_000_000)] = None
    token_parameter: TokenParameter = "max_tokens"
    instruction_role: InstructionRole = "system"
    temperature: Annotated[float | None, Field(default=None, ge=0, le=2)] = None
    top_p: Annotated[float | None, Field(default=None, gt=0, le=1)] = None
    reasoning_effort: ReasoningEffort | None = None
    supports_chat: bool = True
    supports_streaming: bool = True

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_chat_streaming(self) -> "ModelProfileUpdate":
        if self.supports_streaming and not self.supports_chat:
            raise ValueError("Streaming support requires chat support")
        if self.token_parameter == "none" and self.max_output_tokens is not None:
            raise ValueError("max_output_tokens requires a token parameter")
        return self


class ModelProfileResponse(BaseModel):
    model_id: UUID
    endpoint_id: UUID
    endpoint_name: str
    provider_model_id: str
    display_name: str | None
    context_window: int | None
    max_output_tokens: int | None
    token_parameter: TokenParameter
    instruction_role: InstructionRole
    temperature: float | None
    top_p: float | None
    reasoning_effort: ReasoningEffort | None
    supports_chat: bool
    supports_streaming: bool
    endpoint_enabled: bool
    is_available: bool
    created_at: datetime | None
    updated_at: datetime | None


class FallbackModelResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    endpoint_name: str
    model_id: str
    display_name: str | None
    endpoint_enabled: bool
    is_available: bool
    supports_chat: bool
    supports_streaming: bool


class ModelRoutingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fallback_model_ids: Annotated[list[UUID], Field(default_factory=list, max_length=20)]

    @field_validator("fallback_model_ids")
    @classmethod
    def validate_unique_models(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Fallback models cannot contain duplicates")
        return value


class ModelRoutingResponse(BaseModel):
    fallbacks: list[FallbackModelResponse]
