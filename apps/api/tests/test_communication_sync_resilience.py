from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.communication_adapters import ReceivedMessage, SourceSync
from app.communication_models import CommunicationMessage
from app.communication_worker import _record_sync_failure_after_rollback


async def _create_imap_account(client, *, name: str = "Long subject inbox") -> str:
    response = await client.post(
        "/api/communication-accounts",
        json={
            "name": name,
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
                "password": "secret-password",
            },
            "poll_interval_seconds": 60,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_imap_sync_preserves_subject_longer_than_thread_title(
    api_client: tuple,
    monkeypatch,
) -> None:
    client, _, session_factory = api_client
    account_id = await _create_imap_account(client)
    subject = "Long imported subject " + ("x" * 700)
    message = ReceivedMessage(
        external_message_id="<long-subject@example.com>",
        external_thread_id="email:<long-subject@example.com>",
        source_id="INBOX",
        sender_name="Sender",
        sender_address="sender@example.com",
        recipients=[{"name": "Owner", "address": "owner@example.com"}],
        subject=subject,
        content_text="Message body",
        content_html=None,
        metadata={
            "imap_uid": "1289",
            "message_id_header": "<long-subject@example.com>",
        },
        sent_at=datetime(2026, 7, 21, 11, 42, tzinfo=UTC),
        is_read=False,
        attachments=(),
    )

    async def fake_sync(*_args, **_kwargs) -> SourceSync:
        return SourceSync(
            source_key="imap:INBOX",
            cursor_value="1289",
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
    assert sync_response.json()["messages_added"] == 1

    threads = (await client.get("/api/communication-threads")).json()
    assert len(threads) == 1
    assert threads[0]["title"] == subject[:500]

    async with session_factory() as session:
        stored = await session.scalar(select(CommunicationMessage))
    assert stored is not None
    assert stored.subject == subject


async def test_sync_failure_is_recorded_with_a_fresh_account_instance(
    api_client: tuple,
) -> None:
    client, _, session_factory = api_client
    account_id = await _create_imap_account(client, name="Recoverable inbox")

    async with session_factory() as session:
        await session.rollback()
        await _record_sync_failure_after_rollback(
            session,
            account_id=UUID(account_id),
            message="Synthetic sync failure",
        )

    accounts = (await client.get("/api/communication-accounts")).json()
    account = next(item for item in accounts if item["id"] == account_id)
    assert account["last_sync_status"] == "failed"
    assert account["last_error"] == "Synthetic sync failure"
