from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

SecretMap = Annotated[dict[str, str], Field(max_length=64)]


def _normalize_server_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("MCP server name cannot be empty")
    return normalized


def _normalize_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("MCP URL must be an absolute HTTP or HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("MCP URL cannot contain embedded credentials")
    if parsed.fragment:
        raise ValueError("MCP URL cannot contain a fragment")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


def _normalize_secret_map(value: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_name, raw_value in value.items():
        name = raw_name.strip()
        if not name or len(name) > 256:
            raise ValueError("Secret names must contain between 1 and 256 characters")
        if any(character in name for character in "\r\n\0"):
            raise ValueError("Secret names cannot contain control characters")
        if len(raw_value) > 16_384:
            raise ValueError("Secret values cannot exceed 16,384 characters")
        normalized[name] = raw_value
    return normalized


class McpServerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120)]
    transport: Literal["streamable_http", "stdio"]
    url: Annotated[str | None, Field(default=None, max_length=2048)] = None
    command: Annotated[str | None, Field(default=None, max_length=1024)] = None
    arguments: Annotated[list[str], Field(default_factory=list, max_length=64)]
    headers: SecretMap = Field(default_factory=dict)
    environment: SecretMap = Field(default_factory=dict)
    enabled: bool = True
    timeout_seconds: Annotated[int, Field(default=30, ge=1, le=600)] = 30

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_server_name(value)

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str | None) -> str | None:
        return _normalize_http_url(value)

    @field_validator("command")
    @classmethod
    def normalize_command(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("arguments")
    @classmethod
    def validate_arguments(cls, value: list[str]) -> list[str]:
        if any(len(argument) > 4096 for argument in value):
            raise ValueError("MCP command arguments cannot exceed 4,096 characters")
        return value

    @field_validator("headers", "environment")
    @classmethod
    def normalize_secrets(cls, value: dict[str, str]) -> dict[str, str]:
        return _normalize_secret_map(value)

    @model_validator(mode="after")
    def validate_transport_configuration(self) -> "McpServerPayload":
        if self.transport == "streamable_http":
            if self.url is None:
                raise ValueError("Streamable HTTP MCP servers require a URL")
            if self.command is not None or self.arguments or self.environment:
                raise ValueError(
                    "Streamable HTTP MCP servers cannot define a command or environment"
                )
        else:
            if self.command is None:
                raise ValueError("Stdio MCP servers require a command")
            if self.url is not None or self.headers:
                raise ValueError("Stdio MCP servers cannot define a URL or HTTP headers")
        return self


class McpServerCreate(McpServerPayload):
    pass


class McpServerUpdate(McpServerPayload):
    preserve_secrets: bool = True


class McpServerResponse(BaseModel):
    id: UUID
    name: str
    transport: Literal["streamable_http", "stdio"]
    url: str | None
    command: str | None
    arguments: list[str]
    header_names: list[str]
    environment_names: list[str]
    enabled: bool
    timeout_seconds: int
    tool_count: int
    available_tool_count: int
    last_sync_status: Literal["succeeded", "failed"] | None
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class McpConnectionTestResponse(BaseModel):
    success: bool = True
    tools_found: int
    message: str


class McpSyncResponse(BaseModel):
    success: bool = True
    tools_found: int
    synchronized_at: datetime


class McpToolUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    default_enabled: bool
    requires_confirmation: bool

    @model_validator(mode="after")
    def validate_default(self) -> "McpToolUpdate":
        if self.default_enabled and not self.enabled:
            raise ValueError("A disabled tool cannot be enabled by default")
        return self


class McpToolResponse(BaseModel):
    id: UUID
    server_id: UUID
    server_name: str
    name: str
    public_name: str
    description: str
    input_schema: dict[str, object]
    enabled: bool
    default_enabled: bool
    requires_confirmation: bool
    is_available: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConversationToolSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_ids: Annotated[list[UUID], Field(max_length=256)]

    @field_validator("tool_ids")
    @classmethod
    def unique_tool_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Conversation tool IDs must be unique")
        return value


class ConversationToolSettingsResponse(BaseModel):
    conversation_id: UUID
    tools: list[McpToolResponse]


class ToolExecutionResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    tool_message_id: UUID | None
    tool_id: UUID | None
    tool_call_id: str
    tool_name: str
    arguments: dict[str, object]
    status: Literal["pending_confirmation", "running", "completed", "failed", "denied"]
    result: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
