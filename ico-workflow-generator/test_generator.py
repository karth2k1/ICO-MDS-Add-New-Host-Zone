#!/usr/bin/env python3
"""
Test script for the ICO Workflow Generator.
Validates that generated workflows are valid and can be imported into Intersight.
"""

import json
import sys
import os

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.parser import parse_jira_text
from app.rule_engine import RuleEngine
from app.generator import WorkflowGenerator
from app.validator import WorkflowValidator


def test_parse_jira_text():
    """Test JIRA text parsing."""
    print("\n=== Testing JIRA Text Parser ===")
    
    test_cases = [
        {
            "name": "Add host to SAN",
            "text": """
            Add new host server-01 to SAN Fabric A and B
            
            Host Details:
            - Hostname: server-01
            - Fabric A WWPN: 20:00:00:25:b5:01:00:01
            - Fabric B WWPN: 20:00:00:25:b5:01:00:02
            - VSAN: 100
            - Zone Name: server-01-zone
            
            Actions required:
            1. Create device alias for the host WWPNs
            2. Create zone and add the host
            3. Add zone to active zoneset
            4. Activate zoneset and commit
            5. Save configuration
            """,
            "expected_keywords": ["add", "host", "san", "zone", "fabric"]
        },
        {
            "name": "Toggle LED",
            "text": "Toggle the locator LED on server rack-1-blade-3 to help identify it in the datacenter",
            "expected_keywords": ["toggle", "led", "locator"]
        },
        {
            "name": "Get inventory",
            "text": "Get a list of all servers in the Intersight inventory",
            "expected_keywords": ["inventory", "server", "list"]
        }
    ]
    
    for case in test_cases:
        print(f"\nTest case: {case['name']}")
        result = parse_jira_text(case["text"])
        
        print(f"  Keywords found: {result['keywords']}")
        print(f"  Actions found: {[a['type'] for a in result['actions']]}")
        print(f"  Parameters: {result['parameters']}")
        
        # Check if expected keywords are found
        found_expected = all(
            any(exp in kw for kw in result['keywords']) 
            for exp in case['expected_keywords']
        )
        print(f"  Expected keywords present: {found_expected}")


def test_rule_engine():
    """Test rule engine matching."""
    print("\n=== Testing Rule Engine ===")
    
    rule_engine = RuleEngine()
    
    test_cases = [
        {
            "name": "Add host to SAN",
            "requirements": {
                "raw_text": "add new host to san fabric zone wwpn device alias",
                "keywords": ["add", "host", "san", "zone", "fabric", "wwpn"],
                "actions": [{"type": "add_host_to_san"}],
                "parameters": {}
            },
            "expected_template": "add_host_to_san"
        },
        {
            "name": "Toggle LED",
            "requirements": {
                "raw_text": "toggle locator led on server",
                "keywords": ["toggle", "led", "locator", "server"],
                "actions": [{"type": "toggle_led"}],
                "parameters": {}
            },
            "expected_template": "toggle_locator_led"
        },
        {
            "name": "Server inventory",
            "requirements": {
                "raw_text": "get server inventory list all compute servers",
                "keywords": ["inventory", "server", "list", "compute"],
                "actions": [{"type": "get_inventory"}],
                "parameters": {}
            },
            "expected_template": "get_server_inventory"
        }
    ]
    
    for case in test_cases:
        print(f"\nTest case: {case['name']}")
        matches = rule_engine.match(case["requirements"])
        
        if matches:
            print(f"  Best match: {matches[0]['name']} (score: {matches[0]['score']})")
            print(f"  All matches: {[m['name'] for m in matches]}")
            
            if matches[0]['name'] == case['expected_template']:
                print("  PASS: Correct template matched")
            else:
                print(f"  FAIL: Expected {case['expected_template']}")
        else:
            print("  FAIL: No matches found")


def test_workflow_generation():
    """Test workflow generation."""
    print("\n=== Testing Workflow Generation ===")
    
    # Test toggle LED workflow generation
    print("\nGenerating 'Toggle Locator LED' workflow...")
    
    from workflow_templates.compute.toggle_locator_led import generate_full_workflow
    
    workflow = generate_full_workflow()
    
    print(f"  Components generated: {len(workflow)}")
    for component in workflow:
        body = component.get("Body", {})
        obj_type = body.get("ObjectType", "Unknown")
        name = body.get("Name", "Unknown")
        print(f"    - {obj_type}: {name}")
    
    # Validate the workflow
    validator = WorkflowValidator()
    result = validator.validate(workflow)
    
    print(f"\n  Validation result: {'VALID' if result['valid'] else 'INVALID'}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    if result['warnings']:
        print(f"  Warnings: {result['warnings']}")
    
    return workflow


def test_add_host_to_san():
    """Test Add Host to SAN workflow generation."""
    print("\n=== Testing Add Host to SAN Workflow ===")
    
    from workflow_templates.mds.add_host_to_san import generate_full_workflow
    
    params = {
        "use_fabric_b": True
    }
    
    workflow = generate_full_workflow(params)
    
    print(f"  Components generated: {len(workflow)}")
    for component in workflow:
        body = component.get("Body", {})
        obj_type = body.get("ObjectType", "Unknown")
        name = body.get("Name", "Unknown")
        uri = component.get("Uri", "")
        print(f"    - [{uri.split('/')[-1]}] {name}")
    
    # Validate
    validator = WorkflowValidator()
    result = validator.validate(workflow)
    
    print(f"\n  Validation: {'VALID' if result['valid'] else 'INVALID'}")
    if result['errors']:
        for err in result['errors']:
            print(f"    Error: {err}")
    
    return workflow


def test_full_integration():
    """Test full integration from JIRA text to workflow."""
    print("\n=== Testing Full Integration ===")
    
    jira_text = """
    JIRA Ticket: INFRA-1234
    Title: Add new ESXi host to SAN storage
    
    Description:
    We need to add a new ESXi host (esxi-prod-05) to the SAN fabric.
    
    Requirements:
    - Add host to SAN Fabric A and Fabric B
    - Host WWPN for Fabric A: 20:00:00:25:b5:05:00:01
    - Host WWPN for Fabric B: 20:00:00:25:b5:05:00:02
    - VSAN: 100
    - Zone name: esxi-prod-05-zone
    
    Please create the device alias, zone, and add to the active zoneset.
    Don't forget to save the configuration.
    """
    
    print("Input JIRA text:")
    print("-" * 40)
    print(jira_text[:200] + "...")
    print("-" * 40)
    
    # Step 1: Parse
    print("\nStep 1: Parsing JIRA text...")
    requirements = parse_jira_text(jira_text)
    print(f"  Keywords: {requirements['keywords'][:10]}...")
    print(f"  Actions: {[a['type'] for a in requirements['actions']]}")
    print(f"  WWPNs found: {requirements['parameters'].get('wwpns', [])}")
    
    # Step 2: Match templates
    print("\nStep 2: Matching templates...")
    rule_engine = RuleEngine()
    matches = rule_engine.match(requirements)
    print(f"  Matches found: {len(matches)}")
    for m in matches[:3]:
        print(f"    - {m['name']} (score: {m['score']})")
    
    # Step 3: Generate workflow
    print("\nStep 3: Generating workflow...")
    generator = WorkflowGenerator()
    workflow = generator.generate(matches[:1], requirements)  # Use top match
    print(f"  Components generated: {len(workflow)}")
    
    # Step 4: Validate
    print("\nStep 4: Validating...")
    validator = WorkflowValidator()
    result = validator.validate(workflow)
    print(f"  Valid: {result['valid']}")
    print(f"  Errors: {len(result['errors'])}")
    print(f"  Warnings: {len(result['warnings'])}")
    
    # Step 5: Generate Mermaid diagram
    print("\nStep 5: Generating diagram...")
    mermaid = generator.generate_mermaid(workflow)
    print("  Diagram generated:")
    for line in mermaid.split('\n')[:10]:
        print(f"    {line}")
    if len(mermaid.split('\n')) > 10:
        print("    ...")
    
    return workflow, result


def export_sample_workflow():
    """Export a sample workflow to a file for manual import testing."""
    print("\n=== Exporting Sample Workflow ===")
    
    from workflow_templates.compute.toggle_locator_led import generate_full_workflow
    
    workflow = generate_full_workflow()
    
    output_path = os.path.join(
        os.path.dirname(__file__),
        "sample_output_workflow.json"
    )
    
    with open(output_path, "w") as f:
        json.dump(workflow, f, indent=2)
    
    print(f"  Exported to: {output_path}")
    print(f"  File size: {os.path.getsize(output_path)} bytes")
    print("\n  This file can be imported into Intersight Cloud Orchestrator")
    print("  via the Bulk Import feature or API.")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ICO Workflow Generator - Test Suite")
    print("=" * 60)
    
    try:
        test_parse_jira_text()
        test_rule_engine()
        test_workflow_generation()
        test_add_host_to_san()
        workflow, result = test_full_integration()
        export_sample_workflow()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
        if result['valid']:
            print("\nThe generated workflow is VALID and ready for Intersight import.")
        else:
            print("\nWarning: There were validation issues. Review the errors above.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
