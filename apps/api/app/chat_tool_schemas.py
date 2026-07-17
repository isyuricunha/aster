import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas import ConversationPersonaImport, ConversationPersonaResponse
from app.tool_schemas import ToolExecutionResponse


class ToolCallFunction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=64)]
    arguments: Annotated[str, Field(max_length=100_000)]


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(min_length=1, max_length=256)]
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ToolAwareChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "tool"]
    content: str
    status: Literal["completed", "streaming", "failed", "stopped"]
    error_message: str | None
    model_id: str | None
    tool_calls: list[ToolCall] | None
    tool_call_id: str | None
    tool_name: str | None
    position: int
    created_at: datetime
    updated_at: datetime


class ToolAwareConversationResponse(BaseModel):
    id: UUID
    title: str
    persona: ConversationPersonaResponse | None
    messages: list[ToolAwareChatMessageResponse]
    tool_executions: list[ToolExecutionResponse]
    created_at: datetime
    updated_at: datetime


class ToolAwareConversationImportMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "tool"]
    content: Annotated[str, Field(default="", max_length=100_000)] = ""
    status: Literal["completed", "failed", "stopped"] = "completed"
    error_message: Annotated[str | None, Field(default=None, max_length=500)] = None
    model_id: Annotated[str | None, Field(default=None, max_length=512)] = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: Annotated[str | None, Field(default=None, max_length=256)] = None
    tool_name: Annotated[str | None, Field(default=None, max_length=256)] = None

    @field_validator("error_message", "model_id", "tool_call_id", "tool_name")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_role_metadata(self) -> "ToolAwareConversationImportMessage":
        if self.role == "user":
            if self.status != "completed":
                raise ValueError("Imported user messages must be completed")
            if any(
                value is not None
                for value in (
                    self.error_message,
                    self.model_id,
                    self.tool_calls,
                    self.tool_call_id,
                    self.tool_name,
                )
            ):
                raise ValueError("Imported user messages cannot contain assistant or tool metadata")
        elif self.role == "assistant":
            if self.tool_call_id is not None or self.tool_name is not None:
                raise ValueError("Imported assistant messages cannot contain tool-result metadata")
            if self.status == "completed" and not self.content and not self.tool_calls:
                raise ValueError("Completed assistant messages must contain content or tool calls")
        else:
            if self.tool_call_id is None or self.tool_name is None:
                raise ValueError("Imported tool messages require a call ID and tool name")
            if self.model_id is not None or self.tool_calls is not None:
                raise ValueError("Imported tool messages cannot contain model or tool-call metadata")
            if not self.content:
                raise ValueError("Imported tool messages cannot be empty")
        return self


class ToolAwareConversationImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["aster-conversation"]
    version: Literal[1, 2, 3]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    persona: ConversationPersonaImport | None = None
    messages: Annotated[list[ToolAwareConversationImportMessage], Field(max_length=2_000)]

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Conversation title cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_transfer(self) -> "ToolAwareConversationImportRequest":
        if self.version == 1 and self.persona is not None:
            raise ValueError("Version 1 conversation exports cannot contain a persona snapshot")
        if self.version < 3:
            for message in self.messages:
                if message.role == "tool" or any(
                    value is not None
                    for value in (message.tool_calls, message.tool_call_id, message.tool_name)
                ):
                    raise ValueError("Tool history requires conversation export version 3")
        total_characters = sum(len(message.content) for message in self.messages)
        total_characters += sum(
            len(json.dumps(call.model_dump(mode="json"), ensure_ascii=False))
            for message in self.messages
            for call in message.tool_calls or []
        )
        if self.persona is not None:
            total_characters += len(self.persona.instructions)
        if total_characters > 5_000_000:
            raise ValueError("Imported conversation content exceeds 5,000,000 characters")
        return self
