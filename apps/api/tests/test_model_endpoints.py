from sqlalchemy import select

from app.models import ModelEndpoint
from app.openai_compatible import ModelEndpointError
from app.security import SecretCipher


async def test_endpoint_sync_preferences_and_delete_flow(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    created = await client.post(
        "/api/model-endpoints",
        json={
            "name": "Local models",
            "base_url": "https://models.example/v1/",
            "api_key": "private-key",
        },
    )
    assert created.status_code == 201
    endpoint = created.json()
    assert endpoint["base_url"] == "https://models.example/v1"
    assert endpoint["has_api_key"] is True
    assert "api_key" not in endpoint
    assert "encrypted_api_key" not in endpoint

    async with session_factory() as session:
        stored = await session.scalar(select(ModelEndpoint))
        assert stored is not None
        assert stored.encrypted_api_key != "private-key"
        assert "private-key" not in stored.encrypted_api_key
        assert SecretCipher("tests-only-encryption-key-with-32-characters").decrypt(
            stored.encrypted_api_key
        ) == "private-key"

    tested = await client.post(f"/api/model-endpoints/{endpoint['id']}/test")
    assert tested.status_code == 200
    assert tested.json()["models_found"] == 2
    assert fake_client.received_api_key == "private-key"

    synchronized = await client.post(f"/api/model-endpoints/{endpoint['id']}/sync")
    assert synchronized.status_code == 200
    assert synchronized.json()["models_found"] == 2

    models = (await client.get("/api/models")).json()
    assert [model["model_id"] for model in models] == ["alpha-model", "beta-model"]

    preferences = await client.put(
        "/api/model-preferences",
        json={"primary_model_id": models[0]["id"]},
    )
    assert preferences.status_code == 200
    assert preferences.json()["primary"]["model_id"] == "alpha-model"
    assert preferences.json()["utility"] is None
    assert preferences.json()["resolved_utility"]["model_id"] == "alpha-model"
    assert preferences.json()["image"] is None

    deleted = await client.delete(f"/api/model-endpoints/{endpoint['id']}")
    assert deleted.status_code == 204
    preferences_after_delete = (await client.get("/api/model-preferences")).json()
    assert preferences_after_delete["primary"] is None
    assert preferences_after_delete["resolved_utility"] is None


async def test_failed_sync_keeps_cached_models(api_client: tuple) -> None:
    client, fake_client, _ = api_client
    endpoint = (
        await client.post(
            "/api/model-endpoints",
            json={"name": "Remote models", "base_url": "https://remote.example/v1"},
        )
    ).json()

    assert (await client.post(f"/api/model-endpoints/{endpoint['id']}/sync")).status_code == 200
    fake_client.error = ModelEndpointError("timeout", "The endpoint timed out.")

    failed = await client.post(f"/api/model-endpoints/{endpoint['id']}/sync")
    assert failed.status_code == 502
    assert failed.json()["detail"] == {
        "code": "timeout",
        "message": "The endpoint timed out.",
    }

    models = (await client.get("/api/models")).json()
    assert len(models) == 2
    assert all(model["is_available"] for model in models)

    endpoints = (await client.get("/api/model-endpoints")).json()
    assert endpoints[0]["last_sync_status"] == "failed"
    assert endpoints[0]["last_sync_error"] == "The endpoint timed out."


async def test_manual_model_is_kept_when_discovery_does_not_return_it(api_client: tuple) -> None:
    client, fake_client, _ = api_client
    endpoint = (
        await client.post(
            "/api/model-endpoints",
            json={"name": "Manual endpoint", "base_url": "http://localhost:9000/v1"},
        )
    ).json()

    manual = await client.post(
        f"/api/model-endpoints/{endpoint['id']}/models",
        json={"model_id": "manual-model"},
    )
    assert manual.status_code == 201

    fake_client.models = ["discovered-model"]
    assert (await client.post(f"/api/model-endpoints/{endpoint['id']}/sync")).status_code == 200

    models = (await client.get("/api/models")).json()
    assert {model["model_id"] for model in models} == {"manual-model", "discovered-model"}
    manual_after_sync = next(model for model in models if model["model_id"] == "manual-model")
    assert manual_after_sync["is_manual"] is True
    assert manual_after_sync["is_available"] is True
