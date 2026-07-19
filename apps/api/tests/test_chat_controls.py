import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.chat_generation import next_delta_or_stop, recover_interrupted_streams
from app.chat_runtime import generation_registry
from app.models import (
    ChatMessage,
    Conversation,
    ModelCacheEntry,
    ModelEndpoint,
    ModelPreferences,
    Persona,
    PersonaPreferences,
)
from app.prompt_library import CHAT_SYSTEM_PROMPT


def persona_instruction() -> str:
    return (
        "[USER_DEFINED_PERSONA]\n"
        "The owner defined this persona for identity, tone, style, and response preferences.\n"
        "Name: Assistant\n\n"
        "Instructions:\n"
        "Be direct.\n"
        "[/USER_DEFINED_PERSONA]"
    )


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


async def test_edit_and_resend_replaces_the_conversation_tail(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "First draft"},
    )
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "This should disappear"},
    )
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    first_user_id = detail["messages"][0]["id"]

    fake_client.chat_chunks = ["Edited answer"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/{first_user_id}/edit-and-resend",
        json={"content": "Edited request"},
    )

    assert response.status_code == 200
    assert '"operation": "edit"' in response.text
    assert fake_client.received_chat_messages == [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "developer", "content": persona_instruction()},
        {"role": "user", "content": "Edited request"},
    ]
    updated = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert updated["title"] == "Edited answer"
    assert [message["content"] for message in updated["messages"]] == [
        "Edited request",
        "Edited answer",
    ]


async def test_regenerate_replaces_the_selected_assistant_and_later_messages(
    api_client: tuple,
) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "First"},
    )
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Later message"},
    )
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    first_assistant_id = detail["messages"][1]["id"]

    fake_client.chat_chunks = ["Regenerated"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/{first_assistant_id}/regenerate"
    )

    assert response.status_code == 200
    assert '"operation": "regenerate"' in response.text
    assert fake_client.received_chat_messages == [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "developer", "content": persona_instruction()},
        {"role": "user", "content": "First"},
    ]
    updated = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert [message["content"] for message in updated["messages"]] == [
        "First",
        "Regenerated",
    ]


async def test_parallel_generation_is_rejected_before_new_messages_are_created(
    api_client: tuple,
) -> None:
    client, _, session_factory = api_client
    await configure_primary(session_factory)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    async with session_factory() as session:
        session.add(
            ChatMessage(
                conversation_id=UUID(conversation_id),
                role="assistant",
                content="partial",
                status="streaming",
                model_id="chat-model",
                position=1,
            )
        )
        await session.commit()

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Do not add this"},
    )

    assert response.status_code == 409
    async with session_factory() as session:
        messages = list(await session.scalars(select(ChatMessage)))
    assert len(messages) == 1


async def test_stop_endpoint_signals_the_active_generation(api_client: tuple) -> None:
    client, _, session_factory = api_client
    async with session_factory() as session:
        conversation = Conversation(title="Stopping")
        session.add(conversation)
        await session.flush()
        message = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content="partial",
            status="streaming",
            model_id="chat-model",
            position=1,
        )
        session.add(message)
        await session.commit()
        message_id = message.id

    event = await generation_registry.register(message_id)
    try:
        response = await client.post(f"/api/messages/{message_id}/stop")
        assert response.status_code == 200
        assert response.json() == {"stopped": True, "message_id": str(message_id)}
        assert event.is_set()
    finally:
        await generation_registry.unregister(message_id)


async def test_stop_interrupts_a_waiting_upstream_iterator() -> None:
    async def slow_stream():
        await asyncio.sleep(60)
        yield "late"

    stop_event = asyncio.Event()
    pending = asyncio.create_task(next_delta_or_stop(slow_stream(), stop_event))
    await asyncio.sleep(0)
    stop_event.set()

    delta, stopped, finished = await pending
    assert delta is None
    assert stopped is True
    assert finished is False


async def test_restart_recovery_marks_streaming_messages_as_failed(api_client: tuple) -> None:
    _, _, session_factory = api_client
    async with session_factory() as session:
        conversation = Conversation(title="Interrupted")
        session.add(conversation)
        await session.flush()
        session.add(
            ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content="saved partial output",
                status="streaming",
                model_id="chat-model",
                position=1,
            )
        )
        await session.commit()

    async with session_factory() as session:
        assert await recover_interrupted_streams(session) == 1

    async with session_factory() as session:
        recovered = await session.scalar(select(ChatMessage))
        assert recovered is not None
        assert recovered.status == "failed"
        assert recovered.content == "saved partial output"
        assert recovered.error_message == "The response was interrupted before completion."
