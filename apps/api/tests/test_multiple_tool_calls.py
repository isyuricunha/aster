from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences
from app.openai_compatible import ChatCompletionDelta, ToolCallDelta


async def configure_primary(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        endpoint = ModelEndpoint(
            name="Local",
            base_url="https://example.com/v1",
            enabled=True,
        )
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
        await session.commit()


async def create_automatic_tool(client) -> dict:
    server = await client.post(
        "/api/mcp-servers",
        json={
            "name": "Multiple calls MCP",
            "transport": "streamable_http",
            "url": "https://mcp.example.test/mcp",
            "headers": {},
            "enabled": True,
            "timeout_seconds": 30,
        },
    )
    assert server.status_code == 201
    server_id = server.json()["id"]
    assert (await client.post(f"/api/mcp-servers/{server_id}/sync")).status_code == 200
    tool = (await client.get("/api/mcp-tools")).json()[0]
    enabled = await client.put(
        f"/api/mcp-tools/{tool['id']}",
        json={
            "enabled": True,
            "default_enabled": True,
            "requires_confirmation": False,
        },
    )
    assert enabled.status_code == 200
    return enabled.json()


async def test_multiple_tool_calls_execute_before_generation_continues(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    tool = await create_automatic_tool(client)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    fake_client.chat_event_rounds = [
        [
            ChatCompletionDelta(
                tool_calls=(
                    ToolCallDelta(
                        index=0,
                        call_id="call-first",
                        name=tool["public_name"],
                        arguments='{"value":"first"}',
                    ),
                    ToolCallDelta(
                        index=1,
                        call_id="call-second",
                        name=tool["public_name"],
                        arguments='{"value":"second"}',
                    ),
                ),
                finish_reason="tool_calls",
            )
        ],
        [ChatCompletionDelta(content="Both tool calls completed.")],
    ]

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Run the tool twice."},
    )

    assert response.status_code == 200
    assert fake_client.mcp_client.calls == [
        ("echo", {"value": "first"}),
        ("echo", {"value": "second"}),
    ]
    assert response.text.count("event: tool_result") == 2

    conversation = (await client.get(f"/api/conversations/{conversation_id}")).json()
    call_message = conversation["messages"][1]
    tool_messages = [message for message in conversation["messages"] if message["role"] == "tool"]

    assert [call["id"] for call in call_message["tool_calls"]] == ["call-first", "call-second"]
    assert {message["tool_call_id"] for message in tool_messages} == {
        "call-first",
        "call-second",
    }
    assert [execution["status"] for execution in conversation["tool_executions"]] == [
        "completed",
        "completed",
    ]
    assert conversation["messages"][-1]["content"] == "Both tool calls completed."
