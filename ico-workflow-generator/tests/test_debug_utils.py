"""Tests for debug mode redaction and truncation utilities."""

from app.debug_utils import parse_bool, redact_sensitive, truncate_payload


def test_parse_bool_variants():
    assert parse_bool(True) is True
    assert parse_bool("true") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("false") is False
    assert parse_bool(None) is False


def test_redact_sensitive_masks_known_fields():
    payload = {
        "token": "abc",
        "nested": {"client_secret": "xyz", "safe": "ok"},
        "headers": {"authorization": "Bearer data"},
    }
    redacted, notes = redact_sensitive(payload)
    assert redacted["token"] == "***REDACTED***"
    assert redacted["nested"]["client_secret"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "ok"
    assert redacted["headers"]["authorization"] == "***REDACTED***"
    assert notes


def test_truncate_payload_marks_truncation():
    payload = {"blob": "x" * 2000}
    truncated, was_truncated = truncate_payload(payload, 120)
    assert was_truncated is True
    assert truncated.get("__truncated__") is True

