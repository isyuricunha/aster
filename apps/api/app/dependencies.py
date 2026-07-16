from functools import lru_cache

from app.config import settings
from app.openai_compatible import OpenAICompatibleClient
from app.security import SecretCipher


@lru_cache
def get_secret_cipher() -> SecretCipher:
    return SecretCipher(settings.aster_encryption_key.get_secret_value())


def get_openai_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient()
