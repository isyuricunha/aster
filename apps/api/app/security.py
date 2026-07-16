import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ASSOCIATED_DATA = b"aster:model-endpoint-api-key:v1"


class SecretCipher:
    def __init__(self, secret: str) -> None:
        self._cipher = AESGCM(hashlib.sha256(secret.encode("utf-8")).digest())

    def encrypt(self, value: str) -> str:
        nonce = os.urandom(12)
        encrypted = self._cipher.encrypt(nonce, value.encode("utf-8"), _ASSOCIATED_DATA)
        return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")

    def decrypt(self, value: str) -> str:
        payload = base64.urlsafe_b64decode(value.encode("ascii"))
        nonce, encrypted = payload[:12], payload[12:]
        return self._cipher.decrypt(nonce, encrypted, _ASSOCIATED_DATA).decode("utf-8")
