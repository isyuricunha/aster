from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ModelCacheEntry,
    ModelEndpoint,
    ModelFallbackEntry,
    ModelPreferences,
    ModelProfile,
)
from app.openai_compatible import ModelEndpointError


async def create_models(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[ModelCacheEntry, ModelCacheEntry]:
    async with session_factory() as session:
        primary_endpoint = ModelEndpoint(
            name="Primary endpoint",
            base_url="https://primary.example/v1",
            enabled=True,
        )
        fallback_endpoint = ModelEndpoint(
            name="Fallback endpoint",
            base_url="https://fallback.example/v1",
            enabled=True,
        )
        session.add_all([primary_endpoint, fallback_endpoint])
        await session.flush()
        primary = ModelCacheEntry(
            endpoint_id=primary_endpoint.id,
            model_id="primary-model",
            is_manual=True,
            is_available=True,
        )
        fallback = ModelCacheEntry(
            endpoint_id=fallback_endpoint.id,
            model_id="fallback-model",
            is_manual=True,
            is_available=True,
        )
        session.add_all([primary, fallback])
        await session.flush()
        session.add(ModelPreferences(id=1, primary_model_id=primary.id))
        await session.commit()
        await session.refresh(primary)
        await session.refresh(fallback)
        return primary, fallback


async def test_model_profile_defaults_update_and_reset(api_client: tuple) -> None:
    client, _, session_factory = api_client
    primary, _ = await create_models(session_factory)

    defaults = await client.get(f"/api/model-profiles/{primary.id}")
    assert defaults.status_code == 200
    assert defaults.json()["temperature"] is None
    assert defaults.json()["token_parameter"] == "max_tokens"
    assert defaults.json()["supports_chat"] is True

    updated = await client.put(
        f"/api/model-profiles/{primary.id}",
        json={
            "display_name": "Primary profile",
            "context_window": 131072,
            "max_output_tokens": 8192,
            "token_parameter": "max_completion_tokens",
            "temperature": 0.4,
            "top_p": 0.9,
            "reasoning_effort": "high",
            "supports_chat": True,
            "supports_streaming": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Primary profile"
    assert updated.json()["max_output_tokens"] == 8192

    assert (await client.delete(f"/api/model-profiles/{primary.id}")).status_code == 204
    reset = (await client.get(f"/api/model-profiles/{primary.id}")).json()
    assert reset["display_name"] is None
    assert reset["max_output_tokens"] is None


async def test_model_routing_validates_and_preserves_order(api_client: tuple) -> None:
    client, _, session_factory = api_client
    primary, fallback = await create_models(session_factory)

    duplicate_primary = await client.put(
        "/api/model-routing",
        json={"fallback_model_ids": [str(primary.id)]},
    )
    assert duplicate_primary.status_code == 422

    saved = await client.put(
        "/api/model-routing",
        json={"fallback_model_ids": [str(fallback.id)]},
    )
    assert saved.status_code == 200
    assert [item["id"] for item in saved.json()["fallbacks"]] == [str(fallback.id)]

    loaded = await client.get("/api/model-routing")
    assert [item["model_id"] for item in loaded.json()["fallbacks"]] == ["fallback-model"]


async def test_chat_applies_profile_parameters(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    primary, _ = await create_models(session_factory)
    async with session_factory() as session:
        session.add(
            ModelProfile(
                model_id=primary.id,
                max_output_tokens=4096,
                token_parameter="max_completion_tokens",
                temperature=0.25,
                top_p=0.8,
                reasoning_effort="medium",
            )
        )
        await session.commit()

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Use the profile"},
    )

    assert response.status_code == 200
    assert fake_client.received_chat_model == "primary-model"
    assert fake_client.received_chat_options == {
        "temperature": 0.25,
        "top_p": 0.8,
        "max_output_tokens": 4096,
        "token_parameter": "max_completion_tokens",
        "reasoning_effort": "medium",
    }


async def test_chat_falls_back_before_first_delta(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    _, fallback = await create_models(session_factory)
    async with session_factory() as session:
        session.add(ModelFallbackEntry(model_id=fallback.id, position=0))
        await session.commit()

    fake_client.chat_errors_by_model["primary-model"] = ModelEndpointError(
        "connection_error",
        "Primary endpoint unavailable.",
    )
    fake_client.chat_chunks_by_model["fallback-model"] = ["Fallback answer"]

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Use fallback"},
    )

    assert response.status_code == 200
    assert "event: fallback" in response.text
    assert fake_client.chat_calls == ["primary-model", "primary-model", "fallback-model"]
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["messages"][-1]["content"] == "Fallback answer"
    assert detail["messages"][-1]["model_id"] == "fallback-model"


async def test_chat_does_not_fallback_for_authentication_failure(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    _, fallback = await create_models(session_factory)
    async with session_factory() as session:
        session.add(ModelFallbackEntry(model_id=fallback.id, position=0))
        await session.commit()

    fake_client.chat_errors_by_model["primary-model"] = ModelEndpointError(
        "authentication_failed",
        "The endpoint returned HTTP 401.",
        401,
    )

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Do not hide configuration errors"},
    )

    assert "event: fallback" not in response.text
    assert "event: error" in response.text
    assert fake_client.chat_calls == ["primary-model", "primary-model"]


async def test_chat_does_not_fallback_after_partial_output(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    _, fallback = await create_models(session_factory)
    async with session_factory() as session:
        session.add(ModelFallbackEntry(model_id=fallback.id, position=0))
        await session.commit()

    fake_client.chat_chunks_by_model["primary-model"] = ["Partial answer"]
    fake_client.chat_errors_after_chunks_by_model["primary-model"] = ModelEndpointError(
        "connection_error",
        "Primary endpoint disconnected.",
    )

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Keep one model per response"},
    )

    assert "event: fallback" not in response.text
    assert "event: error" in response.text
    assert fake_client.chat_calls == ["primary-model", "primary-model"]
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["messages"][-1]["content"] == "Partial answer"
    assert detail["messages"][-1]["status"] == "failed"
    assert detail["messages"][-1]["model_id"] == "primary-model"
