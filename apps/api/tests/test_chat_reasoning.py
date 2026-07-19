import json

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ModelCacheEntry,
    ModelEndpoint,
    ModelPreferences,
    Persona,
    PersonaPreferences,
)
from app.openai_compatible import ChatCompletionDelta, OpenAICompatibleClient


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


async def test_openai_compatible_stream_extracts_reasoning_content() -> None:
    events = [
        {
            "choices": [
                {
                    "delta": {"reasoning_content": "Inspecting "},
                    "finish_reason": None,
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {"reasoning_content": "the request."},
                    "finish_reason": None,
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {"content": "Final answer."},
                    "finish_reason": "stop",
                }
            ]
        },
    ]
    stream = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    stream += "data: [DONE]\n\n"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://models.example/v1/chat/completions"
        return httpx.Response(
            200,
            text=stream,
            headers={"Content-Type": "text/event-stream"},
        )

    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))
    deltas = [
        delta
        async for delta in client.stream_chat_completion_events(
            base_url="https://models.example/v1",
            api_key=None,
            model_id="chat-model",
            messages=[{"role": "user", "content": "Hello"}],
        )
    ]

    assert [delta.reasoning for delta in deltas] == [
        "Inspecting ",
        "the request.",
        "",
    ]
    assert [delta.content for delta in deltas] == ["", "", "Final answer."]


async def test_chat_persists_reasoning_but_excludes_it_from_provider_history(
    api_client: tuple,
) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    fake_client.chat_event_rounds = [
        [
            ChatCompletionDelta(reasoning="Inspecting "),
            ChatCompletionDelta(reasoning="the request."),
            ChatCompletionDelta(content="Final answer."),
        ],
        [ChatCompletionDelta(content="Second answer.")],
    ]
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    first_response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "First question"},
    )

    assert first_response.status_code == 200
    assert 'event: delta\ndata: {"content": "<reasoning>"}' in first_response.text
    assert 'event: delta\ndata: {"content": "</reasoning>\\n\\nFinal answer."}' in first_response.text
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["messages"][1]["content"] == (
        "<reasoning>Inspecting the request.</reasoning>\n\nFinal answer."
    )

    second_response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Second question"},
    )

    assert second_response.status_code == 200
    assert {"role": "assistant", "content": "Final answer."} in fake_client.received_chat_messages
    assert all("<reasoning>" not in str(message["content"]) for message in fake_client.received_chat_messages)
