"""CLI entry point for the LeetCode progress tracker bot."""

from __future__ import annotations

import argparse
import sys

from src.config import load_config

NOT_IMPLEMENTED = "Not implemented yet — see IMPLEMENTATION.md for phase details."


def _stub(message: str) -> int:
    print(message)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    return _stub(f"fetch --user {args.user}: {NOT_IMPLEMENTED} (Phase 1)")


def cmd_sync(args: argparse.Namespace) -> int:
    dry = " (dry-run)" if args.dry_run else ""
    return _stub(f"sync{dry}: {NOT_IMPLEMENTED} (Phase 2)")


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
    fetch_parser.add_argument("--user", required=True, help="LeetCode username")
    fetch_parser.set_defaults(func=cmd_fetch)

    sync_parser = subparsers.add_parser("sync", help="Sync submissions and update state")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes without writing state",
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
