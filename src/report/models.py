"""Report data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.leetcode.models import Difficulty
from src.state.models import EnrichedSubmission


@dataclass
class DifficultyCounts:
    easy: int = 0
    medium: int = 0
    hard: int = 0

    @property
    def total(self) -> int:
        return self.easy + self.medium + self.hard

    def add(self, difficulty: Difficulty) -> None:
        if difficulty == "Easy":
            self.easy += 1
        elif difficulty == "Medium":
            self.medium += 1
        elif difficulty == "Hard":
            self.hard += 1


@dataclass
class UserReportSection:
    display_name: str
    username: str
    telegram_handle: str
    submissions: list[EnrichedSubmission]
    counts: DifficultyCounts
    current_streak: int
    last_active_date: str | None


@dataclass
class DailyReport:
    title_date: str
    generated_at: str
    users: list[UserReportSection]
    highlights: list[str] = field(default_factory=list)
    closing_line: str = "See you tomorrow at 3:00 AM EAT."
    plain_text: str = ""
    html: str = ""
