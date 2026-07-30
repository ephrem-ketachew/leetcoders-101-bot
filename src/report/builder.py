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
CLOSING_LINE = "Next report: 3:00 AM EAT."


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


MAX_LISTED_PROBLEMS = 5
CLOSING_LINE = "Next report: 3:00 AM EAT."

_DIFFICULTY_EMOJI = {
    "Easy": "🟢",
    "Medium": "🟡",
    "Hard": "🔴",
}

_RANK_MEDALS = ("🥇", "🥈", "🥉")


def _team_summary(sections: list[UserReportSection]) -> tuple[int, int]:
    solvers = sum(1 for section in sections if section.counts.total > 0)
    problems = sum(section.counts.total for section in sections)
    return solvers, problems


def _rank_prefix(index: int, section: UserReportSection) -> str:
    if section.counts.total <= 0:
        return "▫️ "
    if index < len(_RANK_MEDALS):
        return f"{_RANK_MEDALS[index]} "
    return "▫️ "


def _status_emoji(section: UserReportSection) -> str:
    return "✅" if section.counts.total > 0 else "❌"


def _format_counts_line(counts: DifficultyCounts) -> str:
    return (
        f"🟢 {counts.easy}   🟡 {counts.medium}   🔴 {counts.hard}   "
        f"·   Σ {counts.total}"
    )


def _format_streak_line(streak: int) -> str:
    if streak <= 0:
        return "💤 Streak: 0 days"
    fire = "🔥" if streak >= 3 else "✨"
    return f"{fire} Streak: {_streak_label(streak)}"


def _format_problem_line(item) -> str:
    emoji = _DIFFICULTY_EMOJI.get(item.difficulty, "•")
    return f"   {emoji} {item.submission.title}"


def _format_user_plain(section: UserReportSection, *, rank_prefix: str) -> list[str]:
    header = f"{rank_prefix}{_status_emoji(section)} {section.display_name} (@{section.telegram_handle})"
    lines = [header, f"   leetcode.com/u/{section.username}/"]

    if section.counts.total > 0:
        lines.append(f"   {_format_counts_line(section.counts)}")
        lines.append(f"   {_format_streak_line(section.current_streak)}")
        shown = section.submissions[:MAX_LISTED_PROBLEMS]
        for item in shown:
            lines.append(_format_problem_line(item))
        remaining = len(section.submissions) - len(shown)
        if remaining > 0:
            lines.append(f"   … +{remaining} more")
    else:
        lines.append("   No solves in this report period")
        lines.append(f"   {_format_streak_line(section.current_streak)}")

    return lines


def _format_user_html(section: UserReportSection, *, rank_prefix: str) -> list[str]:
    name = escape_html(section.display_name)
    handle = escape_html(section.telegram_handle)
    username = escape_html(section.username)
    status = _status_emoji(section)

    lines = [
        f"{rank_prefix}<b>{status} {name}</b> (@{handle})",
        f'<a href="https://leetcode.com/u/{username}/">leetcode.com/u/{username}/</a>',
    ]

    if section.counts.total > 0:
        lines.append(f"<code>{escape_html(_format_counts_line(section.counts))}</code>")
        lines.append(escape_html(_format_streak_line(section.current_streak)))
        shown = section.submissions[:MAX_LISTED_PROBLEMS]
        for item in shown:
            emoji = _DIFFICULTY_EMOJI.get(item.difficulty, "•")
            title = escape_html(item.submission.title)
            lines.append(f"   {emoji} {title}")
        remaining = len(section.submissions) - len(shown)
        if remaining > 0:
            lines.append(f"   … +{remaining} more")
    else:
        lines.append("<i>No solves in this report period</i>")
        lines.append(escape_html(_format_streak_line(section.current_streak)))

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

    solvers, problems = _team_summary(sections)
    team_size = len(sections)
    summary_line = f"Team: {solvers}/{team_size} solved · {problems} problem{'s' if problems != 1 else ''} total"

    plain_lines = [
        f"📊 Daily LeetCode Report",
        title_date,
        "",
        summary_line,
        "─" * 28,
        "",
    ]
    html_lines = [
        "<b>📊 Daily LeetCode Report</b>",
        escape_html(title_date),
        "",
        f"<i>{escape_html(summary_line)}</i>",
        "─" * 28,
        "",
    ]

    for index, section in enumerate(sections):
        rank = _rank_prefix(index, section)
        plain_lines.extend(_format_user_plain(section, rank_prefix=rank))
        plain_lines.append("")
        html_lines.extend(_format_user_html(section, rank_prefix=rank))
        html_lines.append("")

    if highlights:
        plain_lines.append("✨ Highlights")
        html_lines.append("<b>✨ Highlights</b>")
        for line in highlights:
            plain_lines.append(f"  • {line}")
            html_lines.append(f"  • {escape_html(line)}")
        plain_lines.append("")
        html_lines.append("")

    plain_lines.append(f"⏰ {CLOSING_LINE}")
    html_lines.append(f"⏰ {escape_html(CLOSING_LINE)}")

    return DailyReport(
        title_date=title_date,
        generated_at=generated_at,
        users=sections,
        highlights=highlights,
        closing_line=CLOSING_LINE,
        plain_text="\n".join(plain_lines),
        html="\n".join(html_lines),
    )
