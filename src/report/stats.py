"""KV-only streak stats report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.state.store import StateStore
from src.telegram.send import escape_html


@dataclass
class StatsReport:
    title_date: str
    plain_text: str
    html: str


def _streak_label(days: int) -> str:
    return f"{days} day" if days == 1 else f"{days} days"


def build_stats_report(config: AppConfig, store: StateStore) -> StatsReport:
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz=tz)
    title_date = now.strftime("%a, %b %d %Y")

    rows: list[tuple[int, str, str, str, str]] = []
    for user in config.users:
        state = store.get_user_state(user.username)
        streak = state.current_streak if state else 0
        longest = state.longest_streak if state else 0
        last_active = state.last_active_date if state and state.last_active_date else "never"
        rows.append((streak, user.display_name, user.telegram_handle, last_active, str(longest)))

    rows.sort(key=lambda row: (-row[0], row[1].lower()))

    plain_lines = [f"LeetCoders Stats - {title_date}", ""]
    html_lines = [f"<b>LeetCoders Stats</b> - {escape_html(title_date)}", ""]

    for streak, display_name, handle, last_active, longest in rows:
        plain_lines.append(f"{display_name} (@{handle})")
        plain_lines.append(
            f"  Streak: {_streak_label(streak)} | Last active: {last_active} | Best: {longest} days"
        )
        plain_lines.append("")

        name = escape_html(display_name)
        html_lines.append(f"<b>{name}</b> (@{escape_html(handle)})")
        html_lines.append(
            f"Streak: {_streak_label(streak)} | Last active: {escape_html(last_active)} | "
            f"Best: {longest} days"
        )
        html_lines.append("")

    footer = f"Next daily report: {config.report_time} EAT"
    plain_lines.append(footer)
    html_lines.append(escape_html(footer))

    return StatsReport(
        title_date=title_date,
        plain_text="\n".join(plain_lines),
        html="\n".join(html_lines),
    )
