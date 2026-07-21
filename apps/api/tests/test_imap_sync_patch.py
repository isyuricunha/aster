from __future__ import annotations

import imaplib
import json
import re
from datetime import UTC, datetime
from email.utils import format_datetime

import pytest

from app import communication_adapters
from app.imap_sync_patch import (
    _quoted_mailbox,
    _sync_imap_sync,
    imap_backfill_progress,
    sync_imap_account,
)


def _message_bytes(folder: str, uid: int) -> bytes:
    sent_at = format_datetime(datetime(2026, 7, 21, 12, uid % 60, tzinfo=UTC))
    return (
        f"From: Sender {uid} <sender{uid}@example.test>\r\n"
        "To: owner@example.test\r\n"
        f"Subject: {folder} message {uid}\r\n"
        f"Message-ID: <{folder}-{uid}@example.test>\r\n"
        f"Date: {sent_at}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        f"Message body {uid}."
    ).encode()


class FakeImapClient:
    def __init__(self, mailboxes: dict[str, list[int]] | None = None) -> None:
        self.mailboxes = mailboxes or {"INBOX": [], "Sent Items": []}
        self.selected: list[str] = []
        self.current: str | None = None
        self.fetches: list[tuple[str, int]] = []

    def list(self) -> tuple[str, list[bytes]]:
        entries: list[bytes] = []
        for index, name in enumerate(self.mailboxes):
            flag = b"\\Inbox" if index == 0 else b"\\Sent"
            encoded = name.encode("ascii")
            entries.append(b"(\\HasNoChildren " + flag + b') "/" "' + encoded + b'"')
        return "OK", entries

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        self.selected.append(mailbox)
        decoded = mailbox[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        name = communication_adapters._decode_modified_utf7(decoded)
        if name not in self.mailboxes:
            raise imaplib.IMAP4.error(f"malformed mailbox argument: {mailbox}")
        self.current = name
        return "OK", [str(len(self.mailboxes[name])).encode()]

    def uid(self, command: str, *args: object) -> tuple[str, list[object]]:
        assert self.current is not None
        values = self.mailboxes[self.current]
        if command == "search":
            criteria = str(args[-1])
            if criteria == "ALL":
                selected = values
            elif match := re.fullmatch(r"UID (\d+):\*", criteria):
                lower = int(match.group(1))
                selected = [uid for uid in values if uid >= lower]
            elif match := re.fullmatch(r"UID 1:(\d+)", criteria):
                upper = int(match.group(1))
                selected = [uid for uid in values if uid <= upper]
            else:
                raise AssertionError(f"Unexpected search criteria: {criteria}")
            return "OK", [" ".join(str(uid) for uid in selected).encode()]
        assert command == "fetch"
        uid = int(str(args[0]))
        assert uid in values
        self.fetches.append((self.current, uid))
        return (
            "OK",
            [
                (
                    f"1 (UID {uid} RFC822 {{{uid}}} FLAGS ())".encode(),
                    _message_bytes(self.current, uid),
                ),
                b")",
            ],
        )

    def logout(self) -> tuple[str, list[bytes]]:
        return "BYE", [b"logged out"]

    def shutdown(self) -> None:
        return None


def _config(limit: int = 50) -> dict[str, object]:
    return {
        "host": "imap.example.test",
        "port": 993,
        "security": "ssl",
        "folder": "INBOX",
        "max_messages_per_sync": limit,
    }


def _install_client(monkeypatch: pytest.MonkeyPatch, client: FakeImapClient) -> None:
    monkeypatch.setattr(
        communication_adapters,
        "_imap_connect",
        lambda config, credentials: client,
    )


def _cursor_payload(value: str) -> dict[str, object]:
    payload = json.loads(value)
    assert isinstance(payload, dict)
    return payload


def test_sync_quotes_mailboxes_with_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeImapClient()
    _install_client(monkeypatch, client)

    result = _sync_imap_sync(
        _config(),
        {"username": "owner@example.test", "password": "secret"},
        None,
    )

    assert client.selected == ['"INBOX"', '"Sent Items"']
    assert result.messages == ()
    assert result.backfill_pending is False


def test_legacy_cursor_continues_backfill_without_skipping_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeImapClient({"INBOX": list(range(1, 121))})
    _install_client(monkeypatch, client)

    first = _sync_imap_sync(_config(20), {}, '{"INBOX":"120"}')
    first_payload = _cursor_payload(first.cursor_value)
    first_state = first_payload["mailboxes"]["INBOX"]

    assert [uid for _, uid in client.fetches] == list(range(120, 100, -1))
    assert len(first.messages) == 20
    assert first.backfill_pending is True
    assert first.backfill_remaining == 100
    assert first_state["newest_uid"] == 120
    assert first_state["backfill_before_uid"] == 101

    client.fetches.clear()
    second = _sync_imap_sync(_config(20), {}, first.cursor_value)

    assert [uid for _, uid in client.fetches] == list(range(100, 80, -1))
    assert len(second.messages) == 20
    assert second.backfill_remaining == 80


def test_new_messages_and_backfill_share_each_sync_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeImapClient({"INBOX": list(range(1, 121))})
    _install_client(monkeypatch, client)
    initial = _sync_imap_sync(_config(20), {}, None)

    client.mailboxes["INBOX"].extend([121, 122, 123])
    client.fetches.clear()
    result = _sync_imap_sync(_config(10), {}, initial.cursor_value)
    payload = _cursor_payload(result.cursor_value)
    state = payload["mailboxes"]["INBOX"]
    fetched = [uid for _, uid in client.fetches]

    assert fetched[:3] == [121, 122, 123]
    assert fetched[3:] == list(range(100, 93, -1))
    assert state["newest_uid"] == 123
    assert state["backfill_before_uid"] == 94
    assert result.backfill_remaining == 93


def test_empty_mailboxes_do_not_consume_the_global_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeImapClient(
        {
            "INBOX": list(range(1, 21)),
            "Sent Items": [],
        }
    )
    _install_client(monkeypatch, client)

    result = _sync_imap_sync(_config(10), {}, None)

    assert len(result.messages) == 10
    assert [folder for folder, _ in client.fetches] == ["INBOX"] * 10
    assert [uid for _, uid in client.fetches] == list(range(20, 10, -1))


def test_completed_backfill_does_not_refetch_old_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeImapClient({"INBOX": [1, 2, 3, 4, 5]})
    _install_client(monkeypatch, client)

    first = _sync_imap_sync(_config(10), {}, None)
    client.fetches.clear()
    second = _sync_imap_sync(_config(10), {}, first.cursor_value)

    assert len(first.messages) == 5
    assert first.backfill_pending is False
    assert first.backfill_remaining == 0
    assert second.messages == ()
    assert client.fetches == []
    assert imap_backfill_progress(second.cursor_value) == (False, 0)


def test_modified_utf7_mailbox_argument_round_trips() -> None:
    argument = _quoted_mailbox("Projetos & Família")
    encoded = argument[1:-1].replace('\\"', '"').replace("\\\\", "\\")

    assert communication_adapters._decode_modified_utf7(encoded) == "Projetos & Família"


@pytest.mark.asyncio
async def test_sync_exposes_imap_protocol_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_sync(
        config: dict[str, object],
        credentials: dict[str, str],
        cursor_value: str | None,
    ) -> communication_adapters.SourceSync:
        raise imaplib.IMAP4.error("SELECT command error: BAD invalid mailbox")

    monkeypatch.setattr("app.imap_sync_patch._sync_imap_sync", fail_sync)

    with pytest.raises(communication_adapters.CommunicationAdapterError) as caught:
        await sync_imap_account({}, {}, None)

    assert caught.value.code == "sync_failed"
    assert "SELECT command error: BAD invalid mailbox" in caught.value.message
