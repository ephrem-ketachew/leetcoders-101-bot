"""Local JSON cache for LeetCode problem difficulties."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.config import ROOT_DIR
from src.leetcode.client import fetch_problem_difficulty, fetch_problemset_page
from src.leetcode.models import Difficulty
from src.state.store import PROBLEMS_CACHE_KEY, StateStore

DEFAULT_CACHE_PATH = ROOT_DIR / "data" / "problems_cache.json"
DEFAULT_TIMEZONE = "Africa/Nairobi"


class ProblemCache:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_CACHE_PATH
        self._problems: dict[str, Difficulty] = {}
        self._updated_at: str | None = None
        self._total: int = 0
        self._load()

    @property
    def count(self) -> int:
        return len(self._problems)

    def _to_payload(self) -> dict[str, Any]:
        return {
            "updated_at": self._updated_at,
            "total": self._total,
            "problems": self._problems,
        }

    def _from_payload(self, raw: dict[str, Any]) -> None:
        self._updated_at = raw.get("updated_at")
        self._total = int(raw.get("total") or 0)
        problems = raw.get("problems") or {}
        self._problems = {str(k): v for k, v in problems.items()}

    def _load(self) -> None:
        if not self.path.exists():
            return

        with self.path.open(encoding="utf-8") as f:
            raw: dict[str, Any] = json.load(f)

        self._from_payload(raw)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._to_payload(), f, indent=2, sort_keys=True)

    def load_from_store(self, store: StateStore, *, min_count: int = 100) -> bool:
        raw = store.get_json(PROBLEMS_CACHE_KEY)
        if not raw or not isinstance(raw, dict):
            return False

        self._from_payload(raw)
        return self.count >= min_count

    def save_to_store(self, store: StateStore) -> None:
        if not self._problems:
            return
        store.put_json(PROBLEMS_CACHE_KEY, self._to_payload())

    def ensure_loaded(
        self,
        *,
        store: StateStore | None = None,
        min_count: int = 100,
        page_size: int = 100,
        delay: float = 0.3,
    ) -> None:
        if self.count >= min_count:
            return

        if store and self.load_from_store(store, min_count=min_count):
            return

        self.refresh(page_size=page_size, delay=delay)

        if store:
            self.save_to_store(store)

    def refresh(self, *, page_size: int = 100, delay: float = 0.3) -> int:
        skip = 0
        total = 0

        while True:
            page_total, page_problems = fetch_problemset_page(skip=skip, limit=page_size)
            total = page_total
            self._problems.update(page_problems)
            skip += page_size

            if skip >= total or not page_problems:
                break
            time.sleep(delay)

        self._total = total
        self._updated_at = datetime.now(tz=ZoneInfo(DEFAULT_TIMEZONE)).isoformat()
        self._save()
        return self.count

    def get_difficulty(self, title_slug: str) -> Difficulty:
        cached = self._problems.get(title_slug)
        if cached:
            return cached

        difficulty = fetch_problem_difficulty(title_slug)
        self._problems[title_slug] = difficulty
        if not self._updated_at:
            self._updated_at = datetime.now(tz=ZoneInfo(DEFAULT_TIMEZONE)).isoformat()
        self._save()
        return difficulty
