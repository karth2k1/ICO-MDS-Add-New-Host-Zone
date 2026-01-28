"""
LLM-based workflow generator using GPT-4.1.

Replaces the rule-based approach with intelligent natural language understanding.
"""

import json
from typing import Any, Dict, List, Optional

from app.llm_client import get_llm_client, CiscoLLMClient


# System prompt for workflow generation
SYSTEM_PROMPT = """You are an expert Cisco Intersight Cloud Orchestrator (ICO) workflow designer.

Your task is to analyze JIRA ticket text and generate ICO workflow definitions in JSON format.

## Available Workflow Templates

You can generate the following types of workflows:

### 1. Add Host to SAN (MDS Zoning)
- Creates device aliases for host WWPNs
- Creates zones and adds to active zoneset
- Commits zone database and saves configuration
- Supports single fabric (A only) or dual fabric (A and B)

Required inputs to extract:
- zone_name: Name for the new zone
- host_wwpn_fabric_A: WWPN for Fabric A (format: xx:xx:xx:xx:xx:xx:xx:xx)
- host_wwpn_fabric_B: WWPN for Fabric B (if dual fabric)
- vsan_id: VSAN ID number
- use_fabric_b: true if Fabric B is mentioned, false otherwise

### 2. Toggle Locator LED
- Controls the locator LED on a physical server
- Useful for identifying servers in the datacenter

Required inputs to extract:
- server_identifier: Server name, serial, or description
- led_state: "On" or "Off" (default to "On" if just "toggle" or "identify")

### 3. Get Server Inventory
- Retrieves list of compute servers from Intersight
- Can filter by various attributes

Required inputs to extract:
- max_results: Maximum number of servers (default 100)
- filter: Optional OData filter expression

### 4. Save MDS Configuration
- Saves running config to startup config on MDS switch

Required inputs to extract:
- switch_identifier: MDS switch name or IP

## Response Format

Always respond with valid JSON in this exact structure:

{
  "workflow_type": "add_host_to_san" | "toggle_locator_led" | "get_server_inventory" | "save_mds_config" | "unknown",
  "confidence": 0.0-1.0,
  "extracted_parameters": {
    // Parameters specific to the workflow type
  },
  "reasoning": "Brief explanation of why this workflow was selected",
  "warnings": ["Any issues or missing information"],
  "suggested_workflow_name": "Descriptive name for the workflow"
}

## Important Rules

1. Extract WWPN addresses exactly as written (format: xx:xx:xx:xx:xx:xx:xx:xx)
2. Extract VSAN IDs as integers
3. If both Fabric A and B are mentioned, set use_fabric_b to true
4. If information is ambiguous or missing, note it in warnings
5. Confidence should reflect how well the request matches available templates
6. If the request doesn't match any template, use "unknown" and explain what would be needed
"""


def analyze_jira_text(jira_text: str, llm_client: CiscoLLMClient = None) -> Dict[str, Any]:
    """
    Analyze JIRA ticket text using GPT-4.1 to determine workflow type and extract parameters.
    
    Args:
        jira_text: Raw JIRA ticket text
        llm_client: Optional LLM client instance
        
    Returns:
        Analysis result with workflow_type, parameters, confidence, etc.
    """
    client = llm_client or get_llm_client()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this JIRA ticket and determine the appropriate ICO workflow:\n\n{jira_text}"}
    ]
    
    try:
        result = client.get_json_completion(messages, temperature=0.1)
        return result
    except Exception as e:
        return {
            "workflow_type": "error",
            "confidence": 0,
            "extracted_parameters": {},
            "reasoning": f"LLM analysis failed: {str(e)}",
            "warnings": [str(e)],
            "suggested_workflow_name": None
        }


def generate_workflow_from_analysis(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate workflow JSON based on LLM analysis.
    
    Args:
        analysis: Result from analyze_jira_text
        
    Returns:
        List of bulk REST sub-requests for Intersight import
    """
    workflow_type = analysis.get("workflow_type", "unknown")
    params = analysis.get("extracted_parameters", {})
    
    if workflow_type == "add_host_to_san":
        from workflow_templates.mds.add_host_to_san import generate_full_workflow
        return generate_full_workflow({
            "use_fabric_b": params.get("use_fabric_b", True),
            "zone_name": params.get("zone_name"),
            "wwpns": [params.get("host_wwpn_fabric_A"), params.get("host_wwpn_fabric_B")]
        })
    
    elif workflow_type == "toggle_locator_led":
        from workflow_templates.compute.toggle_locator_led import generate_full_workflow
        return generate_full_workflow(params)
    
    elif workflow_type == "get_server_inventory":
        from workflow_templates.compute.get_server_inventory import generate_full_workflow
        return generate_full_workflow(params)
    
    elif workflow_type == "save_mds_config":
        from workflow_templates.mds.save_config import generate_full_workflow
        return generate_full_workflow(params)
    
    else:
        # Unknown workflow type - return empty or provide guidance
        return []


def generate_workflow_with_llm(jira_text: str, llm_client: CiscoLLMClient = None) -> Dict[str, Any]:
    """
    Full pipeline: analyze JIRA text and generate workflow.
    
    Args:
        jira_text: Raw JIRA ticket text
        llm_client: Optional LLM client instance
        
    Returns:
        Dictionary with analysis, workflow, and metadata
    """
    # Analyze the JIRA text
    analysis = analyze_jira_text(jira_text, llm_client)
    
    # Generate workflow based on analysis
    workflow = []
    if analysis.get("workflow_type") not in ("unknown", "error"):
        workflow = generate_workflow_from_analysis(analysis)
    
    # Generate Mermaid diagram if we have a workflow
    mermaid = ""
    if workflow:
        from app.generator import WorkflowGenerator
        gen = WorkflowGenerator()
        mermaid = gen.generate_mermaid(workflow)
    
    # Validate the workflow
    validation = {"valid": False, "errors": [], "warnings": [], "info": []}
    if workflow:
        from app.validator import WorkflowValidator
        validator = WorkflowValidator()
        validation = validator.validate(workflow)
    
    return {
        "success": analysis.get("workflow_type") not in ("unknown", "error"),
        "analysis": analysis,
        "workflow": workflow,
        "mermaid": mermaid,
        "validation": validation,
        "workflow_type": analysis.get("workflow_type"),
        "confidence": analysis.get("confidence", 0),
        "suggested_name": analysis.get("suggested_workflow_name")
    }


# Prompt for generating custom workflows (advanced feature)
CUSTOM_WORKFLOW_PROMPT = """You are an expert Cisco Intersight Cloud Orchestrator (ICO) workflow designer.

Generate a complete ICO workflow JSON based on the requirements. The output must be valid JSON that can be imported into Intersight via the Bulk Import feature.

## JSON Structure Requirements

The output must be an array of bulk.RestSubRequest objects. Each request creates one component:

1. **Custom Data Types** (if needed):
   - Uri: "/v1/workflow/CustomDataTypeDefinitions"
   - ObjectType: "workflow.CustomDataTypeDefinition"

2. **Task Definitions**:
   - Uri: "/v1/workflow/TaskDefinitions"
   - ObjectType: "workflow.TaskDefinition"
   - Must include Properties with InputDefinition and OutputDefinition

3. **Batch API Executors** (for tasks that call APIs):
   - Uri: "/v1/workflow/BatchApiExecutors"
   - ObjectType: "workflow.BatchApiExecutor"
   - Contains Batch array of workflow.WebApi calls

4. **Workflow Definitions**:
   - Uri: "/v1/workflow/WorkflowDefinitions"
   - ObjectType: "workflow.WorkflowDefinition"
   - Must include Tasks array with StartTask, worker tasks, and end tasks

## Key Rules

1. All Names must be alphanumeric with no spaces (use CamelCase)
2. Labels can have spaces and are user-friendly
3. Task references must match exactly
4. Include UI positions for all tasks
5. Use Go template syntax for variable substitution: {{.global.taskName.output.paramName}}
6. Use Intersight syntax for workflow variables: ${workflow.input.paramName}

Generate the complete workflow JSON:
"""


def generate_custom_workflow(
    requirements: str,
    llm_client: CiscoLLMClient = None
) -> Dict[str, Any]:
    """
    Generate a completely custom workflow using LLM.
    
    This is an advanced feature that lets the LLM design the entire workflow.
    
    Args:
        requirements: Detailed requirements for the workflow
        llm_client: Optional LLM client instance
        
    Returns:
        Generated workflow and metadata
    """
    client = llm_client or get_llm_client()
    
    messages = [
        {"role": "system", "content": CUSTOM_WORKFLOW_PROMPT},
        {"role": "user", "content": requirements}
    ]
    
    try:
        # Get JSON completion
        response = client.chat_completion(
            messages,
            temperature=0.2,
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        content = response["choices"][0]["message"]["content"]
        workflow = json.loads(content)
        
        # If the LLM wrapped it in an object, extract the array
        if isinstance(workflow, dict) and "workflow" in workflow:
            workflow = workflow["workflow"]
        
        # Validate
        from app.validator import WorkflowValidator
        validator = WorkflowValidator()
        validation = validator.validate(workflow if isinstance(workflow, list) else [workflow])
        
        return {
            "success": True,
            "workflow": workflow,
            "validation": validation
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "workflow": [],
            "validation": {"valid": False, "errors": [str(e)], "warnings": [], "info": []}
        }
