from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.automation_models import Automation, AutomationRun
from app.automation_queue import enqueue_due_automations


async def test_scheduler_enqueues_one_catch_up_run_and_skips_old_backlog(
    api_client: tuple,
) -> None:
    _, _, session_factory = api_client
    now = datetime.now(UTC)
    async with session_factory() as session:
        automation = Automation(
            name="Backlog test",
            instruction="Return ok.",
            enabled=True,
            trigger_type="interval",
            timezone="UTC",
            schedule={
                "interval_seconds": 60,
                "anchor_at": (now - timedelta(days=1)).isoformat(),
            },
            next_run_at=now - timedelta(days=1),
        )
        session.add(automation)
        await session.commit()
        await session.refresh(automation)
        automation_id = automation.id

    async with session_factory() as session:
        assert await enqueue_due_automations(session, limit=25) == 1

    async with session_factory() as session:
        stored = await session.get(Automation, automation_id)
        assert stored is not None
        assert stored.next_run_at is not None
        stored_next = stored.next_run_at
        if stored_next.tzinfo is None:
            stored_next = stored_next.replace(tzinfo=UTC)
        assert stored_next > now
        count = int(
            await session.scalar(
                select(func.count(AutomationRun.id)).where(
                    AutomationRun.automation_id == automation_id
                )
            )
            or 0
        )
        assert count == 1

    async with session_factory() as session:
        assert await enqueue_due_automations(session, limit=25) == 0
