import pytest
from pydantic import ValidationError

from app.config import Settings

TEST_ENCRYPTION_KEY = "test-encryption-key-with-at-least-32-characters"


def test_database_url_uses_local_postgres_settings_when_empty() -> None:
    settings = Settings(
        aster_encryption_key=TEST_ENCRYPTION_KEY,
        database_url="",
        postgres_host="database",
        postgres_port=5433,
        postgres_db="aster db",
        postgres_user="aster user",
        postgres_password="p@ss/word",
    )

    assert settings.database_url == (
        "postgresql+asyncpg://aster%20user:p%40ss%2Fword@database:5433/aster%20db"
    )


def test_explicit_database_url_takes_precedence() -> None:
    external_url = "postgresql+asyncpg://external:password@database.example:5432/aster"
    settings = Settings(
        aster_encryption_key=TEST_ENCRYPTION_KEY,
        database_url=external_url,
        postgres_password="ignored",
    )

    assert settings.database_url == external_url


def test_runtime_timeout_settings_accept_positive_values() -> None:
    settings = Settings(
        aster_encryption_key=TEST_ENCRYPTION_KEY,
        aster_endpoint_timeout_seconds=45,
        aster_stream_timeout_seconds=300,
    )

    assert settings.aster_endpoint_timeout_seconds == 45
    assert settings.aster_stream_timeout_seconds == 300


@pytest.mark.parametrize(
    "field",
    ["aster_endpoint_timeout_seconds", "aster_stream_timeout_seconds"],
)
def test_runtime_timeout_settings_reject_non_positive_values(field: str) -> None:
    values = {
        "aster_encryption_key": TEST_ENCRYPTION_KEY,
        field: 0,
    }

    with pytest.raises(ValidationError):
        Settings(**values)
