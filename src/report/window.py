"""Report window cutoff and submission filtering."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.leetcode.models import submission_datetime
from src.state.models import EnrichedSubmission
from src.state.store import StateStore


def _parse_report_time(report_time: str) -> tuple[int, int]:
    hour_str, minute_str = report_time.split(":", 1)
    return int(hour_str), int(minute_str)


def get_report_cutoff(
    *,
    store: StateStore,
    config: AppConfig,
    now: datetime | None = None,
) -> datetime:
    last_report_at = store.get_last_report_at()
    tz = ZoneInfo(config.timezone)

    if last_report_at:
        cutoff = datetime.fromisoformat(last_report_at)
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=tz)
        return cutoff

    current = now or datetime.now(tz=tz)
    hour, minute = _parse_report_time(config.report_time)
    previous_day = current.date() - timedelta(days=1)
    return datetime(
        previous_day.year,
        previous_day.month,
        previous_day.day,
        hour,
        minute,
        tzinfo=tz,
    )


def filter_for_report(
    submissions: list[EnrichedSubmission],
    cutoff: datetime,
    timezone: str,
) -> list[EnrichedSubmission]:
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=ZoneInfo(timezone))

    filtered: list[EnrichedSubmission] = []
    for item in submissions:
        submitted = submission_datetime(item.submission.timestamp, timezone)
        if submitted > cutoff:
            filtered.append(item)
    return filtered


def filter_since_timestamp(
    submissions: list[EnrichedSubmission],
    since_iso: str | None,
    timezone: str,
) -> list[EnrichedSubmission]:
    if not since_iso:
        return submissions

    cutoff = datetime.fromisoformat(since_iso)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=ZoneInfo(timezone))
    return filter_for_report(submissions, cutoff, timezone)
