"""Build plain-text and HTML daily reports."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.report.models import DailyReport, DifficultyCounts, UserReportSection
from src.report.shoutouts import build_highlights
from src.report.window import filter_for_report
from src.state.models import SyncSummary
from src.telegram.send import escape_html

MAX_LISTED_PROBLEMS = 5
CLOSING_LINE = "See you tomorrow at 3:00 AM EAT."


def _counts_from_submissions(submissions) -> DifficultyCounts:
    counts = DifficultyCounts()
    for item in submissions:
        counts.add(item.difficulty)
    return counts


def _streak_label(days: int) -> str:
    return f"{days} day" if days == 1 else f"{days} days"


def _build_user_sections(
    config: AppConfig,
    summary: SyncSummary,
    cutoff: datetime,
) -> list[UserReportSection]:
    sync_by_username = {result.username: result for result in summary.users}

    sections: list[UserReportSection] = []
    for user in config.users:
        sync_result = sync_by_username[user.username]
        filtered = filter_for_report(
            sync_result.new_submissions,
            cutoff,
            config.timezone,
        )
        sections.append(
            UserReportSection(
                display_name=user.display_name,
                username=user.username,
                telegram_handle=user.telegram_handle,
                submissions=filtered,
                counts=_counts_from_submissions(filtered),
                current_streak=sync_result.current_streak,
                last_active_date=sync_result.last_active_date,
            )
        )

    sections.sort(key=lambda section: (-section.counts.total, section.display_name.lower()))
    return sections


def _format_user_plain(section: UserReportSection) -> list[str]:
    lines = [
        f"{section.display_name} (@{section.telegram_handle}) - {section.username}",
        (
            f"  Total: {section.counts.total}  |  "
            f"Easy: {section.counts.easy}  Medium: {section.counts.medium}  "
            f"Hard: {section.counts.hard}"
        ),
        f"  Streak: {_streak_label(section.current_streak)}",
    ]

    if not section.submissions:
        return lines

    shown = section.submissions[:MAX_LISTED_PROBLEMS]
    for item in shown:
        lines.append(f"  - {item.submission.title} ({item.difficulty})")

    remaining = len(section.submissions) - len(shown)
    if remaining > 0:
        lines.append(f"  ... and {remaining} more")
    return lines


def _format_user_html(section: UserReportSection) -> list[str]:
    name = escape_html(section.display_name)
    handle = escape_html(section.telegram_handle)
    username = escape_html(section.username)
    lines = [
        f"<b>{name}</b> (@{handle}) - <code>{username}</code>",
        (
            f"Total: {section.counts.total} | "
            f"Easy: {section.counts.easy} Medium: {section.counts.medium} "
            f"Hard: {section.counts.hard}"
        ),
        f"Streak: {_streak_label(section.current_streak)}",
    ]

    if not section.submissions:
        return lines

    shown = section.submissions[:MAX_LISTED_PROBLEMS]
    for item in shown:
        title = escape_html(item.submission.title)
        lines.append(f"- {title} ({item.difficulty})")

    remaining = len(section.submissions) - len(shown)
    if remaining > 0:
        lines.append(f"... and {remaining} more")
    return lines


def build_daily_report(
    config: AppConfig,
    summary: SyncSummary,
    cutoff: datetime,
) -> DailyReport:
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz=tz)
    title_date = now.strftime("%a, %b %d %Y")
    generated_at = now.strftime("%Y-%m-%d %H:%M %Z")

    sections = _build_user_sections(config, summary, cutoff)
    pre_sync_last_active = {
        result.username: result.pre_sync_last_active_date for result in summary.users
    }
    highlights = build_highlights(sections, pre_sync_last_active=pre_sync_last_active)

    plain_lines = [f"Daily LeetCode Report - {title_date}", ""]
    html_lines = [f"<b>Daily LeetCode Report</b> - {escape_html(title_date)}", ""]

    for section in sections:
        plain_lines.extend(_format_user_plain(section))
        plain_lines.append("")
        html_lines.extend(_format_user_html(section))
        html_lines.append("")

    if highlights:
        plain_lines.append("Highlights")
        html_lines.append("<b>Highlights</b>")
        for line in highlights:
            plain_lines.append(f"- {line}")
            html_lines.append(f"- {escape_html(line)}")
        plain_lines.append("")
        html_lines.append("")

    plain_lines.append(CLOSING_LINE)
    html_lines.append(escape_html(CLOSING_LINE))

    return DailyReport(
        title_date=title_date,
        generated_at=generated_at,
        users=sections,
        highlights=highlights,
        closing_line=CLOSING_LINE,
        plain_text="\n".join(plain_lines),
        html="\n".join(html_lines),
    )
