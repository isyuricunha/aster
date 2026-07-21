import imaplib

import pytest

from app import communication_adapters
from app.imap_sync_patch import (
    _quoted_mailbox,
    _sync_imap_sync,
    sync_imap_account,
)


class FakeImapClient:
    def __init__(self) -> None:
        self.selected: list[str] = []

    def list(self) -> tuple[str, list[bytes]]:
        return (
            "OK",
            [
                b'(\\HasNoChildren \\Inbox) "/" "INBOX"',
                b'(\\HasNoChildren \\Sent) "/" "Sent Items"',
            ],
        )

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        self.selected.append(mailbox)
        if mailbox not in {'"INBOX"', '"Sent Items"'}:
            raise imaplib.IMAP4.error(f"malformed mailbox argument: {mailbox}")
        return "OK", [b"0"]

    def uid(self, command: str, *args: object) -> tuple[str, list[bytes]]:
        assert command == "search"
        return "OK", [b""]

    def logout(self) -> tuple[str, list[bytes]]:
        return "BYE", [b"logged out"]

    def shutdown(self) -> None:
        return None


def test_sync_quotes_mailboxes_with_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeImapClient()
    monkeypatch.setattr(
        communication_adapters,
        "_imap_connect",
        lambda config, credentials: client,
    )

    result = _sync_imap_sync(
        {
            "host": "imap.example.test",
            "port": 993,
            "security": "ssl",
            "folder": "INBOX",
            "max_messages_per_sync": 50,
        },
        {"username": "owner@example.test", "password": "secret"},
        None,
    )

    assert client.selected == ['"INBOX"', '"Sent Items"']
    assert result.messages == ()


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
