from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.mcp_client import McpClientError
from app.models import McpServer, ModelCacheEntry, ModelEndpoint, ModelPreferences
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


async def create_and_sync_server(client, *, secret: str = "test-secret") -> tuple[str, dict]:
    response = await client.post(
        "/api/mcp-servers",
        json={
            "name": "Test MCP",
            "transport": "streamable_http",
            "url": "https://mcp.example.test/mcp",
            "headers": {"Authorization": f"Bearer {secret}"},
            "enabled": True,
            "timeout_seconds": 15,
        },
    )
    assert response.status_code == 201
    server = response.json()
    sync = await client.post(f"/api/mcp-servers/{server['id']}/sync")
    assert sync.status_code == 200
    tools = (await client.get("/api/mcp-tools")).json()
    assert len(tools) == 1
    return server["id"], tools[0]


async def enable_tool(
    client,
    tool: dict,
    *,
    confirmation: bool,
    default_enabled: bool = True,
) -> dict:
    response = await client.put(
        f"/api/mcp-tools/{tool['id']}",
        json={
            "enabled": True,
            "default_enabled": default_enabled,
            "requires_confirmation": confirmation,
        },
    )
    assert response.status_code == 200
    return response.json()


def tool_call_event(public_name: str, call_id: str = "call-1") -> ChatCompletionDelta:
    return ChatCompletionDelta(
        tool_calls=(
            ToolCallDelta(
                index=0,
                call_id=call_id,
                name=public_name,
                arguments='{"value":"hello"}',
            ),
        ),
        finish_reason="tool_calls",
    )


async def test_mcp_server_secrets_are_encrypted_and_not_returned(api_client: tuple) -> None:
    client, _, session_factory = api_client
    secret = "do-not-return-this-value"

    server_id, _ = await create_and_sync_server(client, secret=secret)
    payload = (await client.get(f"/api/mcp-servers/{server_id}")).json()

    assert payload["header_names"] == ["Authorization"]
    assert secret not in str(payload)
    async with session_factory() as session:
        server = await session.get(McpServer, server_id)
        assert server is not None
        assert server.encrypted_headers is not None
        assert secret not in server.encrypted_headers


async def test_discovered_tools_start_disabled_and_require_confirmation(api_client: tuple) -> None:
    client, _, _ = api_client

    _, tool = await create_and_sync_server(client)

    assert tool["enabled"] is False
    assert tool["default_enabled"] is False
    assert tool["requires_confirmation"] is True
    assert tool["is_available"] is True
    assert tool["public_name"].startswith("mcp_")


async def test_automatic_tool_call_executes_and_continues_the_model(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    _, tool = await create_and_sync_server(client)
    tool = await enable_tool(client, tool, confirmation=False)
    conversation = (await client.post("/api/conversations", json={})).json()
    scope = (await client.get(f"/api/conversations/{conversation['id']}/tools")).json()
    assert [item["id"] for item in scope["tools"]] == [tool["id"]]

    fake_client.chat_event_rounds = [
        [tool_call_event(tool["public_name"])],
        [ChatCompletionDelta(content="The tool completed.")],
    ]
    response = await client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "Use the echo tool."},
    )

    assert response.status_code == 200
    assert "event: tool_calls" in response.text
    assert "event: tool_result" in response.text
    assert "event: assistant_started" in response.text
    assert fake_client.mcp_client.calls == [("echo", {"value": "hello"})]
    assert len(fake_client.received_chat_tools) == 1

    detail = (await client.get(f"/api/conversations/{conversation['id']}")).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
        "tool",
        "assistant",
    ]
    assert detail["messages"][1]["tool_calls"][0]["function"]["name"] == tool["public_name"]
    assert detail["messages"][2]["tool_name"] == "echo"
    assert detail["messages"][3]["content"] == "The tool completed."
    assert detail["tool_executions"][0]["status"] == "completed"
    assert any(
        message.get("role") == "tool" and "UNTRUSTED_TOOL_RESULT" in message["content"]
        for message in fake_client.received_chat_messages
    )


async def test_confirmation_can_be_approved_and_resume_generation(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    _, tool = await create_and_sync_server(client)
    tool = await enable_tool(client, tool, confirmation=True)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    fake_client.chat_event_rounds = [[tool_call_event(tool["public_name"])]]
    initial = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Ask before using the tool."},
    )
    assert "event: confirmation_required" in initial.text
    assert fake_client.mcp_client.calls == []

    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    execution = detail["tool_executions"][0]
    assert execution["status"] == "pending_confirmation"

    fake_client.chat_event_rounds = [[ChatCompletionDelta(content="Approved result used.")]]
    approved = await client.post(f"/api/tool-executions/{execution['id']}/approve")

    assert approved.status_code == 200
    assert "event: tool_result" in approved.text
    assert "event: assistant_started" in approved.text
    assert fake_client.mcp_client.calls == [("echo", {"value": "hello"})]
    refreshed = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert refreshed["tool_executions"][0]["status"] == "completed"
    assert refreshed["messages"][-1]["content"] == "Approved result used."


async def test_confirmation_can_be_denied_and_resume_generation(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    _, tool = await create_and_sync_server(client)
    tool = await enable_tool(client, tool, confirmation=True)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    fake_client.chat_event_rounds = [[tool_call_event(tool["public_name"])]]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Request a tool call."},
    )
    execution = (
        await client.get(f"/api/conversations/{conversation_id}/tool-executions")
    ).json()[0]

    fake_client.chat_event_rounds = [[ChatCompletionDelta(content="I respected the denial.")]]
    denied = await client.post(f"/api/tool-executions/{execution['id']}/deny")

    assert denied.status_code == 200
    assert fake_client.mcp_client.calls == []
    refreshed = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert refreshed["tool_executions"][0]["status"] == "denied"
    tool_message = next(message for message in refreshed["messages"] if message["role"] == "tool")
    assert tool_message["content"] == "The owner denied this tool call."
    assert refreshed["messages"][-1]["content"] == "I respected the denial."


async def test_unknown_tool_call_is_recorded_as_a_failure(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    _, tool = await create_and_sync_server(client)
    await enable_tool(client, tool, confirmation=False)
    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]

    fake_client.chat_event_rounds = [
        [tool_call_event("mcp_unknown_tool")],
        [ChatCompletionDelta(content="The unavailable tool could not run.")],
    ]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Try an unavailable tool."},
    )

    assert response.status_code == 200
    assert fake_client.mcp_client.calls == []
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["tool_executions"][0]["status"] == "failed"
    assert "not enabled" in detail["tool_executions"][0]["error_message"]
    assert detail["messages"][-1]["content"] == "The unavailable tool could not run."


async def test_stdio_connection_reports_runtime_policy(api_client: tuple) -> None:
    client, fake_client, _ = api_client
    response = await client.post(
        "/api/mcp-servers",
        json={
            "name": "Local stdio",
            "transport": "stdio",
            "command": "python",
            "arguments": ["server.py"],
            "environment": {"TOKEN": "secret"},
            "enabled": True,
            "timeout_seconds": 30,
        },
    )
    assert response.status_code == 201
    fake_client.mcp_client.list_error = McpClientError(
        "stdio_disabled",
        "Stdio MCP servers are disabled by the Aster runtime configuration.",
    )

    tested = await client.post(f"/api/mcp-servers/{response.json()['id']}/test")

    assert tested.status_code == 422
    assert tested.json()["detail"]["code"] == "stdio_disabled"


async def test_version_three_import_preserves_tool_history(api_client: tuple) -> None:
    client, _, _ = api_client
    payload = {
        "format": "aster-conversation",
        "version": 3,
        "title": "Imported tool history",
        "messages": [
            {"role": "user", "content": "Use a tool."},
            {
                "role": "assistant",
                "content": "",
                "model_id": "chat-model",
                "tool_calls": [
                    {
                        "id": "call-imported",
                        "type": "function",
                        "function": {
                            "name": "mcp_imported_echo",
                            "arguments": '{"value":"portable"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": "portable",
                "tool_call_id": "call-imported",
                "tool_name": "echo",
            },
            {"role": "assistant", "content": "The imported result was portable."},
        ],
    }

    response = await client.post("/api/conversations/import", json=payload)

    assert response.status_code == 201
    messages = response.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "tool", "assistant"]
    assert messages[1]["tool_calls"][0]["id"] == "call-imported"
    assert messages[2]["tool_call_id"] == "call-imported"
