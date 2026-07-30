"""State and sync result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.leetcode.models import Difficulty, Submission

MAX_SEEN_SUBMISSION_IDS = 200


@dataclass
class UserState:
    username: str
    seen_submission_ids: list[str] = field(default_factory=list)
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: str | None = None
    bootstrapped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "seen_submission_ids": self.seen_submission_ids,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "last_active_date": self.last_active_date,
            "bootstrapped": self.bootstrapped,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserState:
        return cls(
            username=str(data["username"]),
            seen_submission_ids=[str(x) for x in data.get("seen_submission_ids", [])],
            current_streak=int(data.get("current_streak", 0)),
            longest_streak=int(data.get("longest_streak", 0)),
            last_active_date=data.get("last_active_date"),
            bootstrapped=bool(data.get("bootstrapped", False)),
        )


@dataclass(frozen=True)
class EnrichedSubmission:
    submission: Submission
    difficulty: Difficulty
    local_date: str


@dataclass
class UserSyncResult:
    username: str
    display_name: str
    new_submissions: list[EnrichedSubmission]
    did_bootstrap: bool
    seeded_count: int
    current_streak: int
    last_active_date: str | None
    pre_sync_last_active_date: str | None = None


@dataclass
class SyncSummary:
    synced_at: str
    dry_run: bool
    store_label: str
    users: list[UserSyncResult]

    @property
    def total_new(self) -> int:
        return sum(len(user.new_submissions) for user in self.users)
