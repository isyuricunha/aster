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


async def create_confirmation_tool(client) -> dict:
    server = (
        await client.post(
            "/api/mcp-servers",
            json={
                "name": "Invariant MCP",
                "transport": "streamable_http",
                "url": "https://mcp.example.test/mcp",
                "headers": {},
                "enabled": True,
                "timeout_seconds": 30,
            },
        )
    ).json()
    assert (await client.post(f"/api/mcp-servers/{server['id']}/sync")).status_code == 200
    tool = (await client.get("/api/mcp-tools")).json()[0]
    updated = await client.put(
        f"/api/mcp-tools/{tool['id']}",
        json={
            "enabled": True,
            "default_enabled": True,
            "requires_confirmation": True,
        },
    )
    assert updated.status_code == 200
    return updated.json()


async def test_pending_confirmation_blocks_new_branches_and_scope_changes(
    api_client: tuple,
) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    tool = await create_confirmation_tool(client)
    conversation = (await client.post("/api/conversations", json={})).json()

    fake_client.chat_event_rounds = [
        [
            ChatCompletionDelta(
                tool_calls=(
                    ToolCallDelta(
                        index=0,
                        call_id="pending-call",
                        name=tool["public_name"],
                        arguments='{"value":"wait"}',
                    ),
                ),
                finish_reason="tool_calls",
            )
        ]
    ]
    initial = await client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "Request approval."},
    )
    assert initial.status_code == 200
    assert "event: confirmation_required" in initial.text

    blocked_send = await client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "Do not create another branch."},
    )
    blocked_scope = await client.put(
        f"/api/conversations/{conversation['id']}/tools",
        json={"tool_ids": []},
    )
    blocked_persona = await client.patch(
        f"/api/conversations/{conversation['id']}",
        json={"persona_id": None},
    )

    assert blocked_send.status_code == 409
    assert blocked_scope.status_code == 409
    assert blocked_persona.status_code == 409


async def test_switching_transport_clears_incompatible_secrets(api_client: tuple) -> None:
    client, _, _ = api_client
    created = await client.post(
        "/api/mcp-servers",
        json={
            "name": "Transport MCP",
            "transport": "streamable_http",
            "url": "https://mcp.example.test/mcp",
            "headers": {"Authorization": "Bearer secret"},
            "enabled": True,
            "timeout_seconds": 30,
        },
    )
    assert created.status_code == 201
    server_id = created.json()["id"]

    switched = await client.put(
        f"/api/mcp-servers/{server_id}",
        json={
            "name": "Transport MCP",
            "transport": "stdio",
            "url": None,
            "command": "/usr/bin/python3",
            "arguments": ["server.py"],
            "headers": {},
            "environment": {"API_TOKEN": "new-secret"},
            "enabled": True,
            "timeout_seconds": 30,
            "preserve_secrets": True,
        },
    )

    assert switched.status_code == 200
    payload = switched.json()
    assert payload["header_names"] == []
    assert payload["environment_names"] == ["API_TOKEN"]
