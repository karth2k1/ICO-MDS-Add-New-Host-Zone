"""Persistent LLM settings with env fallback and masking."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.parse import urlparse


LLM_MODEL_DISPLAY_NAME = "Cisco Chat AI GPT-4.1"

_FIELDS = (
    "client_id",
    "client_secret",
    "appkey",
    "username",
    "oauth_url",
    "chat_url",
)
_REQUIRED_FIELDS = ("client_id", "client_secret", "appkey")
_URL_FIELDS = ("oauth_url", "chat_url")
_SECRET_FIELDS = ("client_secret", "appkey")


@dataclass
class LLMSettingsStore:
    """Simple JSON-backed store for local LLM configuration."""

    path: str

    def _ensure_parent(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def load_local(self) -> dict:
        """Load raw settings from local file, if present."""
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: str(v).strip() for k, v in data.items() if k in _FIELDS and isinstance(v, str)}

    def save(self, payload: dict) -> dict:
        """Validate and persist settings."""
        normalized = _normalize_input(payload)
        validate_editable_settings(normalized)
        self._ensure_parent()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2)
        return normalized

    def clear(self) -> None:
        """Delete local settings file."""
        if os.path.exists(self.path):
            os.remove(self.path)


def _normalize_input(payload: dict) -> dict:
    normalized = {}
    payload = payload if isinstance(payload, dict) else {}
    for field in _FIELDS:
        value = payload.get(field, "")
        if value is None:
            value = ""
        if not isinstance(value, str):
            value = str(value)
        normalized[field] = value.strip()
    return normalized


def _is_valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_editable_settings(payload: dict) -> None:
    """Validate user-edited settings before save."""
    for field in _REQUIRED_FIELDS:
        if not payload.get(field, "").strip():
            raise ValueError(f"Missing required field: {field}")
    for field in _URL_FIELDS:
        value = payload.get(field, "").strip()
        if value and not _is_valid_http_url(value):
            raise ValueError(f"Invalid URL in field: {field}")


def env_defaults() -> dict:
    """Read LLM config from environment."""
    return {
        "client_id": os.environ.get("CISCO_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("CISCO_CLIENT_SECRET", "").strip(),
        "appkey": os.environ.get("CISCO_APPKEY", "").strip(),
        "username": os.environ.get("CISCO_USERNAME", "ico-workflow-generator").strip(),
        "oauth_url": os.environ.get("CISCO_OAUTH_URL", "").strip(),
        "chat_url": os.environ.get("CISCO_CHAT_AI_URL", "").strip(),
    }


def resolve_effective_settings(store: LLMSettingsStore) -> dict:
    """Merge env defaults with local overrides (local non-empty wins)."""
    effective = env_defaults()
    local = store.load_local()
    for field in _FIELDS:
        local_value = local.get(field, "").strip()
        if local_value:
            effective[field] = local_value
    return effective


def is_effectively_configured(settings: dict) -> bool:
    """True when required auth fields are available."""
    return all(bool((settings.get(field) or "").strip()) for field in _REQUIRED_FIELDS)


def masked_settings(settings: dict) -> dict:
    """Mask secret values for API/UI responses."""
    result = dict(settings)
    for field in _SECRET_FIELDS:
        raw = (result.get(field) or "").strip()
        if not raw:
            result[field] = ""
        elif len(raw) <= 4:
            result[field] = "*" * len(raw)
        else:
            result[field] = "*" * (len(raw) - 4) + raw[-4:]
    return result

