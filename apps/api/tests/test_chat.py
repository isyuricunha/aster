from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ChatMessage,
    ModelCacheEntry,
    ModelEndpoint,
    ModelPreferences,
    Persona,
    PersonaPreferences,
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
        persona = Persona(
            name="Assistant",
            description="Test persona",
            instructions="Be direct.",
            enabled=True,
            instruction_role="developer",
        )
        session.add_all([model, persona])
        await session.flush()
        session.add(ModelPreferences(id=1, primary_model_id=model.id))
        session.add(PersonaPreferences(id=1, default_persona_id=persona.id))
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
    assert detail["persona"]["name"] == "Assistant"
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


async def test_conversation_import_preserves_content_and_order(api_client: tuple) -> None:
    client, _, _ = api_client
    response = await client.post(
        "/api/conversations/import",
        json={
            "format": "aster-conversation",
            "version": 1,
            "title": "  Imported   chat ",
            "messages": [
                {
                    "role": "user",
                    "content": "Show me `code`.",
                    "status": "completed",
                    "error_message": None,
                    "model_id": None,
                },
                {
                    "role": "assistant",
                    "content": "```python\nprint('hello')\n```",
                    "status": "stopped",
                    "error_message": None,
                    "model_id": "chat-model",
                },
            ],
        },
    )

    assert response.status_code == 201
    detail = response.json()
    assert detail["title"] == "Imported chat"
    assert detail["persona"] is None
    assert [message["position"] for message in detail["messages"]] == [0, 1]
    assert detail["messages"][0]["content"] == "Show me `code`."
    assert detail["messages"][1]["status"] == "stopped"
    assert detail["messages"][1]["model_id"] == "chat-model"

    invalid = await client.post(
        "/api/conversations/import",
        json={
            "format": "aster-conversation",
            "version": 1,
            "title": "Invalid",
            "messages": [
                {
                    "role": "assistant",
                    "content": "Partial",
                    "status": "streaming",
                }
            ],
        },
    )
    assert invalid.status_code == 422


async def test_conversation_search_matches_titles_and_message_content(api_client: tuple) -> None:
    client, _, _ = api_client
    title_match = await client.post(
        "/api/conversations/import",
        json={
            "format": "aster-conversation",
            "version": 1,
            "title": "Alpha planning",
            "messages": [],
        },
    )
    content_match = await client.post(
        "/api/conversations/import",
        json={
            "format": "aster-conversation",
            "version": 1,
            "title": "Other topic",
            "messages": [
                {
                    "role": "assistant",
                    "content": "The hidden needle is here.",
                    "status": "completed",
                    "model_id": "chat-model",
                }
            ],
        },
    )
    await client.post(
        "/api/conversations/import",
        json={
            "format": "aster-conversation",
            "version": 1,
            "title": "Unrelated",
            "messages": [],
        },
    )

    title_results = (await client.get("/api/conversations", params={"query": "ALPHA"})).json()
    assert [item["id"] for item in title_results] == [title_match.json()["id"]]

    content_results = (await client.get("/api/conversations", params={"query": "needle"})).json()
    assert [item["id"] for item in content_results] == [content_match.json()["id"]]

    all_results = (await client.get("/api/conversations", params={"query": "  "})).json()
    assert len(all_results) == 3
