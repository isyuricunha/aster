from datetime import UTC, datetime

from app.automation_schedule import (
    ScheduleValidationError,
    next_run_at,
    validate_schedule,
)

AGENT_TRIGGER_TYPES = {
    "manual",
    "once",
    "interval",
    "daily",
    "weekly",
    "communication",
}


def validate_agent_schedule(
    trigger_type: str,
    schedule: dict[str, object],
    timezone_name: str,
) -> dict[str, object]:
    if trigger_type not in AGENT_TRIGGER_TYPES:
        raise ScheduleValidationError("Unsupported agent trigger")
    if trigger_type in {"manual", "communication"}:
        return {}
    return validate_schedule(trigger_type, schedule, timezone_name)


def next_agent_run_at(
    trigger_type: str,
    schedule: dict[str, object],
    timezone_name: str,
    *,
    now: datetime | None = None,
    after: datetime | None = None,
) -> datetime | None:
    if trigger_type in {"manual", "communication"}:
        return None
    return next_run_at(
        trigger_type,
        schedule,
        timezone_name,
        now=(now or datetime.now(UTC)),
        after=after,
    )
