import json

from app.communication_adapters import (
    _cursor_map,
    _imap_uid_parts,
    _mailbox_name,
    _selectable_mailboxes,
)


class FakeImapClient:
    def __init__(self, responses: list[bytes], status: str = "OK") -> None:
        self.responses = responses
        self.status = status

    def list(self) -> tuple[str, list[bytes]]:
        return self.status, self.responses


def test_mailbox_name_parses_quoted_and_unquoted_names() -> None:
    assert _mailbox_name(b'(\\HasNoChildren \\Inbox) "/" "INBOX"') == "INBOX"
    assert _mailbox_name(b'(\\HasNoChildren) "/" Projects') == "Projects"


def test_selectable_mailboxes_orders_system_folders_and_keeps_custom_folders() -> None:
    client = FakeImapClient(
        [
            b'(\\HasNoChildren) "/" Projects',
            b'(\\HasNoChildren \\Trash) "/" "Trash"',
            b'(\\HasNoChildren \\Sent) "/" "Sent"',
            b'(\\Noselect) "/" "[Provider]"',
            b'(\\HasNoChildren \\All) "/" "All Mail"',
            b'(\\HasNoChildren \\Drafts) "/" "Drafts"',
            b'(\\HasNoChildren \\Inbox) "/" "INBOX"',
            b'(\\HasNoChildren \\Junk) "/" "Spam"',
        ]
    )

    assert _selectable_mailboxes(client, "INBOX") == [
        "INBOX",
        "Sent",
        "Drafts",
        "Spam",
        "Trash",
        "Projects",
    ]


def test_selectable_mailboxes_falls_back_when_list_is_unavailable() -> None:
    assert _selectable_mailboxes(FakeImapClient([], status="NO"), "INBOX") == ["INBOX"]


def test_cursor_map_supports_legacy_and_multi_mailbox_values() -> None:
    assert _cursor_map("42", "INBOX") == {"INBOX": "42"}
    assert _cursor_map('{"INBOX":"42","Sent":"9","Broken":"nope"}', "INBOX") == {
        "INBOX": "42",
        "Sent": "9",
    }
    assert _cursor_map("not-json", "INBOX") == {}


def test_folder_aware_imap_uid_round_trip() -> None:
    stored = json.dumps({"folder": "Sent", "uid": "81"}, separators=(",", ":"))

    assert _imap_uid_parts(stored, "INBOX") == ("Sent", "81")
    assert _imap_uid_parts("81", "INBOX") == ("INBOX", "81")
