"""Incremental sync engine for LeetCode submissions."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.leetcode.client import LeetCodeError, fetch_recent_submissions, fetch_user_profile
from src.leetcode.models import Submission, submission_datetime
from src.leetcode.problems import ProblemCache
from src.state.models import (
    MAX_SEEN_SUBMISSION_IDS,
    EnrichedSubmission,
    SyncSummary,
    UserState,
    UserSyncResult,
)
from src.state.store import StateStore, StateStoreError


def _empty_user_state(username: str) -> UserState:
    return UserState(username=username)


def _local_date_str(timestamp: int, timezone: str) -> str:
    return submission_datetime(timestamp, timezone).date().isoformat()


def _trim_seen_ids(seen_ids: list[str]) -> list[str]:
    return seen_ids[:MAX_SEEN_SUBMISSION_IDS]


def _merge_new_ids(seen_ids: list[str], new_ids: list[str]) -> list[str]:
    new_id_set = set(new_ids)
    merged = new_ids + [item for item in seen_ids if item not in new_id_set]
    return _trim_seen_ids(merged)


def _apply_streak_for_date(state: UserState, active_date: date) -> None:
    date_str = active_date.isoformat()

    if state.last_active_date == date_str:
        return

    if state.last_active_date is None:
        state.current_streak = 1
    else:
        previous = date.fromisoformat(state.last_active_date)
        if active_date == previous + timedelta(days=1):
            state.current_streak += 1
        elif active_date > previous:
            state.current_streak = 1

    state.last_active_date = date_str
    state.longest_streak = max(state.longest_streak, state.current_streak)


def _update_streaks(state: UserState, enriched: list[EnrichedSubmission]) -> None:
    if not enriched:
        return

    sorted_subs = sorted(enriched, key=lambda item: item.submission.timestamp)
    processed_dates: set[str] = set()

    for item in sorted_subs:
        if item.local_date in processed_dates:
            continue
        processed_dates.add(item.local_date)
        _apply_streak_for_date(state, date.fromisoformat(item.local_date))


def _enrich_submissions(
    submissions: list[Submission],
    *,
    problem_cache: ProblemCache,
    timezone: str,
) -> list[EnrichedSubmission]:
    enriched: list[EnrichedSubmission] = []
    for submission in submissions:
        enriched.append(
            EnrichedSubmission(
                submission=submission,
                difficulty=problem_cache.get_difficulty(submission.title_slug),
                local_date=_local_date_str(submission.timestamp, timezone),
            )
        )
    return enriched


def sync_user(
    *,
    username: str,
    display_name: str,
    config: AppConfig,
    store: StateStore,
    problem_cache: ProblemCache,
    dry_run: bool,
) -> UserSyncResult:
    profile = fetch_user_profile(username)
    if not profile.exists:
        raise LeetCodeError(f"Profile not found or private: {username}")

    submissions = fetch_recent_submissions(username, limit=20)
    state = store.get_user_state(username) or _empty_user_state(username)
    state.username = username
    pre_sync_last_active_date = state.last_active_date

    known = set(state.seen_submission_ids)
    new_raw = [submission for submission in submissions if submission.id not in known]

    did_bootstrap = False
    seeded_count = 0
    new_enriched: list[EnrichedSubmission] = []

    if not state.bootstrapped:
        state.seen_submission_ids = _trim_seen_ids([s.id for s in submissions])
        state.bootstrapped = True
        did_bootstrap = True
        seeded_count = len(submissions)
    else:
        if new_raw:
            new_ids = [submission.id for submission in new_raw]
            state.seen_submission_ids = _merge_new_ids(state.seen_submission_ids, new_ids)
            new_enriched = _enrich_submissions(
                new_raw,
                problem_cache=problem_cache,
                timezone=config.timezone,
            )
            _update_streaks(state, new_enriched)

    if not dry_run:
        store.put_user_state(state)

    return UserSyncResult(
        username=username,
        display_name=display_name,
        new_submissions=new_enriched,
        did_bootstrap=did_bootstrap,
        seeded_count=seeded_count,
        current_streak=state.current_streak,
        last_active_date=state.last_active_date,
        pre_sync_last_active_date=pre_sync_last_active_date,
    )


def _maybe_push_problem_cache(store: StateStore, problem_cache: ProblemCache) -> None:
    try:
        problem_cache.save_to_store(store)
    except StateStoreError:
        pass


def sync_all_users(
    *,
    config: AppConfig,
    store: StateStore,
    problem_cache: ProblemCache,
    dry_run: bool = False,
) -> SyncSummary:
    tz = ZoneInfo(config.timezone)
    synced_at = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M %Z")

    problem_cache.ensure_loaded(store=store)
    results: list[UserSyncResult] = []

    for user in config.users:
        result = sync_user(
            username=user.username,
            display_name=user.display_name,
            config=config,
            store=store,
            problem_cache=problem_cache,
            dry_run=dry_run,
        )
        results.append(result)

    if not dry_run:
        iso_now = datetime.now(tz=tz).isoformat()
        store.put_last_sync_at(iso_now)
        try:
            _maybe_push_problem_cache(store, problem_cache)
        except StateStoreError:
            pass

    return SyncSummary(
        synced_at=synced_at,
        dry_run=dry_run,
        store_label=store.label,
        users=results,
    )
