from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IntegrationKind = Literal["smtp", "caldav", "webhook"]
TriggerType = Literal["once", "interval", "daily", "weekly", "webhook", "communication"]
RunStatus = Literal[
    "queued",
    "running",
    "delivering",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
]


class IntegrationConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: IntegrationKind
    enabled: bool = True
    config: dict[str, object] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class IntegrationConnectionUpdate(IntegrationConnectionCreate):
    preserve_credentials: bool = True


class IntegrationConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: IntegrationKind
    enabled: bool
    config: dict[str, object]
    credential_names: list[str]
    last_test_status: str | None
    last_test_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class IntegrationTestResponse(BaseModel):
    status: Literal["ok"]
    message: str


class AutomationDeliveryInput(BaseModel):
    integration_id: UUID
    channel: Literal["email", "calendar", "webhook"]
    enabled: bool = True
    config: dict[str, object] = Field(default_factory=dict)


class AutomationDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID
    integration_name: str
    channel: Literal["email", "calendar", "webhook"]
    enabled: bool
    config: dict[str, object]
    position: int


class AutomationWrite(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    instruction: str = Field(min_length=1, max_length=100_000)
    enabled: bool = True
    trigger_type: TriggerType
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    schedule: dict[str, object] = Field(default_factory=dict)
    model_id: UUID | None = None
    persona_id: UUID | None = None
    use_default_persona: bool = False
    notify_on_success: bool = True
    notify_on_failure: bool = True
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=60, ge=0, le=86_400)
    timeout_seconds: int = Field(default=300, ge=10, le=3_600)
    deliveries: list[AutomationDeliveryInput] = Field(default_factory=list, max_length=16)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("timezone")
    @classmethod
    def normalize_timezone(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_persona_choice(self) -> "AutomationWrite":
        if self.persona_id is not None and self.use_default_persona:
            raise ValueError("Choose a persona or the default persona, not both")
        return self


class AutomationCreate(AutomationWrite):
    pass


class AutomationUpdate(AutomationWrite):
    pass


class AutomationEnabledUpdate(BaseModel):
    enabled: bool


class AutomationResponse(BaseModel):
    id: UUID
    builtin_key: str | None
    state: dict[str, object]
    name: str
    description: str
    instruction: str
    enabled: bool
    trigger_type: TriggerType
    timezone: str
    schedule: dict[str, object]
    next_run_at: datetime | None
    model_id: UUID | None
    persona_id: UUID | None
    persona_name: str | None
    persona_description: str | None
    persona_instruction_role: str | None
    notify_on_success: bool
    notify_on_failure: bool
    max_attempts: int
    retry_delay_seconds: int
    timeout_seconds: int
    webhook_configured: bool
    webhook_token: str | None = None
    webhook_path: str | None = None
    deliveries: list[AutomationDeliveryResponse]
    last_enqueued_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def normalize_webhook_path(self) -> "AutomationResponse":
        self.webhook_path = (
            f"/api/webhooks/{self.id}" if self.webhook_configured else None
        )
        return self


class AutomationDeliveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    delivery_id: UUID | None
    integration_id: UUID | None
    channel: Literal["email", "calendar", "webhook"]
    status: Literal["running", "completed", "failed"]
    destination: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class AutomationRunResponse(BaseModel):
    id: UUID
    automation_id: UUID
    automation_name: str
    trigger_source: Literal[
        "schedule",
        "manual",
        "webhook",
        "communication",
        "retry",
    ]
    status: RunStatus
    scheduled_for: datetime
    available_at: datetime
    attempt: int
    max_attempts: int
    lease_owner: str | None
    lease_expires_at: datetime | None
    trigger_payload: dict[str, object]
    instruction_snapshot: str
    persona_name: str | None
    provider_model_id: str | None
    response: str | None
    error_code: str | None
    error_message: str | None
    attempt_history: list[dict[str, object]]
    deliveries: list[AutomationDeliveryAttemptResponse]
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    automation_id: UUID | None
    run_id: UUID | None
    level: Literal["info", "success", "error"]
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total: int


class WebhookAcceptedResponse(BaseModel):
    status: Literal["accepted", "duplicate"]
    run_id: UUID | None
