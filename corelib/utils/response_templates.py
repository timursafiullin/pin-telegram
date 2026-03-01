from __future__ import annotations

from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo


def _coerce_datetime(value: datetime | str, timezone_name: str | None = None) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value)

    if timezone_name:
        tz = ZoneInfo(timezone_name)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
    return dt


def _format_day(dt: datetime) -> str:
    return dt.strftime("%d %B %Y")


def _format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def format_schedule_response(
    *,
    day: datetime | str,
    events: Iterable[dict[str, str]],
    timezone_name: str | None = None,
) -> str:
    day_dt = _coerce_datetime(day, timezone_name)
    event_list = list(events)
    if not event_list:
        return f"On {_format_day(day_dt)} you have nothing scheduled."

    lines = [f"On {_format_day(day_dt)} your schedule is:"]
    for idx, event in enumerate(event_list, start=1):
        start_dt = _coerce_datetime(event["start_time"], timezone_name)
        lines.append(f"{idx}. {_format_time(start_dt)} – {event['title']}")
    return "\n".join(lines)


def format_event_created_response(
    *,
    start_time: datetime | str,
    title: str,
    timezone_name: str | None = None,
) -> str:
    start_dt = _coerce_datetime(start_time, timezone_name)
    return f"Accepted. Scheduled:\n- {_format_time(start_dt)}, {_format_day(start_dt)}, {title}"
