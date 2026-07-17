from uuid import UUID

from app.automation_models import IntegrationConnection
from app.config import settings
from app.integration_service import decrypt_credentials
from app.security import SecretCipher


async def test_partial_credential_update_preserves_unchanged_secrets(
    api_client: tuple,
) -> None:
    client, _, session_factory = api_client
    created = await client.post(
        "/api/integrations",
        json={
            "name": "Deployment webhook",
            "kind": "webhook",
            "enabled": True,
            "config": {
                "url": "https://example.com/hooks/aster",
                "auth_type": "none",
            },
            "credentials": {
                "Authorization": "Bearer original-token",
                "X-Signature": "original-signature",
            },
        },
    )
    assert created.status_code == 201, created.text
    integration_id = created.json()["id"]

    updated = await client.put(
        f"/api/integrations/{integration_id}",
        json={
            "name": "Deployment webhook",
            "kind": "webhook",
            "enabled": True,
            "config": {
                "url": "https://example.com/hooks/aster",
                "auth_type": "none",
            },
            "credentials": {"X-Signature": "rotated-signature"},
            "preserve_credentials": True,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["credential_names"] == ["Authorization", "X-Signature"]
    assert "original-token" not in updated.text
    assert "rotated-signature" not in updated.text

    cipher = SecretCipher(settings.aster_encryption_key.get_secret_value())
    async with session_factory() as session:
        integration = await session.get(
            IntegrationConnection,
            UUID(integration_id),
        )
        assert integration is not None
        assert decrypt_credentials(cipher, integration.encrypted_credentials) == {
            "Authorization": "Bearer original-token",
            "X-Signature": "rotated-signature",
        }

    cleared = await client.put(
        f"/api/integrations/{integration_id}",
        json={
            "name": "Deployment webhook",
            "kind": "webhook",
            "enabled": True,
            "config": {
                "url": "https://example.com/hooks/aster",
                "auth_type": "none",
            },
            "credentials": {},
            "preserve_credentials": False,
        },
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["credential_names"] == []

    async with session_factory() as session:
        integration = await session.get(
            IntegrationConnection,
            UUID(integration_id),
        )
        assert integration is not None
        assert integration.encrypted_credentials is None
