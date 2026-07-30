"""Load users.yaml and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
USERS_FILE = CONFIG_DIR / "users.yaml"
USERS_EXAMPLE_FILE = CONFIG_DIR / "users.yaml.example"


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    telegram_handle: str


@dataclass(frozen=True)
class AppConfig:
    users: tuple[User, ...]
    timezone: str
    report_time: str


def _resolve_users_path() -> Path:
    if USERS_FILE.exists():
        return USERS_FILE
    if USERS_EXAMPLE_FILE.exists():
        print(
            f"Warning: {USERS_FILE.name} not found; falling back to {USERS_EXAMPLE_FILE.name}"
        )
        return USERS_EXAMPLE_FILE
    raise FileNotFoundError(
        f"Missing config: create {USERS_FILE} from {USERS_EXAMPLE_FILE}"
    )


def load_config(*, env_file: Path | None = None) -> AppConfig:
    """Load application config from users.yaml and optional .env file."""
    load_dotenv(env_file or ROOT_DIR / ".env")

    users_path = _resolve_users_path()
    with users_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "users" not in raw:
        raise ValueError(f"Invalid config in {users_path}: missing 'users' key")

    users = tuple(
        User(
            username=str(entry["username"]),
            display_name=str(entry.get("display_name", entry["username"])),
            telegram_handle=str(entry.get("telegram_handle", entry["username"])),
        )
        for entry in raw["users"]
    )

    return AppConfig(
        users=users,
        timezone=str(raw.get("timezone", "Africa/Nairobi")),
        report_time=str(raw.get("report_time", "03:00")),
    )


def get_env(name: str, *, default: str | None = None, required: bool = False) -> str | None:
    """Read an environment variable, optionally requiring it to be set."""
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
