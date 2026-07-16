import pytest
from pydantic import ValidationError

from app.config import Settings


def test_runtime_timeout_settings_accept_positive_values() -> None:
    settings = Settings(
        aster_encryption_key="test-encryption-key-with-at-least-32-characters",
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
        "aster_encryption_key": "test-encryption-key-with-at-least-32-characters",
        field: 0,
    }

    with pytest.raises(ValidationError):
        Settings(**values)
