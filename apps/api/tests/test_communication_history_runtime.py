from types import SimpleNamespace
from uuid import uuid4

import pytest

from app import communication_adapters, communication_worker
from app.imap_read_state_patch import install_imap_read_state_patch


class FakeSession:
    def __init__(self, account: object) -> None:
        self.account = account
        self.commit_count = 0

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, model: object, account_id: object) -> object:
        return self.account

    async def commit(self) -> None:
        self.commit_count += 1


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def __call__(self) -> FakeSession:
        return self.session


@pytest.mark.asyncio
async def test_worker_drains_multiple_backfill_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = SimpleNamespace(
        id=uuid4(),
        sync_lease_owner="worker-1",
        kind="imap",
        config={"folder": "INBOX"},
        next_sync_at=None,
    )
    session = FakeSession(account)
    results = iter([(50, 1), (50, 2), (25, 0)])
    pending = iter([True, True, False])
    sync_calls = 0

    async def fake_sync(*args: object, **kwargs: object) -> tuple[int, int]:
        nonlocal sync_calls
        sync_calls += 1
        return next(results)

    async def fake_pending(*args: object, **kwargs: object) -> bool:
        return next(pending)

    monkeypatch.setattr(communication_worker, "sync_communication_account", fake_sync)
    monkeypatch.setattr(communication_worker, "_imap_backfill_pending", fake_pending)

    added, enqueued = await communication_worker.sync_claimed_communication_account(
        FakeSessionFactory(session),
        account_id=account.id,
        worker_id="worker-1",
        cipher=object(),
        store=object(),
        settings=SimpleNamespace(),
    )

    assert sync_calls == 3
    assert added == 125
    assert enqueued == 3
    assert account.next_sync_at is None


@pytest.mark.asyncio
async def test_worker_reschedules_unfinished_large_backfill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = SimpleNamespace(
        id=uuid4(),
        sync_lease_owner="worker-1",
        kind="imap",
        config={"folder": "INBOX"},
        next_sync_at=None,
    )
    session = FakeSession(account)
    sync_calls = 0

    async def fake_sync(*args: object, **kwargs: object) -> tuple[int, int]:
        nonlocal sync_calls
        sync_calls += 1
        return 50, 0

    async def always_pending(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(communication_worker, "_MAX_BACKFILL_BATCHES_PER_CLAIM", 3)
    monkeypatch.setattr(communication_worker, "sync_communication_account", fake_sync)
    monkeypatch.setattr(communication_worker, "_imap_backfill_pending", always_pending)

    added, enqueued = await communication_worker.sync_claimed_communication_account(
        FakeSessionFactory(session),
        account_id=account.id,
        worker_id="worker-1",
        cipher=object(),
        store=object(),
        settings=SimpleNamespace(),
    )

    assert sync_calls == 3
    assert added == 150
    assert enqueued == 0
    assert account.next_sync_at is not None
    assert session.commit_count == 1


def test_imap_seen_flag_is_case_insensitive() -> None:
    install_imap_read_state_patch()
    raw = (
        b"From: sender@example.test\r\n"
        b"To: owner@example.test\r\n"
        b"Subject: Seen state\r\n"
        b"Message-ID: <seen@example.test>\r\n"
        b"\r\n"
        b"Hello"
    )

    message = communication_adapters._parse_imap_message(
        raw,
        uid="42",
        folder="INBOX",
        flags="1 (UID 42 FLAGS (\\SEEN))",
    )

    assert message.is_read is True
