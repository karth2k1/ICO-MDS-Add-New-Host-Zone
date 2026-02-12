"""Regression checks against known workflow fixture files."""

import json
from pathlib import Path

from app.validator import WorkflowValidator


def test_toggle_locator_led_fixture_is_valid():
    repo_root = Path(__file__).resolve().parents[2]
    fixture_path = repo_root / "Toggle_Locator_LED_Task.json"
    with fixture_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    validator = WorkflowValidator()
    result = validator.validate(payload)
    assert result["valid"] is True, f"Fixture should remain valid: {result['errors']}"

