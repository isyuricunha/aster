from datetime import UTC, datetime, time, timedelta
from math import floor
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TRIGGER_TYPES = {"once", "interval", "daily", "weekly", "webhook"}


class ScheduleValidationError(ValueError):
    pass


def timezone_info(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise ScheduleValidationError(f"Unknown timezone: {name}") from error


def _parse_instant(value: object, *, timezone: ZoneInfo) -> datetime:
    if not isinstance(value, str):
        raise ScheduleValidationError("run_at must be an ISO-8601 datetime string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ScheduleValidationError("run_at must be a valid ISO-8601 datetime") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed.astimezone(UTC)


def _parse_clock(value: object) -> time:
    if not isinstance(value, str):
        raise ScheduleValidationError("time must use HH:MM")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as error:
        raise ScheduleValidationError("time must use HH:MM") from error
    if parsed.second or parsed.microsecond:
        raise ScheduleValidationError("time must not include seconds")
    return parsed


def validate_schedule(
    trigger_type: str,
    schedule: dict[str, object],
    timezone_name: str,
) -> dict[str, object]:
    if trigger_type not in TRIGGER_TYPES:
        raise ScheduleValidationError("Unsupported automation trigger")
    zone = timezone_info(timezone_name)
    if trigger_type == "webhook":
        return {}
    if trigger_type == "once":
        instant = _parse_instant(schedule.get("run_at"), timezone=zone)
        return {"run_at": instant.isoformat()}
    if trigger_type == "interval":
        seconds = schedule.get("interval_seconds")
        valid_seconds = (
            isinstance(seconds, int)
            and not isinstance(seconds, bool)
            and 60 <= seconds <= 31_536_000
        )
        if not valid_seconds:
            raise ScheduleValidationError(
                "interval_seconds must be between 60 and 31536000"
            )
        anchor_value = schedule.get("anchor_at")
        anchor = (
            _parse_instant(anchor_value, timezone=zone)
            if anchor_value is not None
            else datetime.now(UTC)
        )
        return {"interval_seconds": seconds, "anchor_at": anchor.isoformat()}
    clock = _parse_clock(schedule.get("time"))
    normalized: dict[str, object] = {"time": clock.strftime("%H:%M")}
    if trigger_type == "weekly":
        weekday = schedule.get("weekday")
        valid_weekday = (
            isinstance(weekday, int)
            and not isinstance(weekday, bool)
            and 0 <= weekday <= 6
        )
        if not valid_weekday:
            raise ScheduleValidationError("weekday must be an integer from 0 to 6")
        normalized["weekday"] = weekday
    return normalized


def next_run_at(
    trigger_type: str,
    schedule: dict[str, object],
    timezone_name: str,
    *,
    now: datetime | None = None,
    after: datetime | None = None,
) -> datetime | None:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    reference = (after or current).astimezone(UTC)
    zone = timezone_info(timezone_name)
    if trigger_type == "webhook":
        return None
    if trigger_type == "once":
        instant = _parse_instant(schedule.get("run_at"), timezone=zone)
        return instant if after is None else None
    if trigger_type == "interval":
        seconds = int(schedule["interval_seconds"])
        anchor = _parse_instant(schedule.get("anchor_at"), timezone=zone)
        if reference < anchor:
            return anchor
        elapsed = (reference - anchor).total_seconds()
        steps = floor(elapsed / seconds) + 1
        return anchor + timedelta(seconds=steps * seconds)
    clock = _parse_clock(schedule.get("time"))
    local_reference = reference.astimezone(zone)
    if trigger_type == "daily":
        candidate = datetime.combine(local_reference.date(), clock, tzinfo=zone)
        if candidate <= local_reference:
            candidate += timedelta(days=1)
        return candidate.astimezone(UTC)
    weekday = int(schedule["weekday"])
    days = (weekday - local_reference.weekday()) % 7
    candidate = datetime.combine(
        local_reference.date() + timedelta(days=days),
        clock,
        tzinfo=zone,
    )
    if candidate <= local_reference:
        candidate += timedelta(days=7)
    return candidate.astimezone(UTC)
