import json

import httpx
import pytest

from app.communication_adapters import send_discord_reply
from app.communication_storage import (
    CommunicationAttachmentStore,
    CommunicationStorageError,
)


@pytest.mark.asyncio
async def test_discord_reply_disables_all_mentions(monkeypatch) -> None:
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["authorization"] = request.headers.get("Authorization")
        received["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "9001",
                "timestamp": "2026-07-18T12:00:00Z",
            },
        )

    real_client = httpx.AsyncClient

    def client_factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(
        "app.communication_adapters.httpx.AsyncClient",
        client_factory,
    )

    result = await send_discord_reply(
        {
            "api_base_url": "https://discord.example/api/v10",
            "channel_ids": ["123"],
        },
        {"token": "bot-secret"},
        channel_id="123",
        reply_to_message_id="456",
        content="Hello @everyone <@42>",
        timeout_seconds=30,
    )

    assert result.external_message_id == "discord:9001"
    assert received["url"] == "https://discord.example/api/v10/channels/123/messages"
    assert received["authorization"] == "Bot bot-secret"
    assert received["payload"] == {
        "content": "Hello @everyone <@42>",
        "allowed_mentions": {"parse": []},
        "message_reference": {
            "message_id": "456",
            "channel_id": "123",
            "fail_if_not_exists": False,
        },
    }


def test_communication_storage_is_private_and_bounded(tmp_path) -> None:
    store = CommunicationAttachmentStore(str(tmp_path))
    stored = store.write(
        account_id="account",
        message_id="message",
        filename="../invoice?.txt",
        media_type="text/plain",
        data=b"private attachment",
        max_bytes=1_000,
    )

    assert stored.filename == "invoice_.txt"
    assert stored.storage_key.startswith("communications/account/message/")
    assert store.read(stored.storage_key) == b"private attachment"

    with pytest.raises(CommunicationStorageError):
        store.read("../outside")

    with pytest.raises(CommunicationStorageError):
        store.write(
            account_id="account",
            message_id="message",
            filename="large.bin",
            media_type="application/octet-stream",
            data=b"1234",
            max_bytes=3,
        )
