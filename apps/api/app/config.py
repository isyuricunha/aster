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

    @field_validator("aster_encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("ASTER_ENCRYPTION_KEY must contain at least 32 characters")
        return value

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
