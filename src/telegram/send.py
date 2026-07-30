"""Telegram Bot API helpers."""

from __future__ import annotations

import httpx

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4000


class TelegramError(Exception):
    """Raised when a Telegram API request fails."""


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_message(
    *,
    token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
) -> None:
    for chunk in _split_message(text):
        _send_single(token=token, chat_id=chat_id, text=chunk, parse_mode=parse_mode)


def _split_message(text: str) -> list[str]:
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > MAX_MESSAGE_LENGTH:
            if current:
                chunks.append(current.rstrip())
                current = ""
            for index in range(0, len(line), MAX_MESSAGE_LENGTH):
                chunks.append(line[index : index + MAX_MESSAGE_LENGTH])
            continue

        if len(current) + len(line) > MAX_MESSAGE_LENGTH:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line

    if current:
        chunks.append(current.rstrip())
    return chunks


def _send_single(*, token: str, chat_id: str, text: str, parse_mode: str) -> None:
    url = TELEGRAM_API_BASE.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload)
            body = response.json()
    except httpx.HTTPError as exc:
        raise TelegramError(f"HTTP request failed: {exc}") from exc

    if response.status_code >= 400 or not body.get("ok"):
        description = body.get("description", response.text)
        raise TelegramError(f"Telegram API error: {description}")
