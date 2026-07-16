from app.security import SecretCipher


def test_secret_cipher_round_trip_does_not_expose_plaintext() -> None:
    cipher = SecretCipher("a-secure-test-key-that-is-long-enough")
    encrypted = cipher.encrypt("secret-api-key")

    assert encrypted != "secret-api-key"
    assert "secret-api-key" not in encrypted
    assert cipher.decrypt(encrypted) == "secret-api-key"
