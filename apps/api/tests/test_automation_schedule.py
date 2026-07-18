from datetime import UTC, datetime

import pytest

from app.automation_schedule import (
    ScheduleValidationError,
    next_run_at,
    validate_schedule,
)


def test_once_schedule_normalizes_local_time_to_utc() -> None:
    schedule = validate_schedule(
        "once",
        {"run_at": "2026-07-20T08:00:00"},
        "America/Sao_Paulo",
    )
    assert schedule == {"run_at": "2026-07-20T11:00:00+00:00"}
    assert next_run_at(
        "once",
        schedule,
        "America/Sao_Paulo",
        now=datetime(2026, 7, 19, tzinfo=UTC),
    ) == datetime(2026, 7, 20, 11, tzinfo=UTC)
    assert next_run_at(
        "once",
        schedule,
        "America/Sao_Paulo",
        after=datetime(2026, 7, 20, 11, tzinfo=UTC),
    ) is None


def test_interval_schedule_advances_from_stable_anchor() -> None:
    schedule = validate_schedule(
        "interval",
        {
            "interval_seconds": 3600,
            "anchor_at": "2026-07-17T10:00:00Z",
        },
        "UTC",
    )
    assert next_run_at(
        "interval",
        schedule,
        "UTC",
        now=datetime(2026, 7, 17, 10, 30, tzinfo=UTC),
    ) == datetime(2026, 7, 17, 11, tzinfo=UTC)
    assert next_run_at(
        "interval",
        schedule,
        "UTC",
        after=datetime(2026, 7, 17, 13, tzinfo=UTC),
    ) == datetime(2026, 7, 17, 14, tzinfo=UTC)


def test_daily_and_weekly_schedules_use_local_wall_clock() -> None:
    daily = validate_schedule("daily", {"time": "08:15"}, "America/Sao_Paulo")
    assert next_run_at(
        "daily",
        daily,
        "America/Sao_Paulo",
        now=datetime(2026, 7, 17, 10, tzinfo=UTC),
    ) == datetime(2026, 7, 17, 11, 15, tzinfo=UTC)

    weekly = validate_schedule(
        "weekly",
        {"time": "09:00", "weekday": 0},
        "America/Sao_Paulo",
    )
    assert next_run_at(
        "weekly",
        weekly,
        "America/Sao_Paulo",
        now=datetime(2026, 7, 17, 12, tzinfo=UTC),
    ) == datetime(2026, 7, 20, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("trigger_type", "schedule", "timezone"),
    [
        ("interval", {"interval_seconds": 59}, "UTC"),
        ("weekly", {"time": "08:00", "weekday": 7}, "UTC"),
        ("daily", {"time": "25:00"}, "UTC"),
        ("once", {"run_at": "not-a-date"}, "UTC"),
        ("daily", {"time": "08:00"}, "Mars/Olympus"),
    ],
)
def test_invalid_schedules_are_rejected(
    trigger_type: str,
    schedule: dict[str, object],
    timezone: str,
) -> None:
    with pytest.raises(ScheduleValidationError):
        validate_schedule(trigger_type, schedule, timezone)
