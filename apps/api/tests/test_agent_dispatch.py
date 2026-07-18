from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.agent_communication_dispatch import dispatch_agent_communication_events
from app.agent_dispatch_models import AgentMessageDispatch
from app.agent_models import AgentRun
from app.communication_models import (
    CommunicationAccount,
    CommunicationMessage,
    CommunicationThread,
)
from app.config import settings


def communication_agent_payload(account_id: str) -> dict[str, object]:
    return {
        "name": "Communication operator",
        "description": "A bounded event-driven agent.",
        "goal": "Summarize matching future support messages.",
        "enabled": True,
        "paused": False,
        "trigger_type": "communication",
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
        "communication_scopes": [
            {
                "account_id": account_id,
                "allow_read": True,
                "allow_reply": False,
                "reply_approval_policy": "always",
            }
        ],
        "knowledge_scopes": [],
    }


async def test_dispatches_only_future_matching_messages_once(api_client: tuple) -> None:
    client, _, session_factory = api_client
    account_response = await client.post(
        "/api/communication-accounts",
        json={
            "name": "Agent dispatch inbox",
            "kind": "imap",
            "enabled": False,
            "config": {
                "host": "imap.example.test",
                "port": 993,
                "security": "ssl",
                "folder": "INBOX",
            },
            "credentials": {
                "username": "agent@example.test",
                "password": "private-password",
            },
            "poll_interval_seconds": 60,
        },
    )
    assert account_response.status_code == 201, account_response.text
    account_id = account_response.json()["id"]

    agent_response = await client.post(
        "/api/agents",
        json=communication_agent_payload(account_id),
    )
    assert agent_response.status_code == 201, agent_response.text
    agent_id = agent_response.json()["id"]

    rule_response = await client.post(
        "/api/agent-communication-rules",
        json={
            "name": "Future support messages",
            "agent_id": agent_id,
            "account_id": account_id,
            "enabled": True,
            "sender_pattern": "*@example.test",
            "source_ids": ["INBOX"],
            "body_contains": "agent",
            "require_mention": False,
        },
    )
    assert rule_response.status_code == 201, rule_response.text
    rule_created_at = datetime.fromisoformat(rule_response.json()["created_at"])

    async with session_factory() as session:
        account = await session.get(CommunicationAccount, UUID(account_id))
        assert account is not None
        thread = CommunicationThread(
            account_id=account.id,
            kind="email",
            external_thread_id="agent-dispatch-thread",
            title="Support",
            participants=[],
            metadata={"source_id": "INBOX"},
            unread_count=2,
            last_message_at=rule_created_at + timedelta(seconds=1),
        )
        session.add(thread)
        await session.flush()
        session.add_all(
            [
                CommunicationMessage(
                    account_id=account.id,
                    thread_id=thread.id,
                    external_message_id="agent-dispatch-old",
                    direction="inbound",
                    source_id="INBOX",
                    sender_name="Old sender",
                    sender_address="old@example.test",
                    recipients=[],
                    subject="Old agent request",
                    content_text="This agent message predates the rule.",
                    content_html=None,
                    metadata={},
                    is_read=False,
                    sent_at=rule_created_at - timedelta(seconds=2),
                    received_at=rule_created_at - timedelta(seconds=1),
                ),
                CommunicationMessage(
                    account_id=account.id,
                    thread_id=thread.id,
                    external_message_id="agent-dispatch-new",
                    direction="inbound",
                    source_id="INBOX",
                    sender_name="New sender",
                    sender_address="new@example.test",
                    recipients=[],
                    subject="New agent request",
                    content_text="Please let the agent review this future message.",
                    content_html=None,
                    metadata={},
                    is_read=False,
                    sent_at=rule_created_at + timedelta(milliseconds=500),
                    received_at=rule_created_at + timedelta(seconds=1),
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        first = await dispatch_agent_communication_events(
            session,
            settings=settings,
            limit=100,
        )
    async with session_factory() as session:
        second = await dispatch_agent_communication_events(
            session,
            settings=settings,
            limit=100,
        )
        runs = list(
            await session.scalars(
                select(AgentRun).where(AgentRun.agent_id == UUID(agent_id))
            )
        )
        dispatch_count = int(
            await session.scalar(select(func.count(AgentMessageDispatch.id))) or 0
        )

    assert first == 1
    assert second == 0
    assert len(runs) == 1
    assert runs[0].trigger_source == "communication"
    assert runs[0].trigger_payload["message"]["sender_address"] == "new@example.test"
    assert dispatch_count == 1
