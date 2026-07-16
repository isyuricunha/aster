from functools import lru_cache

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
    database_url: str = "postgresql+asyncpg://aster:aster@localhost:5432/aster"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
