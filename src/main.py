"""CLI entry point for the LeetCode progress tracker bot."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import load_config
from src.leetcode.client import LeetCodeError, fetch_recent_submissions, fetch_user_profile
from src.leetcode.models import Submission, format_submission_time, submission_datetime
from src.leetcode.problems import ProblemCache
from src.state.models import EnrichedSubmission, SyncSummary, UserSyncResult
from src.state.store import StateStoreError, get_state_store
from src.state.sync import sync_all_users

NOT_IMPLEMENTED = "Not implemented yet — see IMPLEMENTATION.md for phase details."


def _stub(message: str) -> int:
    print(message)
    return 0


def _resolve_fetch_targets(args: argparse.Namespace) -> list[tuple[str, str | None]]:
    config = load_config()
    config_by_username = {user.username: user for user in config.users}

    if args.all:
        return [(user.username, user.display_name) for user in config.users]

    username = args.user
    if username not in config_by_username:
        print(f"Note: {username} is not in config/users.yaml; fetching anyway.")
    display_name = config_by_username.get(username).display_name if username in config_by_username else None
    return [(username, display_name)]


def _print_user_submissions(
    username: str,
    display_name: str | None,
    submissions: list[Submission],
    cache: ProblemCache,
    timezone: str,
) -> None:
    label = display_name or username
    print(f"User: {label} ({username})")
    print(f"Recent submissions ({len(submissions)}):")
    print()

    if not submissions:
        print("  (none)")
        print()
        return

    for submission in submissions:
        difficulty = cache.get_difficulty(submission.title_slug)
        when = format_submission_time(submission.timestamp, timezone)
        print(f"  {when}  |  {submission.title} ({difficulty})")
    print()


def _fetch_one_user(
    username: str,
    display_name: str | None,
    *,
    limit: int,
    cache: ProblemCache,
    timezone: str,
) -> int:
    profile = fetch_user_profile(username)
    if not profile.exists:
        print(f"Error: LeetCode profile not found or private: {username}", file=sys.stderr)
        return 1

    submissions = fetch_recent_submissions(username, limit=limit)
    _print_user_submissions(username, display_name, submissions, cache, timezone)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    if args.all and args.user:
        print("Error: use either --user or --all, not both.", file=sys.stderr)
        return 1
    if not args.all and not args.user:
        print("Error: provide --user USERNAME or --all.", file=sys.stderr)
        return 1

    config = load_config()
    cache = ProblemCache()
    cache.ensure_loaded()

    exit_code = 0
    for username, display_name in _resolve_fetch_targets(args):
        try:
            result = _fetch_one_user(
                username,
                display_name,
                limit=args.limit,
                cache=cache,
                timezone=config.timezone,
            )
            exit_code = max(exit_code, result)
        except LeetCodeError as exc:
            print(f"Error fetching {username}: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


def cmd_cache_problems(args: argparse.Namespace) -> int:
    cache = ProblemCache()
    if cache.count >= 100 and not args.force:
        print(f"Cache already loaded: {cache.count} problems at {cache.path}")
        print("Use --force to refresh.")
        return 0

    print("Downloading LeetCode problem list...")
    start = time.perf_counter()
    try:
        count = cache.refresh()
    except LeetCodeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start
    print(f"Cached {count} problems in {elapsed:.1f}s")
    print(f"Saved to: {cache.path}")
    return 0


def _filter_since_report(
    submissions: list[EnrichedSubmission],
    last_report_at: str | None,
    timezone: str,
) -> list[EnrichedSubmission]:
    if not last_report_at:
        return submissions

    cutoff = datetime.fromisoformat(last_report_at)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=ZoneInfo(timezone))

    filtered: list[EnrichedSubmission] = []
    for item in submissions:
        submitted = submission_datetime(item.submission.timestamp, timezone)
        if submitted > cutoff:
            filtered.append(item)
    return filtered


def _print_sync_user(
    result: UserSyncResult,
    *,
    timezone: str,
    since_report: bool,
    last_report_at: str | None,
) -> None:
    print(f"{result.display_name} ({result.username})")

    if result.did_bootstrap:
        print(
            f"  Bootstrap: seeded {result.seeded_count} seen submissions "
            f"(0 counted as new)"
        )
    else:
        submissions = result.new_submissions
        if since_report:
            submissions = _filter_since_report(submissions, last_report_at, timezone)
        print(f"  New submissions: {len(submissions)}")

    streak_label = "day" if result.current_streak == 1 else "days"
    active = result.last_active_date or "never"
    print(f"  Streak: {result.current_streak} {streak_label} (last active: {active})")

    if not result.did_bootstrap:
        submissions = result.new_submissions
        if since_report:
            submissions = _filter_since_report(submissions, last_report_at, timezone)
        for item in submissions:
            when = format_submission_time(item.submission.timestamp, timezone)
            print(f"    {when} | {item.submission.title} ({item.difficulty})")

    print()


def _print_sync_summary(summary: SyncSummary, *, since_report: bool, last_report_at: str | None, timezone: str) -> None:
    mode = " (dry-run)" if summary.dry_run else ""
    print(f"Sync summary - {summary.synced_at}{mode}")
    print(f"Store: {summary.store_label}")
    print()

    for result in summary.users:
        _print_sync_user(
            result,
            timezone=timezone,
            since_report=since_report,
            last_report_at=last_report_at,
        )

    total = summary.total_new
    if since_report and last_report_at:
        total = sum(
            len(_filter_since_report(user.new_submissions, last_report_at, timezone))
            for user in summary.users
        )
    print(f"Total new across team: {total}")


def cmd_sync(args: argparse.Namespace) -> int:
    config = load_config()
    store = get_state_store()
    cache = ProblemCache()
    last_report_at = store.get_last_report_at() if args.since_report else None

    try:
        summary = sync_all_users(
            config=config,
            store=store,
            problem_cache=cache,
            dry_run=args.dry_run,
        )
    except (LeetCodeError, StateStoreError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_sync_summary(
        summary,
        since_report=args.since_report,
        last_report_at=last_report_at,
        timezone=config.timezone,
    )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    mode = "send" if args.send else "dry-run"
    return _stub(f"report ({mode}): {NOT_IMPLEMENTED} (Phase 3)")


def cmd_daily(args: argparse.Namespace) -> int:
    mode = "send" if args.send else "dry-run"
    return _stub(f"daily ({mode}): {NOT_IMPLEMENTED} (Phase 4)")


def cmd_config(_args: argparse.Namespace) -> int:
    config = load_config()
    print(f"Timezone: {config.timezone}")
    print(f"Report time: {config.report_time}")
    print(f"Users ({len(config.users)}):")
    for user in config.users:
        print(
            f"  - {user.display_name} (@{user.telegram_handle}) "
            f"-> leetcode.com/u/{user.username}/"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leetcoders-bot",
        description="Daily LeetCode progress tracker for Telegram.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch recent submissions for a user")
    fetch_group = fetch_parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument("--user", help="LeetCode username")
    fetch_group.add_argument("--all", action="store_true", help="Fetch all users from config")
    fetch_parser.add_argument("--limit", type=int, default=20, help="Max submissions (1-20)")
    fetch_parser.set_defaults(func=cmd_fetch)

    cache_parser = subparsers.add_parser(
        "cache-problems",
        help="Download or refresh local problem difficulty cache",
    )
    cache_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download full problem list even if cache exists",
    )
    cache_parser.set_defaults(func=cmd_cache_problems)

    sync_parser = subparsers.add_parser("sync", help="Sync submissions and update state")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes without writing state",
    )
    sync_parser.add_argument(
        "--since-report",
        action="store_true",
        help="Only show new submissions after last_report_at",
    )
    sync_parser.set_defaults(func=cmd_sync)

    report_parser = subparsers.add_parser("report", help="Generate and optionally send report")
    report_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print report to stdout (default)",
    )
    report_parser.add_argument(
        "--send",
        action="store_true",
        help="Send report to Telegram group",
    )
    report_parser.set_defaults(func=cmd_report)

    daily_parser = subparsers.add_parser(
        "daily",
        help="Full daily pipeline: sync, report, update state",
    )
    daily_parser.add_argument(
        "--send",
        action="store_true",
        help="Send report to Telegram group",
    )
    daily_parser.set_defaults(func=cmd_daily)

    config_parser = subparsers.add_parser("config", help="Show loaded configuration")
    config_parser.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

