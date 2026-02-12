"""Tests for parser and rule-engine behavior."""

from app.parser import parse_jira_text
from app.rule_engine import RuleEngine


def test_parse_jira_text_extracts_expected_parameters():
    text = """
    Add new host esxi-prod-05 to SAN.
    Fabric A WWPN: 20:00:00:25:b5:05:00:01
    Fabric B WWPN: 20:00:00:25:b5:05:00:02
    VSAN 100
    """
    result = parse_jira_text(text)
    assert "wwpns" in result["parameters"]
    assert len(result["parameters"]["wwpns"]) == 2
    assert result["parameters"]["vsan_ids"] == [100]
    assert "add" in result["keywords"]
    assert "san" in result["keywords"]
    assert "fabric" in result["keywords"]


def test_rule_engine_matches_add_host_to_san():
    requirements = parse_jira_text(
        "Add host server-01 to SAN fabric A and B, create zone and activate zoneset."
    )
    engine = RuleEngine()
    matches = engine.match(requirements)
    assert matches, "Expected at least one template match"
    assert matches[0]["name"] == "add_host_to_san"

