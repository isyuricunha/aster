from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.automation_models import AutomationRun
from app.communication_adapters import ReceivedMessage, SourceSync
from app.communication_models import CommunicationMessage


async def test_account_credentials_are_never_returned(api_client: tuple) -> None:
    client, _, _ = api_client
    response = await client.post(
        "/api/communication-accounts",
        json={
            "name": "Primary inbox",
            "kind": "imap",
            "enabled": False,
            "config": {
                "host": "imap.example.com",
                "port": 993,
                "security": "ssl",
                "folder": "INBOX",
            },
            "credentials": {
                "username": "owner@example.com",
                "password": "never-return-this-password",
            },
            "poll_interval_seconds": 60,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["kind"] == "imap"
    assert payload["credential_names"] == ["password", "username"]
    assert "never-return-this-password" not in response.text
    assert "owner@example.com" not in response.text


async def test_inbound_message_enqueues_matching_automation(
    api_client: tuple,
    monkeypatch,
) -> None:
    client, _, session_factory = api_client
    account_response = await client.post(
        "/api/communication-accounts",
        json={
            "name": "Support inbox",
            "kind": "imap",
            "enabled": False,
            "config": {
                "host": "imap.example.com",
                "port": 993,
                "security": "ssl",
                "folder": "INBOX",
            },
            "credentials": {
                "username": "support@example.com",
                "password": "secret-password",
            },
            "poll_interval_seconds": 60,
        },
    )
    account_id = account_response.json()["id"]

    automation_response = await client.post(
        "/api/automations",
        json={
            "name": "Support triage",
            "description": "Classify allowed support email.",
            "instruction": "Summarize the inbound message and identify the requested action.",
            "enabled": True,
            "trigger_type": "communication",
            "timezone": "UTC",
            "schedule": {},
            "model_id": None,
            "persona_id": None,
            "use_default_persona": False,
            "notify_on_success": True,
            "notify_on_failure": True,
            "max_attempts": 1,
            "retry_delay_seconds": 0,
            "timeout_seconds": 30,
            "deliveries": [],
        },
    )
    assert automation_response.status_code == 201
    automation_id = automation_response.json()["id"]

    rule_response = await client.post(
        "/api/communication-rules",
        json={
            "name": "Trusted support sender",
            "account_id": account_id,
            "automation_id": automation_id,
            "enabled": True,
            "sender_pattern": "*@customer.example",
            "source_ids": [],
            "body_contains": "refund",
            "require_mention": False,
        },
    )
    assert rule_response.status_code == 201

    message = ReceivedMessage(
        external_message_id="<support-001@customer.example>",
        external_thread_id="email:<support-001@customer.example>",
        source_id="INBOX",
        sender_name="Customer",
        sender_address="person@customer.example",
        recipients=[{"name": "Support", "address": "support@example.com"}],
        subject="Refund request",
        content_text="Please review my refund request.",
        content_html=None,
        metadata={"imap_uid": "41", "message_id_header": "<support-001@customer.example>"},
        sent_at=datetime(2026, 7, 18, 9, 0, tzinfo=UTC),
        is_read=False,
        attachments=(),
    )

    async def fake_sync(*_args, **_kwargs) -> SourceSync:
        return SourceSync(
            source_key="imap:INBOX",
            cursor_value="41",
            messages=(message,),
        )

    monkeypatch.setattr(
        "app.communication_service.sync_imap_account",
        fake_sync,
    )

    sync_response = await client.post(
        f"/api/communication-accounts/{account_id}/sync"
    )
    assert sync_response.status_code == 200
    assert sync_response.json() == {
        "status": "ok",
        "messages_added": 1,
        "automations_enqueued": 1,
    }

    threads = (await client.get("/api/communication-threads")).json()
    assert len(threads) == 1
    assert threads[0]["title"] == "Refund request"
    assert threads[0]["unread_count"] == 1

    runs = (await client.get("/api/automation-runs?limit=100")).json()
    assert len(runs) == 1
    assert runs[0]["trigger_source"] == "communication"
    assert runs[0]["trigger_payload"]["message"]["sender_address"] == (
        "person@customer.example"
    )

    duplicate_response = await client.post(
        f"/api/communication-accounts/{account_id}/sync"
    )
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["messages_added"] == 0
    assert duplicate_response.json()["automations_enqueued"] == 0

    async with session_factory() as session:
        messages = list(await session.scalars(select(CommunicationMessage)))
        runs = list(await session.scalars(select(AutomationRun)))
    assert len(messages) == 1
    assert len(runs) == 1


async def test_thread_can_be_marked_read(api_client: tuple) -> None:
    client, _, session_factory = api_client
    account = (
        await client.post(
            "/api/communication-accounts",
            json={
                "name": "Discord updates",
                "kind": "discord",
                "enabled": False,
                "config": {
                    "channel_ids": ["123456789"],
                    "channel_labels": {"123456789": "Updates"},
                },
                "credentials": {"token": "discord-token"},
                "poll_interval_seconds": 60,
            },
        )
    ).json()

    from app.communication_models import (
        CommunicationAccount,
        CommunicationMessage,
        CommunicationThread,
    )

    async with session_factory() as session:
        account_row = await session.get(CommunicationAccount, UUID(account["id"]))
        assert account_row is not None
        thread = CommunicationThread(
            account_id=account_row.id,
            kind="discord",
            external_thread_id="discord:123456789",
            title="Updates",
            participants=[],
            metadata={"source_id": "123456789"},
            unread_count=1,
            last_message_at=datetime.now(UTC),
        )
        session.add(thread)
        await session.flush()
        session.add(
            CommunicationMessage(
                account_id=account_row.id,
                thread_id=thread.id,
                external_message_id="discord:1",
                direction="inbound",
                source_id="123456789",
                sender_name="Member",
                sender_address="42",
                recipients=[],
                subject="Updates",
                content_text="Hello",
                content_html=None,
                metadata={"discord_message_id": "1"},
                is_read=False,
                sent_at=datetime.now(UTC),
                received_at=datetime.now(UTC),
            )
        )
        await session.commit()
        thread_id = thread.id

    response = await client.post(f"/api/communication-threads/{thread_id}/read")
    assert response.status_code == 200
    assert response.json()["unread_count"] == 0
    assert response.json()["messages"][0]["is_read"] is True
