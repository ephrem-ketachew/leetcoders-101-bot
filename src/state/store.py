"""Persistent state storage (Cloudflare KV or local JSON fallback)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from src.config import ROOT_DIR, get_env
from src.state.models import UserState

KV_API_BASE = "https://api.cloudflare.com/client/v4"
USER_STATE_KEY = "state/users/{username}"
LAST_SYNC_KEY = "state/last_sync_at"
LAST_REPORT_KEY = "state/last_report_at"
PROBLEMS_CACHE_KEY = "cache/problems"


class StateStoreError(Exception):
    """Raised when state storage read/write fails."""


class StateStore(Protocol):
    @property
    def label(self) -> str: ...

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None: ...

    def put_json(self, key: str, value: dict[str, Any] | list[Any]) -> None: ...

    def get_user_state(self, username: str) -> UserState | None: ...

    def put_user_state(self, state: UserState) -> None: ...

    def get_last_sync_at(self) -> str | None: ...

    def put_last_sync_at(self, iso: str) -> None: ...

    def get_last_report_at(self) -> str | None: ...

    def put_last_report_at(self, iso: str) -> None: ...


def _key_to_filename(key: str) -> str:
    safe = key.replace("/", "__")
    return f"{safe}.json"


class LocalStateStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or ROOT_DIR / "data" / "state"

    @property
    def label(self) -> str:
        return f"local ({self.directory})"

    def _path_for_key(self, key: str) -> Path:
        return self.directory / _key_to_filename(key)

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        path = self._path_for_key(key)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def put_json(self, key: str, value: dict[str, Any] | list[Any]) -> None:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, sort_keys=True)

    def get_user_state(self, username: str) -> UserState | None:
        raw = self.get_json(USER_STATE_KEY.format(username=username))
        if raw is None:
            return None
        return UserState.from_dict(raw)

    def put_user_state(self, state: UserState) -> None:
        self.put_json(USER_STATE_KEY.format(username=state.username), state.to_dict())

    def get_last_sync_at(self) -> str | None:
        raw = self.get_json(LAST_SYNC_KEY)
        if not raw or not isinstance(raw, dict):
            return None
        value = raw.get("synced_at")
        return str(value) if value else None

    def put_last_sync_at(self, iso: str) -> None:
        self.put_json(LAST_SYNC_KEY, {"synced_at": iso})

    def get_last_report_at(self) -> str | None:
        raw = self.get_json(LAST_REPORT_KEY)
        if not raw or not isinstance(raw, dict):
            return None
        value = raw.get("reported_at")
        return str(value) if value else None

    def put_last_report_at(self, iso: str) -> None:
        self.put_json(LAST_REPORT_KEY, {"reported_at": iso})


class CloudflareKVStore:
    def __init__(self, account_id: str, namespace_id: str, api_token: str) -> None:
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.api_token = api_token

    @property
    def label(self) -> str:
        return "cloudflare-kv"

    def _url(self, key: str) -> str:
        encoded = quote(key, safe="")
        return (
            f"{KV_API_BASE}/accounts/{self.account_id}/storage/kv/namespaces/"
            f"{self.namespace_id}/values/{encoded}"
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_token}"}

    def get_raw(self, key: str) -> bytes | None:
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(self._url(key), headers=self._headers())
        except httpx.HTTPError as exc:
            raise StateStoreError(f"KV read failed for {key}: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise StateStoreError(
                f"KV read failed for {key}: HTTP {response.status_code} {response.text}"
            )
        return response.content

    def put_raw(self, key: str, data: bytes, *, content_type: str = "application/json") -> None:
        headers = {**self._headers(), "Content-Type": content_type}
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.put(self._url(key), headers=headers, content=data)
        except httpx.HTTPError as exc:
            raise StateStoreError(f"KV write failed for {key}: {exc}") from exc

        if response.status_code >= 400:
            raise StateStoreError(
                f"KV write failed for {key}: HTTP {response.status_code} {response.text}"
            )

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        raw = self.get_raw(key)
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8"))

    def put_json(self, key: str, value: dict[str, Any] | list[Any]) -> None:
        self.put_raw(key, json.dumps(value).encode("utf-8"))

    def get_user_state(self, username: str) -> UserState | None:
        raw = self.get_json(USER_STATE_KEY.format(username=username))
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise StateStoreError(f"Invalid user state for {username}")
        return UserState.from_dict(raw)

    def put_user_state(self, state: UserState) -> None:
        self.put_json(USER_STATE_KEY.format(username=state.username), state.to_dict())

    def get_last_sync_at(self) -> str | None:
        raw = self.get_json(LAST_SYNC_KEY)
        if not raw or not isinstance(raw, dict):
            return None
        value = raw.get("synced_at")
        return str(value) if value else None

    def put_last_sync_at(self, iso: str) -> None:
        self.put_json(LAST_SYNC_KEY, {"synced_at": iso})

    def get_last_report_at(self) -> str | None:
        raw = self.get_json(LAST_REPORT_KEY)
        if not raw or not isinstance(raw, dict):
            return None
        value = raw.get("reported_at")
        return str(value) if value else None

    def put_last_report_at(self, iso: str) -> None:
        self.put_json(LAST_REPORT_KEY, {"reported_at": iso})


def get_state_store(*, warn_local: bool = True) -> StateStore:
    account_id = get_env("CF_ACCOUNT_ID")
    namespace_id = get_env("CF_KV_NAMESPACE_ID")
    api_token = get_env("CF_API_TOKEN")

    if account_id and namespace_id and api_token:
        return CloudflareKVStore(account_id, namespace_id, api_token)

    if warn_local:
        print("Warning: CF credentials missing; using local state store (data/state/)")
    return LocalStateStore()
