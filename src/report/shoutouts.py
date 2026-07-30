"""Neutral highlight rules for daily reports."""

from __future__ import annotations

from datetime import date

from src.report.models import UserReportSection

STREAK_MILESTONES = {7, 14, 30, 60}
MAX_HIGHLIGHTS = 6


def _format_name_list(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _inactive_days_before_return(section: UserReportSection, pre_sync_last_active: str | None) -> int | None:
    if not pre_sync_last_active or not section.submissions:
        return None

    first_solve_date = min(item.local_date for item in section.submissions)
    previous = date.fromisoformat(pre_sync_last_active)
    returned = date.fromisoformat(first_solve_date)
    gap = (returned - previous).days
    if gap >= 3:
        return gap
    return None


def build_highlights(
    sections: list[UserReportSection],
    *,
    pre_sync_last_active: dict[str, str | None],
) -> list[str]:
    highlights: list[str] = []

    if not sections:
        return highlights

    counts = [(section.display_name, section.counts.total) for section in sections]
    max_count = max(count for _, count in counts)
    if max_count > 0:
        leaders = [name for name, count in counts if count == max_count]
        if len(leaders) == 1:
            highlights.append(
                f"{leaders[0]} solved {max_count} "
                f"problem{'s' if max_count != 1 else ''} today (most in the group)."
            )
        else:
            names = _format_name_list(leaders)
            highlights.append(
                f"{names} each solved {max_count} "
                f"problem{'s' if max_count != 1 else ''} today (most in the group)."
            )

    hard_solvers = [
        section.display_name
        for section in sections
        if any(item.difficulty == "Hard" for item in section.submissions)
    ]
    for name in hard_solvers:
        highlights.append(f"{name} solved a Hard problem today.")

    for section in sections:
        inactive_days = _inactive_days_before_return(
            section,
            pre_sync_last_active.get(section.username),
        )
        if inactive_days is not None:
            highlights.append(f"{section.display_name} returned after {inactive_days} inactive days.")

    if sections and all(section.counts.total >= 1 for section in sections):
        highlights.append("All four members solved at least one problem today.")

    for section in sections:
        if section.counts.total > 0 and section.current_streak in STREAK_MILESTONES:
            highlights.append(f"{section.display_name} reached a {section.current_streak}-day streak.")

    return highlights[:MAX_HIGHLIGHTS]
