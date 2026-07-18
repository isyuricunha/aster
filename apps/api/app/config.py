from functools import lru_cache
from urllib.parse import quote

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Aster API"
    app_environment: str = "development"
    database_url: str = ""
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "aster"
    postgres_user: str = "aster"
    postgres_password: SecretStr = SecretStr("aster")
    aster_encryption_key: SecretStr
    aster_cors_origins: str = "http://localhost:3000"
    aster_endpoint_timeout_seconds: float = Field(default=30.0, gt=0)
    aster_stream_timeout_seconds: float = Field(default=120.0, gt=0)
    aster_session_cookie_name: str = "aster_session"
    aster_session_secure: bool = False
    aster_session_absolute_days: int = Field(default=30, ge=1, le=365)
    aster_session_idle_hours: int = Field(default=168, ge=1, le=8760)
    aster_session_touch_seconds: int = Field(default=300, ge=30, le=3600)
    aster_login_attempts: int = Field(default=5, ge=1, le=100)
    aster_login_window_seconds: int = Field(default=300, ge=30, le=86400)
    aster_mcp_stdio_enabled: bool = False
    aster_mcp_timeout_seconds: float = Field(default=30.0, gt=0, le=600)
    aster_tool_max_rounds: int = Field(default=8, ge=1, le=32)
    aster_tool_argument_max_characters: int = Field(default=100_000, ge=1_000, le=1_000_000)
    aster_tool_result_max_characters: int = Field(default=100_000, ge=1_000, le=1_000_000)
    aster_memory_max_items: int = Field(default=12, ge=1, le=100)
    aster_memory_suggestion_max_items: int = Field(default=8, ge=1, le=32)
    aster_rag_max_sources: int = Field(default=8, ge=1, le=32)
    aster_rag_context_max_characters: int = Field(default=24_000, ge=2_000, le=200_000)
    aster_rag_candidate_limit: int = Field(default=2_000, ge=100, le=20_000)
    aster_document_max_bytes: int = Field(default=5_000_000, ge=10_000, le=100_000_000)
    aster_document_max_characters: int = Field(
        default=2_000_000, ge=10_000, le=20_000_000
    )
    aster_document_chunk_characters: int = Field(default=1_600, ge=400, le=8_000)
    aster_document_chunk_overlap: int = Field(default=200, ge=0, le=2_000)
    aster_document_max_chunks: int = Field(default=2_000, ge=10, le=20_000)
    aster_embedding_batch_size: int = Field(default=64, ge=1, le=256)
    aster_media_root: str = "/var/lib/aster/media"
    aster_image_timeout_seconds: float = Field(default=300.0, gt=0, le=1_800)
    aster_image_upload_max_bytes: int = Field(
        default=20_000_000, ge=100_000, le=200_000_000
    )
    aster_image_output_max_bytes: int = Field(
        default=25_000_000, ge=100_000, le=200_000_000
    )
    aster_image_max_pixels: int = Field(default=40_000_000, ge=1_000_000, le=200_000_000)
    aster_image_max_inputs: int = Field(default=8, ge=1, le=16)
    aster_image_max_outputs: int = Field(default=4, ge=1, le=8)
    aster_automation_poll_seconds: float = Field(default=2.0, ge=0.5, le=60)
    aster_automation_lease_seconds: int = Field(default=120, ge=30, le=3_600)
    aster_automation_heartbeat_seconds: int = Field(default=30, ge=5, le=1_200)
    aster_automation_scheduler_batch_size: int = Field(default=25, ge=1, le=500)
    aster_automation_output_max_characters: int = Field(
        default=100_000, ge=1_000, le=1_000_000
    )
    aster_integration_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    aster_webhook_max_bytes: int = Field(default=1_000_000, ge=1_000, le=20_000_000)
    aster_communication_lease_seconds: int = Field(default=180, ge=30, le=3_600)
    aster_communication_message_max_characters: int = Field(
        default=200_000, ge=1_000, le=2_000_000
    )
    aster_communication_attachment_max_bytes: int = Field(
        default=15_000_000, ge=10_000, le=200_000_000
    )
    aster_communication_max_attachments: int = Field(default=16, ge=0, le=100)
    aster_agent_lease_seconds: int = Field(default=180, ge=30, le=3_600)
    aster_agent_heartbeat_seconds: int = Field(default=45, ge=5, le=1_200)
    aster_agent_scheduler_batch_size: int = Field(default=25, ge=1, le=500)
    aster_agent_dispatch_batch_size: int = Field(default=100, ge=1, le=2_000)
    aster_agent_output_max_characters: int = Field(
        default=100_000, ge=1_000, le=1_000_000
    )
    aster_agent_history_max_characters: int = Field(
        default=50_000, ge=2_000, le=500_000
    )
    aster_agent_retrieval_max_characters: int = Field(
        default=24_000, ge=2_000, le=200_000
    )
    aster_agent_loop_repeat_limit: int = Field(default=3, ge=1, le=20)

    @field_validator("aster_encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("ASTER_ENCRYPTION_KEY must contain at least 32 characters")
        return value

    @field_validator("aster_session_cookie_name")
    @classmethod
    def validate_cookie_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ASTER_SESSION_COOKIE_NAME cannot be empty")
        return normalized

    @field_validator("aster_media_root")
    @classmethod
    def validate_media_root(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ASTER_MEDIA_ROOT cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_runtime_limits(self) -> "Settings":
        if self.aster_document_chunk_overlap >= self.aster_document_chunk_characters:
            raise ValueError(
                "ASTER_DOCUMENT_CHUNK_OVERLAP must be smaller than "
                "ASTER_DOCUMENT_CHUNK_CHARACTERS"
            )
        if self.aster_automation_heartbeat_seconds * 2 >= self.aster_automation_lease_seconds:
            raise ValueError(
                "ASTER_AUTOMATION_HEARTBEAT_SECONDS must be less than half of "
                "ASTER_AUTOMATION_LEASE_SECONDS"
            )
        if self.aster_agent_heartbeat_seconds * 2 >= self.aster_agent_lease_seconds:
            raise ValueError(
                "ASTER_AGENT_HEARTBEAT_SECONDS must be less than half of "
                "ASTER_AGENT_LEASE_SECONDS"
            )
        return self

    @model_validator(mode="after")
    def resolve_database_url(self) -> "Settings":
        if self.database_url.strip():
            return self
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        database = quote(self.postgres_db, safe="")
        self.database_url = (
            f"postgresql+asyncpg://{user}:{password}@"
            f"{self.postgres_host}:{self.postgres_port}/{database}"
        )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.aster_cors_origins.split(",") if origin.strip()]

    @property
    def production(self) -> bool:
        return self.app_environment.casefold() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
