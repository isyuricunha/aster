from functools import lru_cache

from app.communication_storage import CommunicationAttachmentStore
from app.config import settings
from app.image_provider import OpenAICompatibleImageClient
from app.image_storage import PrivateMediaStore
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


def get_image_client() -> OpenAICompatibleImageClient:
    return OpenAICompatibleImageClient(
        timeout_seconds=settings.aster_image_timeout_seconds,
        max_output_bytes=settings.aster_image_output_max_bytes,
        max_outputs=settings.aster_image_max_outputs,
    )


@lru_cache
def get_media_store() -> PrivateMediaStore:
    return PrivateMediaStore(settings.aster_media_root)


@lru_cache
def get_communication_store() -> CommunicationAttachmentStore:
    return CommunicationAttachmentStore(settings.aster_media_root)


def get_mcp_client() -> McpClient:
    return McpClient()
