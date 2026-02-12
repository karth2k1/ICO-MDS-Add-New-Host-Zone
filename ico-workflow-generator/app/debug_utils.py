"""Utilities for safe, opt-in debug telemetry in API responses."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple

SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|secret|password|api[_-]?key|authorization|client[_-]?secret)",
    re.IGNORECASE,
)


def parse_bool(value: Any) -> bool:
    """Parse a truthy value from strings/bools."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def debug_requested(request_obj: Any) -> bool:
    """Check if caller requested debug output for this request."""
    header_value = request_obj.headers.get("X-Debug-Mode", "")
    if parse_bool(header_value):
        return True

    if request_obj.is_json:
        payload = request_obj.get_json(silent=True) or {}
        return parse_bool(payload.get("debug"))

    return parse_bool(request_obj.form.get("debug", ""))


def redact_sensitive(payload: Any) -> Tuple[Any, List[str]]:
    """Recursively redact sensitive keys and return redaction notes."""
    notes: List[str] = []

    def _walk(value: Any, path: str) -> Any:
        if isinstance(value, dict):
            redacted: Dict[str, Any] = {}
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if SENSITIVE_KEY_PATTERN.search(str(key)):
                    notes.append(child_path)
                    redacted[key] = "***REDACTED***"
                else:
                    redacted[key] = _walk(child, child_path)
            return redacted
        if isinstance(value, list):
            return [_walk(item, f"{path}[{idx}]") for idx, item in enumerate(value)]
        if isinstance(value, str) and SENSITIVE_KEY_PATTERN.search(value):
            notes.append(path or "value")
            return "***REDACTED***"
        return value

    return _walk(deepcopy(payload), ""), notes


def truncate_payload(payload: Any, max_chars: int) -> Tuple[Any, bool]:
    """
    Truncate payload by serialized size.

    Returns payload and whether truncation occurred.
    """
    if max_chars <= 0:
        return payload, False

    serialized = json.dumps(payload, ensure_ascii=True)
    if len(serialized) <= max_chars:
        return payload, False

    truncated = serialized[: max_chars - 32] + '..."__truncated__":true}'
    return {"raw_preview": truncated, "__truncated__": True}, True

