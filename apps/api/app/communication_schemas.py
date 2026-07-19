from datetime import datetime
from ipaddress import ip_address
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CommunicationKind = Literal["imap", "discord"]
ThreadKind = Literal["email", "discord"]


def _normalize_imap_host(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    host = value.strip()
    if "://" in host or any(marker in host for marker in ("/", "\\", "?", "#", "@")):
        raise ValueError(
            "IMAP host must be a hostname or IP address without a URL scheme or path"
        )
    if ":" in host:
        candidate = host.removeprefix("[").removesuffix("]")
        try:
            ip_address(candidate)
        except ValueError as error:
            raise ValueError(
                "IMAP host must not include a port; use the separate port field"
            ) from error
        host = candidate
    return host


class CommunicationAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: CommunicationKind
    enabled: bool = True
    config: dict[str, object] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)
    poll_interval_seconds: int = Field(default=60, ge=10, le=86_400)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def normalize_imap_config(self) -> "CommunicationAccountCreate":
        if self.kind != "imap":
            return self
        host = _normalize_imap_host(self.config.get("host"))
        if host is not None:
            self.config = {**self.config, "host": host}
        return self


class CommunicationAccountUpdate(CommunicationAccountCreate):
    preserve_credentials: bool = True


class CommunicationAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: CommunicationKind
    enabled: bool
    config: dict[str, object]
    credential_names: list[str]
    external_identity: dict[str, object]
    poll_interval_seconds: int
    next_sync_at: datetime | None
    last_sync_status: str | None
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class CommunicationAccountTestResponse(BaseModel):
    status: Literal["ok"]
    message: str
    identity: dict[str, object]


class CommunicationSyncResponse(BaseModel):
    status: Literal["ok"]
    messages_added: int
    automations_enqueued: int


class CommunicationAttachmentResponse(BaseModel):
    id: UUID
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    content_path: str


class CommunicationMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    account_id: UUID
    external_message_id: str
    direction: Literal["inbound", "outbound"]
    source_id: str | None
    sender_name: str | None
    sender_address: str | None
    recipients: list[dict[str, str]]
    subject: str | None
    content_text: str
    content_html: str | None
    metadata: dict[str, object]
    is_read: bool
    sent_at: datetime
    received_at: datetime
    attachments: list[CommunicationAttachmentResponse]
    created_at: datetime
    updated_at: datetime


class CommunicationThreadResponse(BaseModel):
    id: UUID
    account_id: UUID
    account_name: str
    kind: ThreadKind
    external_thread_id: str
    title: str
    participants: list[dict[str, str]]
    metadata: dict[str, object]
    unread_count: int
    last_message_at: datetime
    message_count: int
    preview: str
    created_at: datetime
    updated_at: datetime


class CommunicationThreadDetail(CommunicationThreadResponse):
    messages: list[CommunicationMessageResponse]


class CommunicationReply(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)

    @field_validator("content")
    @classmethod
    def preserve_nonempty_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reply content cannot be empty")
        return value


class CommunicationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    account_id: UUID
    automation_id: UUID
    enabled: bool = True
    sender_pattern: str | None = Field(default=None, max_length=500)
    source_ids: list[str] = Field(default_factory=list, max_length=100)
    body_contains: str | None = Field(default=None, max_length=500)
    require_mention: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("sender_pattern", "body_contains")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("source_ids")
    @classmethod
    def normalize_source_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Source IDs must be unique")
        return normalized


class CommunicationRuleUpdate(CommunicationRuleCreate):
    pass


class CommunicationRuleResponse(BaseModel):
    id: UUID
    name: str
    account_id: UUID
    account_name: str
    automation_id: UUID
    automation_name: str
    enabled: bool
    sender_pattern: str | None
    source_ids: list[str]
    body_contains: str | None
    require_mention: bool
    created_at: datetime
    updated_at: datetime


class CommunicationThreadQuery(BaseModel):
    account_id: UUID | None = None
    kind: ThreadKind | None = None
    unread_only: bool = False
    query: str | None = Field(default=None, max_length=200)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)

    @model_validator(mode="after")
    def normalize_query(self) -> "CommunicationThreadQuery":
        if self.query is not None:
            self.query = self.query.strip() or None
        return self
