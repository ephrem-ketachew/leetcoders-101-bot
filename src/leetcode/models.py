"""Data models for LeetCode API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

Difficulty = Literal["Easy", "Medium", "Hard"]


@dataclass(frozen=True)
class Submission:
    id: str
    title: str
    title_slug: str
    timestamp: int


@dataclass(frozen=True)
class UserProfile:
    username: str
    exists: bool


def submission_datetime(timestamp: int, tz: str = "Africa/Nairobi") -> datetime:
    """Convert a LeetCode Unix timestamp to a timezone-aware datetime."""
    return datetime.fromtimestamp(timestamp, tz=ZoneInfo(tz))


def format_submission_time(timestamp: int, tz: str = "Africa/Nairobi") -> str:
    """Format submission time for CLI output."""
    dt = submission_datetime(timestamp, tz)
    return dt.strftime("%Y-%m-%d %H:%M %Z")
