from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ChatMessage,
    ModelCacheEntry,
    ModelEndpoint,
    ModelPreferences,
    PersonaSettings,
)
from app.openai_compatible import ModelEndpointError


async def configure_primary(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        endpoint = ModelEndpoint(name="Local", base_url="https://example.com/v1", enabled=True)
        session.add(endpoint)
        await session.flush()
        model = ModelCacheEntry(
            endpoint_id=endpoint.id,
            model_id="chat-model",
            is_manual=True,
            is_available=True,
        )
        session.add(model)
        await session.flush()
        session.add(ModelPreferences(id=1, primary_model_id=model.id))
        session.add(
            PersonaSettings(
                id=1,
                name="Assistant",
                instructions="Be direct.",
                enabled=True,
                instruction_role="developer",
            )
        )
        await session.commit()


async def test_chat_persists_streamed_messages_and_uses_primary_model(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "  Keep my spacing  "},
    )

    assert response.status_code == 200
    assert "event: meta" in response.text
    assert 'event: delta\ndata: {"content": "Hello"}' in response.text
    assert "event: done" in response.text
    assert fake_client.received_chat_model == "chat-model"
    assert fake_client.received_chat_messages == [
        {"role": "developer", "content": "Your name is Assistant.\n\nBe direct."},
        {"role": "user", "content": "  Keep my spacing  "},
    ]

    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["title"] == "Keep my spacing"
    assert detail["messages"][0]["content"] == "  Keep my spacing  "
    assert detail["messages"][1]["content"] == "Hello from Aster"
    assert detail["messages"][1]["status"] == "completed"


async def test_chat_includes_completed_history_in_order(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "First"},
    )

    fake_client.chat_chunks = ["Second answer"]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Second"},
    )

    assert fake_client.received_chat_messages == [
        {"role": "developer", "content": "Your name is Assistant.\n\nBe direct."},
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Hello from Aster"},
        {"role": "user", "content": "Second"},
    ]


async def test_chat_failure_is_persisted_with_sanitized_error(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    fake_client.chat_error = ModelEndpointError(
        "upstream_error",
        "The endpoint returned HTTP 500.",
    )
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Hello"},
    )

    assert 'event: error\ndata: {"code": "upstream_error"' in response.text
    async with session_factory() as session:
        messages = list(
            await session.scalars(select(ChatMessage).order_by(ChatMessage.position.asc()))
        )
    assert messages[-1].status == "failed"
    assert messages[-1].error_message == "The endpoint returned HTTP 500."


async def test_chat_requires_primary_model_before_persisting_messages(api_client: tuple) -> None:
    client, _, session_factory = api_client
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Hello"},
    )

    assert response.status_code == 409
    async with session_factory() as session:
        assert list(await session.scalars(select(ChatMessage))) == []


async def test_conversation_crud(api_client: tuple) -> None:
    client, _, _ = api_client
    created = await client.post("/api/conversations", json={"title": "  First   chat "})
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "First chat"

    renamed = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "Renamed"},
    )
    assert renamed.json()["title"] == "Renamed"
    assert (await client.get("/api/conversations")).json()[0]["message_count"] == 0

    assert (await client.delete(f"/api/conversations/{conversation_id}")).status_code == 204
    assert (await client.get(f"/api/conversations/{conversation_id}")).status_code == 404
