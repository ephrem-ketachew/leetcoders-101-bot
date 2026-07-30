"""LeetCode GraphQL client (zero authentication)."""

from __future__ import annotations

from typing import Any

import httpx

from src.leetcode.models import Difficulty, Submission, UserProfile

GRAPHQL_URL = "https://leetcode.com/graphql"
DEFAULT_TIMEOUT = 10.0
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "LeetCoders101Bot/1.0",
}

QUERY_USER_PROFILE = """
query userProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submitStats {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

QUERY_RECENT_SUBMISSIONS = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

QUERY_QUESTION_DIFFICULTY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    difficulty
    titleSlug
  }
}
"""

QUERY_PROBLEMSET = """
query problemsetQuestionList(
  $categorySlug: String
  $limit: Int
  $skip: Int
  $filters: QuestionListFilterInput
) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      titleSlug
      difficulty
    }
  }
}
"""


class LeetCodeError(Exception):
    """Raised when a LeetCode GraphQL request fails."""


def _graphql(
    query: str,
    variables: dict[str, Any],
    *,
    operation_name: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query, "variables": variables}
    if operation_name:
        payload["operationName"] = operation_name

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(GRAPHQL_URL, json=payload, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise LeetCodeError(f"HTTP request failed: {exc}") from exc

    if "errors" in body:
        messages = "; ".join(
            err.get("message", str(err)) for err in body["errors"]
        )
        raise LeetCodeError(f"GraphQL error: {messages}")

    data = body.get("data")
    if data is None:
        raise LeetCodeError("GraphQL response missing 'data' field")

    return data


def fetch_user_profile(username: str) -> UserProfile:
    data = _graphql(
        QUERY_USER_PROFILE,
        {"username": username},
        operation_name="userProfile",
    )
    matched = data.get("matchedUser")
    if not matched:
        return UserProfile(username=username, exists=False)
    return UserProfile(username=str(matched.get("username", username)), exists=True)


def fetch_recent_submissions(username: str, *, limit: int = 20) -> list[Submission]:
    if limit < 1 or limit > 20:
        raise ValueError("limit must be between 1 and 20 (public API cap)")

    data = _graphql(
        QUERY_RECENT_SUBMISSIONS,
        {"username": username, "limit": limit},
        operation_name="recentAcSubmissions",
    )
    raw_list = data.get("recentAcSubmissionList") or []

    submissions: list[Submission] = []
    for item in raw_list:
        submissions.append(
            Submission(
                id=str(item["id"]),
                title=str(item["title"]),
                title_slug=str(item["titleSlug"]),
                timestamp=int(item["timestamp"]),
            )
        )
    return submissions


def fetch_problem_difficulty(title_slug: str) -> Difficulty:
    data = _graphql(
        QUERY_QUESTION_DIFFICULTY,
        {"titleSlug": title_slug},
        operation_name="questionData",
    )
    question = data.get("question")
    if not question or not question.get("difficulty"):
        raise LeetCodeError(f"Could not resolve difficulty for problem: {title_slug}")

    difficulty = str(question["difficulty"])
    if difficulty not in ("Easy", "Medium", "Hard"):
        raise LeetCodeError(f"Unexpected difficulty '{difficulty}' for {title_slug}")
    return difficulty  # type: ignore[return-value]


def fetch_problemset_page(*, skip: int, limit: int) -> tuple[int, dict[str, Difficulty]]:
    data = _graphql(
        QUERY_PROBLEMSET,
        {
            "categorySlug": "",
            "skip": skip,
            "limit": limit,
            "filters": {},
        },
        operation_name="problemsetQuestionList",
    )
    page = data.get("problemsetQuestionList") or {}
    total = int(page.get("total") or 0)
    questions = page.get("questions") or []

    problems: dict[str, Difficulty] = {}
    for item in questions:
        slug = item.get("titleSlug")
        difficulty = item.get("difficulty")
        if slug and difficulty in ("Easy", "Medium", "Hard"):
            problems[str(slug)] = difficulty  # type: ignore[assignment]

    return total, problems
