from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_execution import execute_agent_run
from app.agent_models import AgentRun
from app.agent_queue import claim_next_agent_run
from app.agent_run_scope_models import AgentRunToolScope
from app.config import settings
from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences
from app.openai_compatible import ChatCompletionDelta, ToolCallDelta
from app.security import SecretCipher


async def configure_primary(
    session_factory: async_sessionmaker[AsyncSession],
) -> ModelCacheEntry:
    async with session_factory() as session:
        endpoint = ModelEndpoint(
            name="Agent provider",
            base_url="https://example.com/v1",
            enabled=True,
        )
        session.add(endpoint)
        await session.flush()
        model = ModelCacheEntry(
            endpoint_id=endpoint.id,
            model_id="agent-model",
            is_manual=True,
            is_available=True,
        )
        session.add(model)
        await session.flush()
        session.add(ModelPreferences(id=1, primary_model_id=model.id))
        await session.commit()
        return model


def agent_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Project operator",
        "description": "A bounded project agent.",
        "goal": "Inspect the current state and return a concise result.",
        "enabled": True,
        "paused": False,
        "trigger_type": "manual",
        "timezone": "UTC",
        "schedule": {},
        "model_id": None,
        "persona_id": None,
        "use_default_persona": False,
        "memory_enabled": False,
        "rag_enabled": False,
        "max_steps": 12,
        "max_model_calls": 12,
        "max_tool_calls": 20,
        "max_runtime_seconds": 900,
        "max_estimated_tokens": 100000,
        "max_estimated_cost_microusd": None,
        "input_cost_per_million_microusd": None,
        "output_cost_per_million_microusd": None,
        "notify_on_completion": True,
        "notify_on_failure": True,
        "tools": [],
        "communication_scopes": [],
        "knowledge_scopes": [],
    }
    payload.update(overrides)
    return payload


async def create_enabled_tool(client) -> dict[str, object]:
    server = await client.post(
        "/api/mcp-servers",
        json={
            "name": "Agent MCP",
            "transport": "streamable_http",
            "url": "https://mcp.example.test/mcp",
            "headers": {},
            "enabled": True,
            "timeout_seconds": 15,
        },
    )
    assert server.status_code == 201, server.text
    synced = await client.post(f"/api/mcp-servers/{server.json()['id']}/sync")
    assert synced.status_code == 200, synced.text
    tool = (await client.get("/api/mcp-tools")).json()[0]
    enabled = await client.put(
        f"/api/mcp-tools/{tool['id']}",
        json={
            "enabled": True,
            "default_enabled": False,
            "requires_confirmation": True,
        },
    )
    assert enabled.status_code == 200, enabled.text
    return enabled.json()


async def test_agent_crud_manual_run_and_direct_completion(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)

    created = await client.post("/api/agents", json=agent_payload())
    assert created.status_code == 201, created.text
    agent = created.json()
    assert agent["tools"] == []
    assert agent["communication_scopes"] == []

    queued = await client.post(f"/api/agents/{agent['id']}/run")
    assert queued.status_code == 202, queued.text
    run = queued.json()
    assert run["status"] == "queued"

    async with session_factory() as session:
        claimed = await claim_next_agent_run(
            session,
            worker_id="agent-test-worker",
            lease_seconds=180,
        )
    assert claimed is not None

    fake_client.chat_event_rounds = [
        [ChatCompletionDelta(content="The bounded agent completed successfully.")]
    ]
    await execute_agent_run(
        session_factory,
        run_id=claimed.id,
        worker_id="agent-test-worker",
        client=fake_client,
        mcp_client=fake_client.mcp_client,
        cipher=SecretCipher(settings.aster_encryption_key.get_secret_value()),
        settings=settings,
    )

    detail = await client.get(f"/api/agent-runs/{run['id']}")
    assert detail.status_code == 200
    result = detail.json()
    assert result["status"] == "completed"
    assert result["provider_model_id"] == "agent-model"
    assert result["final_output"] == "The bounded agent completed successfully."
    assert result["steps"][-1]["kind"] == "final"
    assert result["estimated_tokens"] > 0

    notifications = (await client.get("/api/agent-notifications")).json()
    assert notifications["unread_count"] == 1
    assert notifications["items"][0]["level"] == "success"


async def test_agent_tool_scope_is_frozen_and_requires_owner_approval(
    api_client: tuple,
) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)
    tool = await create_enabled_tool(client)

    created = await client.post(
        "/api/agents",
        json=agent_payload(
            name="Approved tool operator",
            tools=[{"tool_id": tool["id"], "approval_policy": "always"}],
        ),
    )
    assert created.status_code == 201, created.text
    agent = created.json()
    queued = await client.post(f"/api/agents/{agent['id']}/run")
    assert queued.status_code == 202, queued.text
    run_id = UUID(queued.json()["id"])

    updated = await client.put(
        f"/api/agents/{agent['id']}",
        json=agent_payload(name="Approved tool operator", tools=[]),
    )
    assert updated.status_code == 200, updated.text
    async with session_factory() as session:
        frozen = list(
            await session.scalars(
                select(AgentRunToolScope).where(AgentRunToolScope.run_id == run_id)
            )
        )
    assert [str(item.tool_id) for item in frozen] == [tool["id"]]

    fake_client.chat_event_rounds = [
        [
            ChatCompletionDelta(
                tool_calls=(
                    ToolCallDelta(
                        index=0,
                        call_id="agent-call-1",
                        name=str(tool["public_name"]),
                        arguments='{"value":"hello"}',
                    ),
                ),
                finish_reason="tool_calls",
            )
        ],
        [ChatCompletionDelta(content="The approved tool action completed.")],
    ]

    async with session_factory() as session:
        claimed = await claim_next_agent_run(
            session,
            worker_id="approval-worker",
            lease_seconds=180,
        )
    assert claimed is not None
    await execute_agent_run(
        session_factory,
        run_id=claimed.id,
        worker_id="approval-worker",
        client=fake_client,
        mcp_client=fake_client.mcp_client,
        cipher=SecretCipher(settings.aster_encryption_key.get_secret_value()),
        settings=settings,
    )

    waiting = (await client.get(f"/api/agent-runs/{run_id}")).json()
    assert waiting["status"] == "waiting_approval"
    assert fake_client.mcp_client.calls == []
    approval = waiting["approvals"][0]
    assert approval["status"] == "pending"

    approved = await client.post(f"/api/agent-approvals/{approval['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "queued"

    async with session_factory() as session:
        resumed = await claim_next_agent_run(
            session,
            worker_id="approval-worker",
            lease_seconds=180,
        )
    assert resumed is not None
    await execute_agent_run(
        session_factory,
        run_id=resumed.id,
        worker_id="approval-worker",
        client=fake_client,
        mcp_client=fake_client.mcp_client,
        cipher=SecretCipher(settings.aster_encryption_key.get_secret_value()),
        settings=settings,
    )

    completed = (await client.get(f"/api/agent-runs/{run_id}")).json()
    assert completed["status"] == "completed"
    assert fake_client.mcp_client.calls == [("echo", {"value": "hello"})]
    assert completed["tool_calls_used"] == 1


async def test_emergency_stop_cancels_active_runs_and_blocks_new_runs(
    api_client: tuple,
) -> None:
    client, _, _ = api_client
    created = await client.post(
        "/api/agents",
        json=agent_payload(name="Emergency stop test"),
    )
    assert created.status_code == 201, created.text
    agent_id = created.json()["id"]
    queued = await client.post(f"/api/agents/{agent_id}/run")
    assert queued.status_code == 202

    stopped = await client.put(
        "/api/agent-control",
        json={
            "emergency_stop": True,
            "reason": "Owner emergency test.",
        },
    )
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["emergency_stop"] is True

    runs = (await client.get("/api/agent-runs")).json()
    assert runs[0]["status"] == "cancelled"
    assert runs[0]["error_code"] == "emergency_stop"

    blocked = await client.post(f"/api/agents/{agent_id}/run")
    assert blocked.status_code == 409

    released = await client.put(
        "/api/agent-control",
        json={"emergency_stop": False, "reason": ""},
    )
    assert released.status_code == 200
    assert released.json()["emergency_stop"] is False

    async with _session_for_run(api_client) as session:
        stored = await session.get(AgentRun, UUID(runs[0]["id"]))
        assert stored is not None
        assert stored.cancel_requested is True


class _session_for_run:
    def __init__(self, api_client: tuple) -> None:
        self.factory = api_client[2]
        self.context = None

    async def __aenter__(self):
        self.context = self.factory()
        return await self.context.__aenter__()

    async def __aexit__(self, exc_type, exc, tb):
        return await self.context.__aexit__(exc_type, exc, tb)
