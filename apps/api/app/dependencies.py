from functools import lru_cache

from app.config import settings
from app.mcp_client import McpClient
from app.openai_compatible import OpenAICompatibleClient
from app.security import SecretCipher


@lru_cache
def get_secret_cipher() -> SecretCipher:
    return SecretCipher(settings.aster_encryption_key.get_secret_value())


def get_openai_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        timeout_seconds=settings.aster_endpoint_timeout_seconds,
        stream_timeout_seconds=settings.aster_stream_timeout_seconds,
    )


def get_mcp_client() -> McpClient:
    return McpClient()
