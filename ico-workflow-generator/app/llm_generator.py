"""
LLM-based workflow generator using GPT-4.1 with sample-based learning.

This approach feeds real ICO workflow examples to the LLM, enabling it to
generate ANY workflow - not just pre-defined templates.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from app.debug_utils import redact_sensitive, truncate_payload
from app.llm_client import get_llm_client, CiscoLLMClient


# =============================================================================
# Sample Workflows - These teach the LLM the exact ICO JSON format
# =============================================================================

# Minimal Task Definition example
SAMPLE_TASK_DEFINITION = {
    "Body": {
        "ClassId": "workflow.TaskDefinition",
        "DefaultVersion": True,
        "Description": "Enables or disables a port on an MDS switch",
        "Label": "MDS Port Admin Action",
        "Name": "MDSPortAdminAction",
        "ObjectType": "workflow.TaskDefinition",
        "Properties": {
            "ExternalMeta": True,
            "InputDefinition": [
                {
                    "CustomDataTypeProperties": {
                        "CatalogMoid": "shared",
                        "CustomDataTypeName": "MDSTargetDataType",
                        "ObjectType": "workflow.CustomDataProperty"
                    },
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "MDS target switch",
                    "DisplayMeta": {
                        "InventorySelector": True,
                        "ObjectType": "workflow.DisplayMeta",
                        "WidgetType": "None"
                    },
                    "Label": "MDS Switch",
                    "Name": "mds_switch",
                    "ObjectType": "workflow.TargetDataType",
                    "Properties": [],
                    "Required": True
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "Port interface name (e.g., fc1/1)",
                    "DisplayMeta": {
                        "InventorySelector": False,
                        "ObjectType": "workflow.DisplayMeta",
                        "WidgetType": "None"
                    },
                    "Label": "Port Interface",
                    "Name": "port_interface",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "string"
                    },
                    "Required": True
                },
                {
                    "Default": {
                        "ObjectType": "workflow.DefaultValue",
                        "Override": True,
                        "Value": "no shutdown"
                    },
                    "Description": "Admin action to perform",
                    "DisplayMeta": {
                        "InventorySelector": False,
                        "ObjectType": "workflow.DisplayMeta",
                        "WidgetType": "Radio"
                    },
                    "Label": "Admin Action",
                    "Name": "admin_action",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {
                            "EnumList": [
                                {"Label": "Enable Port", "ObjectType": "workflow.EnumEntry", "Value": "no shutdown"},
                                {"Label": "Disable Port", "ObjectType": "workflow.EnumEntry", "Value": "shutdown"}
                            ],
                            "ObjectType": "workflow.Constraints"
                        },
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "enum"
                    },
                    "Required": True
                }
            ],
            "ObjectType": "workflow.Properties",
            "OutputDefinition": [
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "API response",
                    "DisplayMeta": {
                        "InventorySelector": False,
                        "ObjectType": "workflow.DisplayMeta",
                        "WidgetType": "None"
                    },
                    "Label": "Response",
                    "Name": "response",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "json"
                    }
                }
            ],
            "RetryCount": 3,
            "RetryDelay": 60,
            "RetryPolicy": "Fixed",
            "SupportStatus": "Supported",
            "Timeout": 600,
            "TimeoutPolicy": "Timeout"
        },
        "RollbackTasks": [],
        "SharedScope": "user",
        "Tags": [
            {"Key": "author", "Value": "ico-automation"},
            {"Key": "subcategory", "Value": "MDS"},
            {"Key": "category", "Value": "Networking"}
        ],
        "Version": 1
    },
    "ClassId": "bulk.RestSubRequest",
    "ObjectType": "bulk.RestSubRequest",
    "TargetMoid": "",
    "Uri": "/v1/workflow/TaskDefinitions",
    "Verb": "POST"
}

# Minimal BatchApiExecutor example
SAMPLE_BATCH_EXECUTOR = {
    "Body": {
        "Batch": [
            {
                "Body": "{\n  \"ins_api\": {\n    \"version\": \"1.2\",\n    \"type\": \"cli_conf\",\n    \"chunk\": \"0\",\n    \"sid\": \"1\",\n    \"input\": \"interface {{.global.task.input.port_interface}} ; {{.global.task.input.admin_action}}\",\n    \"output_format\": \"json\"\n  }\n}",
                "ContentType": "json",
                "Description": "Execute port admin action on MDS switch",
                "EndpointRequestType": "Internal",
                "Label": "Port Admin Action",
                "Method": "POST",
                "Name": "PortAdminAction",
                "ObjectType": "workflow.WebApi",
                "Outcomes": [],
                "Protocol": "https",
                "ResponseSpec": {
                    "ErrorParameters": [],
                    "ObjectType": "content.Grammar",
                    "Parameters": [
                        {
                            "AcceptSingleValue": False,
                            "ComplexType": "",
                            "ItemType": "simple",
                            "Name": "api_response",
                            "ObjectType": "content.Parameter",
                            "Path": "$",
                            "Secure": False,
                            "Type": "json"
                        }
                    ],
                    "Types": []
                },
                "TargetType": "Endpoint",
                "Url": "/ins"
            }
        ],
        "CancelAction": [],
        "ClassId": "workflow.BatchApiExecutor",
        "Constraints": {"ObjectType": "workflow.TaskConstraints"},
        "Description": "Enables or disables a port on an MDS switch",
        "Name": "MDS Port Admin Action",
        "ObjectType": "workflow.BatchApiExecutor",
        "Output": {
            "response": "{{.global.PortAdminAction.output.api_response}}"
        },
        "SharedScope": "user",
        "TaskDefinition": {
            "ObjectType": "workflow.TaskDefinition",
            "Selector": "Name eq 'MDSPortAdminAction' and Version eq 1"
        }
    },
    "ClassId": "bulk.RestSubRequest",
    "ObjectType": "bulk.RestSubRequest",
    "TargetMoid": "",
    "Uri": "/v1/workflow/BatchApiExecutors",
    "Verb": "POST"
}

# Minimal WorkflowDefinition example
SAMPLE_WORKFLOW = {
    "Body": {
        "ClassId": "workflow.WorkflowDefinition",
        "DefaultVersion": True,
        "Description": "Manages MDS port state with save configuration",
        "InputDefinition": [
            {
                "CustomDataTypeProperties": {
                    "CatalogMoid": "shared",
                    "CustomDataTypeName": "MDSTargetDataType",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "MDS switch to configure",
                "DisplayMeta": {
                    "InventorySelector": True,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "MDS Switch",
                "Name": "mds_switch",
                "ObjectType": "workflow.TargetDataType",
                "Properties": [],
                "Required": True
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Port interface (e.g., fc1/1)",
                "DisplayMeta": {
                    "InventorySelector": False,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "Port Interface",
                "Name": "port_interface",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "string"
                },
                "Required": True
            },
            {
                "Default": {
                    "ObjectType": "workflow.DefaultValue",
                    "Override": True,
                    "Value": "no shutdown"
                },
                "Description": "Enable or disable the port",
                "DisplayMeta": {
                    "InventorySelector": False,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "Radio"
                },
                "Label": "Port Action",
                "Name": "port_action",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {
                        "EnumList": [
                            {"Label": "Enable", "ObjectType": "workflow.EnumEntry", "Value": "no shutdown"},
                            {"Label": "Disable", "ObjectType": "workflow.EnumEntry", "Value": "shutdown"}
                        ],
                        "ObjectType": "workflow.Constraints"
                    },
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "enum"
                },
                "Required": True
            }
        ],
        "InputParameterSet": [],
        "Label": "MDS Port Management",
        "Name": "MDSPortManagement",
        "ObjectType": "workflow.WorkflowDefinition",
        "OutputDefinition": [
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Result message",
                "DisplayMeta": {
                    "InventorySelector": False,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "Result",
                "Name": "result",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "string"
                }
            }
        ],
        "OutputParameters": {
            "result": "Port ${workflow.input.port_interface} action '${workflow.input.port_action}' completed successfully."
        },
        "Properties": {
            "EnableDebug": True,
            "ExternalMeta": True,
            "ObjectType": "workflow.WorkflowProperties",
            "SupportStatus": "Supported"
        },
        "SharedScope": "user",
        "Tags": [
            {"Key": "author", "Value": "ico-automation"},
            {"Key": "subcategory", "Value": "MDS"},
            {"Key": "category", "Value": "Networking"}
        ],
        "Tasks": [
            {
                "Name": "StartTask",
                "NextTask": "ExecutePortAction",
                "ObjectType": "workflow.StartTask"
            },
            {
                "Name": "SuccessEndTask",
                "ObjectType": "workflow.SuccessEndTask"
            },
            {
                "Name": "FailureEndTask",
                "ObjectType": "workflow.FailureEndTask"
            },
            {
                "CatalogMoid": "user",
                "Description": "Execute the port admin action",
                "InputParameters": {
                    "mds_switch": "${workflow.input.mds_switch}",
                    "port_interface": "${workflow.input.port_interface}",
                    "admin_action": "${workflow.input.port_action}"
                },
                "Label": "Execute Port Action",
                "Name": "ExecutePortAction",
                "ObjectType": "workflow.WorkerTask",
                "OnSuccess": "SaveConfig",
                "OnFailure": "FailureEndTask",
                "TaskDefinitionName": "MDSPortAdminAction",
                "Version": 1
            },
            {
                "CatalogMoid": "user",
                "Description": "Save running config to startup",
                "InputParameters": {
                    "mds_switch": "${workflow.input.mds_switch}"
                },
                "Label": "Save Configuration",
                "Name": "SaveConfig",
                "ObjectType": "workflow.WorkerTask",
                "OnSuccess": "SuccessEndTask",
                "OnFailure": "FailureEndTask",
                "TaskDefinitionName": "SaveMDSConfiguration",
                "Version": 1
            }
        ],
        "UiInputFilters": [],
        "UiRenderingData": {
            "Positions": [
                {"Name": "StartTask", "X": 300, "Y": 50},
                {"Name": "ExecutePortAction", "X": 300, "Y": 150},
                {"Name": "SaveConfig", "X": 300, "Y": 250},
                {"Name": "SuccessEndTask", "X": 300, "Y": 350},
                {"Name": "FailureEndTask", "X": 500, "Y": 350}
            ]
        },
        "VariableDefinition": [],
        "Version": 1
    },
    "ClassId": "bulk.RestSubRequest",
    "ObjectType": "bulk.RestSubRequest",
    "TargetMoid": "",
    "Uri": "/v1/workflow/WorkflowDefinitions",
    "Verb": "POST"
}


# =============================================================================
# System Prompt for Pure LLM Generation
# =============================================================================

BASE_SYSTEM_PROMPT = """You are an expert Cisco Intersight Cloud Orchestrator (ICO) workflow designer.

Your task is to generate complete ICO workflow definitions in JSON format based on user requirements. 
You will generate the FULL workflow JSON, not just analyze requirements.

## Output Format

You must output a JSON array of bulk.RestSubRequest objects that can be imported into Intersight.
The array should contain:
1. Any required CustomDataTypeDefinitions (if needed for new data types)
2. TaskDefinition objects for each task
3. BatchApiExecutor objects that implement each task
4. WorkflowDefinition that orchestrates the tasks

## Key ICO Concepts

### 1. Task Definitions (workflow.TaskDefinition)
- Define reusable tasks with inputs and outputs
- Must have matching BatchApiExecutor for implementation
- Name must be alphanumeric (CamelCase, no spaces)
- Label can have spaces (user-friendly display name)

### 2. Batch API Executors (workflow.BatchApiExecutor)
- Implement tasks using WebApi calls
- For MDS switches, use the NX-API via /ins endpoint with ins_api JSON body
- Use Go template syntax for variables: {{.global.task.input.param_name}}
- Output mapping uses: {{.global.WebApiName.output.param_name}}

### 3. Workflow Definitions (workflow.WorkflowDefinition)
- Orchestrate multiple tasks into a workflow
- Use ${workflow.input.param} for workflow inputs
- Use ${TaskName.output.param} for task outputs
- Must include StartTask, SuccessEndTask, and FailureEndTask
- Worker tasks need OnSuccess and OnFailure transitions

### 4. MDS Switch Commands (NX-API)
Common MDS CLI commands for the ins_api input field:
- Port enable: "interface fc1/1 ; no shutdown"
- Port disable: "interface fc1/1 ; shutdown"  
- VSAN assignment: "vsan database ; vsan 100 interface fc1/1"
- Show commands: "show interface fc1/1 | json native"
- Config save: "copy running-config startup-config"

### 5. Variable Substitution
- Task input variables: {{.global.task.input.variable_name}}
- WebApi output extraction: {{.global.WebApiName.output.param_name}}
- Workflow variables: ${workflow.input.variable_name}
- Task output in workflow: ${TaskName.output.variable_name}

## Sample ICO Components

Here are REAL examples of the exact JSON structures you must produce:

### Sample TaskDefinition:
__SAMPLE_TASK_DEFINITION__

### Sample BatchApiExecutor:
__SAMPLE_BATCH_EXECUTOR__

### Sample WorkflowDefinition:
__SAMPLE_WORKFLOW__

## Important Rules

1. Generate COMPLETE, VALID JSON that can be imported to Intersight
2. Follow the exact structure shown in the samples above
3. Use alphanumeric CamelCase for Name fields (no spaces)
4. Use descriptive Labels with spaces for user-friendly display
5. Include proper UiRenderingData with task positions
6. Link BatchApiExecutor to TaskDefinition via Selector
7. For MDS tasks, use MDSTargetDataType from shared catalog
8. Always include error handling (OnFailure transitions)
9. Include a save configuration step for MDS workflows
10. For workflow.WebApi, TargetType must be one of: Endpoint or Local.
    Never use values like "Intersight" or object-type strings like "workflow.TargetType".

## Response Format

Your response must be a VALID JSON array. Do not include any text before or after the JSON.
The JSON should be an array starting with [ and ending with ].
"""


def build_system_prompt(context_artifacts: Optional[List[Dict[str, Any]]] = None) -> str:
    """Build system prompt with static samples and optional dynamic context."""
    prompt = BASE_SYSTEM_PROMPT
    prompt = prompt.replace("__SAMPLE_TASK_DEFINITION__", json.dumps(SAMPLE_TASK_DEFINITION, indent=2))
    prompt = prompt.replace("__SAMPLE_BATCH_EXECUTOR__", json.dumps(SAMPLE_BATCH_EXECUTOR, indent=2))
    prompt = prompt.replace("__SAMPLE_WORKFLOW__", json.dumps(SAMPLE_WORKFLOW, indent=2))

    if not context_artifacts:
        return prompt

    context_chunks: List[str] = []
    for idx, artifact in enumerate(context_artifacts, 1):
        artifact_id = artifact.get("artifact_id", f"artifact-{idx}")
        name = artifact.get("name", "Unnamed")
        source_type = artifact.get("source_type", "unknown")
        source_ref = artifact.get("source_reference", "unknown")
        domain = artifact.get("domain", "generic")
        content = artifact.get("content", [])
        # Keep examples bounded to avoid prompt bloat even after selection.
        trimmed_content = content[:12] if isinstance(content, list) else []

        context_chunks.append(
            f"### Dynamic Context Example {idx}\n"
            f"- ArtifactId: {artifact_id}\n"
            f"- Name: {name}\n"
            f"- SourceType: {source_type}\n"
            f"- SourceReference: {source_ref}\n"
            f"- Domain: {domain}\n"
            f"- ExamplePayload:\n{json.dumps(trimmed_content, indent=2)}"
        )

    return (
        prompt
        + "\n\n## Additional User-Supplied Context\n"
        + "Use these examples when they are relevant to the requirement. "
        + "Do not copy Moids or tenant-specific identifiers.\n\n"
        + "\n\n".join(context_chunks)
    )


def _normalize_webapi_target_type(workflow_data: List[Dict]) -> Tuple[List[Dict], List[Dict[str, str]]]:
    """
    Normalize WebApi TargetType values to valid ICO enum values.

    The LLM may output semantic labels (e.g. "Intersight") or schema names
    (e.g. "workflow.TargetType"), which are invalid enum values.
    """
    valid_target_types = {"Endpoint", "Local"}
    changes: List[Dict[str, str]] = []

    def infer_target_type(url: str) -> str:
        # In this ICO schema, external HTTP URLs still use TargetType=Endpoint.
        return "Endpoint"

    for idx, item in enumerate(workflow_data):
        if not isinstance(item, dict):
            continue
        body = item.get("Body")
        if not isinstance(body, dict):
            continue
        component_name = body.get("Name", f"Component {idx}")
        batch_items = body.get("Batch", [])
        if not isinstance(batch_items, list):
            continue

        for batch_idx, batch_item in enumerate(batch_items):
            if not isinstance(batch_item, dict):
                continue
            if batch_item.get("ObjectType") != "workflow.WebApi":
                continue

            url = batch_item.get("Url", "")
            current_target = batch_item.get("TargetType", "")
            inferred = infer_target_type(url)

            needs_fix = False
            if not current_target:
                needs_fix = True
            elif isinstance(current_target, str) and current_target.startswith("workflow."):
                needs_fix = True
            elif current_target == "Intersight":
                needs_fix = True
            elif (
                isinstance(current_target, str)
                and current_target == "Local"
                and isinstance(url, str)
                and url.lower().startswith(("http://", "https://"))
            ):
                # Absolute URLs should be treated as Endpoint for this ICO schema.
                needs_fix = True
            elif current_target not in valid_target_types:
                needs_fix = True

            if needs_fix:
                batch_item["TargetType"] = inferred
                changes.append(
                    {
                        "component": component_name,
                        "batch_name": batch_item.get("Name", f"Batch{batch_idx}"),
                        "from": str(current_target) if current_target else "<missing>",
                        "to": inferred,
                    }
                )

    return workflow_data, changes


def _normalize_webapi_request_shape(workflow_data: List[Dict]) -> Tuple[List[Dict], List[Dict[str, str]]]:
    """
    Normalize WebApi request fields into a shape that imports reliably.

    The LLM sometimes places URL/method metadata inside WebApi Body for GET calls.
    ICO WebApi expects URL and Method at the top level of each batch item, with
    an empty Body for GET requests.
    """
    changes: List[Dict[str, str]] = []

    for idx, item in enumerate(workflow_data):
        if not isinstance(item, dict):
            continue
        body = item.get("Body")
        if not isinstance(body, dict):
            continue
        component_name = body.get("Name", f"Component {idx}")
        batch_items = body.get("Batch", [])
        if not isinstance(batch_items, list):
            continue

        for batch_idx, batch_item in enumerate(batch_items):
            if not isinstance(batch_item, dict) or batch_item.get("ObjectType") != "workflow.WebApi":
                continue

            batch_name = batch_item.get("Name", f"Batch{batch_idx}")
            method = str(batch_item.get("Method", "")).upper()
            raw_body = batch_item.get("Body", "")

            if isinstance(raw_body, str) and raw_body.strip():
                try:
                    parsed_body = json.loads(raw_body)
                except Exception:
                    parsed_body = None
                if isinstance(parsed_body, dict):
                    # If Body contains request metadata, lift URL up and clear Body for GET.
                    embedded_url = parsed_body.get("url")
                    if isinstance(embedded_url, str) and embedded_url.strip():
                        if batch_item.get("Url") != embedded_url:
                            batch_item["Url"] = embedded_url
                            changes.append(
                                {
                                    "component": component_name,
                                    "batch_name": batch_name,
                                    "field": "Url",
                                    "reason": "promoted from Body.url",
                                }
                            )
                    if method == "GET" and set(parsed_body.keys()).issubset({"url", "method", "headers", "params"}):
                        batch_item["Body"] = ""
                        changes.append(
                            {
                                "component": component_name,
                                "batch_name": batch_name,
                                "field": "Body",
                                "reason": "cleared metadata-only GET body",
                            }
                        )

            endpoint_request_type = str(batch_item.get("EndpointRequestType", "")).strip()
            url = str(batch_item.get("Url", "")).lower()
            if endpoint_request_type == "Local":
                batch_item["EndpointRequestType"] = "External" if url.startswith(("http://", "https://")) else "Internal"
                changes.append(
                    {
                        "component": component_name,
                        "batch_name": batch_name,
                        "field": "EndpointRequestType",
                        "reason": "normalized Local to External/Internal",
                    }
                )

    return workflow_data, changes


def _validate_ico_compatibility(workflow_data: List[Dict]) -> List[str]:
    """
    Validate that the workflow uses only supported ICO features.
    
    The LLM sometimes hallucinates ICO features that don't exist (like expression
    evaluators, template execution endpoints, or array types). This function
    detects these and returns a list of error messages.
    
    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []
    valid_protocols = {"https", "http", ""}
    valid_types = {"string", "integer", "boolean", "json", "enum", "float", "long"}
    valid_target_types = {"Endpoint", "Local"}
    invalid_url_patterns = ["template", "expression", "evaluator", "execute"]
    
    for idx, item in enumerate(workflow_data):
        if not isinstance(item, dict) or "Body" not in item:
            continue
        body = item.get("Body", {})
        if not isinstance(body, dict):
            continue
        
        obj_type = body.get("ObjectType", "")
        name = body.get("Name", f"Component {idx}")
        
        # Check BatchApiExecutor for invalid WebApi settings
        if "Batch" in body and isinstance(body["Batch"], list):
            for batch_item in body["Batch"]:
                if not isinstance(batch_item, dict):
                    continue
                protocol = batch_item.get("Protocol", "")
                url = batch_item.get("Url", "")
                target_type = batch_item.get("TargetType", "")
                endpoint_request_type = batch_item.get("EndpointRequestType", "")
                
                # Check for invalid protocol
                if protocol.lower() not in valid_protocols:
                    errors.append(
                        f"'{name}' uses unsupported Protocol '{protocol}'. "
                        f"ICO only supports 'https' or 'http' protocols for WebApi calls."
                    )
                
                # Check for hallucinated endpoints
                url_lower = url.lower()
                for pattern in invalid_url_patterns:
                    if pattern in url_lower:
                        errors.append(
                            f"'{name}' uses non-existent endpoint '{url}'. "
                            f"ICO does not have built-in expression evaluation or template execution endpoints."
                        )
                        break
                
                # Check for invalid TargetType
                if isinstance(target_type, str) and target_type.startswith("workflow."):
                    errors.append(
                        f"'{name}' uses invalid TargetType '{target_type}'. "
                        f"TargetType must be an enum value, not a schema type. "
                        f"Valid values are: Endpoint, Local."
                    )
                elif target_type == "Intersight":
                    errors.append(
                        f"'{name}' uses invalid TargetType 'Intersight'. "
                        f"Use a valid enum value: Endpoint or Local."
                    )
                elif target_type and target_type not in valid_target_types:
                    errors.append(
                        f"'{name}' uses unsupported TargetType '{target_type}'. "
                        f"ICO WebApi TargetType must be one of: Endpoint, Local."
                    )

                # EndpointRequestType "Local" has triggered import failures in
                # some ICO environments; prefer Internal/External.
                if endpoint_request_type == "Local":
                    errors.append(
                        f"'{name}' uses EndpointRequestType 'Local', which may not be supported. "
                        f"Use 'Internal' for relative URLs or 'External' for absolute URLs."
                    )
        
        # Check for invalid type syntax in InputDefinition/OutputDefinition
        for def_key in ["InputDefinition", "OutputDefinition"]:
            definitions = body.get(def_key, [])
            if not isinstance(definitions, list):
                continue
            for defn in definitions:
                if not isinstance(defn, dict):
                    continue
                props = defn.get("Properties", {})
                if not isinstance(props, dict):
                    continue
                type_val = props.get("Type", "")
                param_name = defn.get("Name", "unknown")
                
                # Check for array syntax which ICO doesn't support in this format
                if "[" in str(type_val) or "]" in str(type_val):
                    errors.append(
                        f"'{name}' parameter '{param_name}' uses unsupported type '{type_val}'. "
                        f"ICO PrimitiveDataType supports: string, integer, boolean, json, enum."
                    )
                # Check for completely invalid types
                elif type_val.lower() not in valid_types and type_val:
                    errors.append(
                        f"'{name}' parameter '{param_name}' uses unknown type '{type_val}'. "
                        f"Valid types are: string, integer, boolean, json, enum."
                    )
    
    return errors


def _sanitize_labels(workflow_data: List[Dict]) -> List[Dict]:
    """
    Sanitize Label fields to match ICO's required pattern.
    
    ICO requires labels to match: ^[a-zA-Z0-9]+[\sa-zA-Z0-9_'.:/-]{1,92}$
    This means:
    - Must start with alphanumeric
    - Can contain: letters, numbers, space, underscore, apostrophe, period, colon, slash, hyphen
    - NOT allowed: parentheses, brackets, and other special characters
    """
    import re
    
    # Pattern for allowed characters (after the first alphanumeric)
    allowed_chars = re.compile(r"[^a-zA-Z0-9\s_'.:/\-]")
    
    def sanitize_label(label: str) -> str:
        if not label:
            return label
        # Remove disallowed characters
        sanitized = allowed_chars.sub("", label)
        # Ensure it starts with alphanumeric
        sanitized = sanitized.lstrip(" _'.:/-")
        # Ensure it's not empty and not too long
        if not sanitized:
            sanitized = "Label"
        if len(sanitized) > 93:
            sanitized = sanitized[:93]
        return sanitized
    
    def process_definitions(definitions: List) -> None:
        """Process InputDefinition or OutputDefinition lists."""
        if not isinstance(definitions, list):
            return
        for defn in definitions:
            if isinstance(defn, dict) and "Label" in defn:
                original = defn["Label"]
                sanitized = sanitize_label(original)
                if original != sanitized:
                    defn["Label"] = sanitized
    
    for item in workflow_data:
        if not isinstance(item, dict) or "Body" not in item:
            continue
        body = item.get("Body", {})
        if not isinstance(body, dict):
            continue
        
        # Sanitize Label at body level
        if "Label" in body:
            body["Label"] = sanitize_label(body["Label"])
        
        # Sanitize InputDefinition and OutputDefinition labels
        process_definitions(body.get("InputDefinition", []))
        process_definitions(body.get("OutputDefinition", []))
        
        # Also check Properties for nested definitions
        props = body.get("Properties", {})
        if isinstance(props, dict):
            process_definitions(props.get("InputDefinition", []))
            process_definitions(props.get("OutputDefinition", []))
        
        # Sanitize labels in Batch items
        if "Batch" in body and isinstance(body["Batch"], list):
            for batch_item in body["Batch"]:
                if isinstance(batch_item, dict) and "Label" in batch_item:
                    batch_item["Label"] = sanitize_label(batch_item["Label"])
        
        # Sanitize labels in Tasks
        if "Tasks" in body and isinstance(body["Tasks"], list):
            for task in body["Tasks"]:
                if isinstance(task, dict) and "Label" in task:
                    task["Label"] = sanitize_label(task["Label"])
    
    return workflow_data


def _fix_template_escaping(workflow_data: List[Dict]) -> List[Dict]:
    """
    Fix LLM's incorrect escaping in Go template expressions.
    
    The LLM often generates \" (backslash-quote) inside Go template conditionals like:
        {{if eq .global.task.input.var \"value\"}}
    
    But Go templates expect plain quotes:
        {{if eq .global.task.input.var "value"}}
    
    This function corrects that escaping in all Body strings that contain Go templates.
    """
    import re
    
    def fix_body_string(body_str: str) -> str:
        """Fix escaping in a single Body string."""
        if not isinstance(body_str, str):
            return body_str
        
        # Pattern to find Go template expressions with escaped quotes
        # Match {{if eq/ne ... \"value\"}} and similar patterns
        # Replace \" with " inside template expressions {{ ... }}
        
        def fix_template_expr(match):
            """Fix escaped quotes inside a single template expression."""
            expr = match.group(0)
            # Replace \" with " inside the template expression
            fixed = expr.replace('\\"', '"')
            return fixed
        
        # Match Go template expressions: {{ ... }}
        # This regex captures everything between {{ and }}
        pattern = r'\{\{[^}]+\}\}'
        fixed_body = re.sub(pattern, fix_template_expr, body_str)
        
        return fixed_body
    
    # Process all items in workflow_data
    for item in workflow_data:
        if not isinstance(item, dict):
            continue
        body = item.get("Body")
        if not isinstance(body, dict):
            continue
        
        # Check for BatchApiExecutor which has Batch array with WebApi items
        if "Batch" in body and isinstance(body["Batch"], list):
            for batch_item in body["Batch"]:
                if isinstance(batch_item, dict) and "Body" in batch_item:
                    original = batch_item["Body"]
                    if isinstance(original, str):
                        batch_item["Body"] = fix_body_string(original)
    
    return workflow_data


def generate_workflow_with_llm(
    jira_text: str,
    llm_client: CiscoLLMClient = None,
    context_artifacts: Optional[List[Dict[str, Any]]] = None,
    context_diagnostics: Optional[Dict[str, Any]] = None,
    debug_mode: bool = False,
    debug_max_payload_chars: int = 16000,
) -> Dict[str, Any]:
    """
    Generate a complete ICO workflow from JIRA text using GPT-4.1.
    
    This is the new pure-LLM approach where the LLM generates the entire
    workflow JSON based on sample examples.
    
    Args:
        jira_text: Raw JIRA ticket text describing the workflow requirements
        llm_client: Optional LLM client instance
        
    Returns:
        Dictionary with workflow, validation, and metadata
    """
    client = llm_client or get_llm_client()
    system_prompt = build_system_prompt(context_artifacts or [])
    started_at = time.time()
    debug_payload: Dict[str, Any] = {"enabled": debug_mode}
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""Generate a COMPLETE ICO workflow for the following requirements. You MUST generate ALL components in a single JSON response.

REQUIREMENTS:
{jira_text}

CRITICAL INSTRUCTIONS:
1. Generate a JSON object with key "requests" containing an array
2. The array MUST include ALL of these components:
   - ALL TaskDefinition objects needed (one for each task mentioned)
   - ALL BatchApiExecutor objects (one for each TaskDefinition)
   - ONE WorkflowDefinition that orchestrates all tasks
3. Do NOT generate just one component - generate the COMPLETE workflow
4. Follow the exact JSON structure from the samples provided

Output format: {{"requests": [<all bulk.RestSubRequest objects here>]}}"""}
    ]

    if debug_mode:
        debug_payload["request"] = {
            "llm_request_envelope": {
                "temperature": 0.2,
                "max_tokens": 16384,
                "response_format": {"type": "json_object"},
                "messages": messages,
            }
        }
        debug_payload["context"] = {
            "selected_context_count": len(context_artifacts or []),
            "selected_context_ids": [item.get("artifact_id") for item in (context_artifacts or [])],
            "diagnostics": context_diagnostics or {},
        }
    
    try:
        # Get completion with JSON format
        response = client.chat_completion(
            messages,
            temperature=0.2,
            max_tokens=16384,
            response_format={"type": "json_object"}
        )
        llm_elapsed_ms = int((time.time() - started_at) * 1000)
        if debug_mode:
            debug_payload["llm"] = {
                "latency_ms": llm_elapsed_ms,
                "response_keys": list(response.keys()) if isinstance(response, dict) else [],
                "choices_count": len(response.get("choices", [])) if isinstance(response, dict) else 0,
            }
        
        content = response["choices"][0]["message"]["content"]
        
        # Parse the response
        try:
            workflow_data = json.loads(content)
        except json.JSONDecodeError as e:
            result = {
                "success": False,
                "error": f"Failed to parse LLM response as JSON: {str(e)}",
                "raw_response": content[:1000],
                "workflow": [],
                "validation": {"valid": False, "errors": [str(e)], "warnings": [], "info": []}
            }
            if debug_mode:
                debug_payload["pipeline"] = {"stage": "parse_json", "error": str(e)}
                debug_payload["llm"]["raw_content_preview"] = content[:5000]
                redacted, notes = redact_sensitive(debug_payload)
                truncated, was_truncated = truncate_payload(redacted, debug_max_payload_chars)
                result["debug"] = {
                    "payload": truncated,
                    "redaction": {"redacted_fields": notes, "truncated": was_truncated},
                }
            return result
        
        # Handle wrapped responses
        if isinstance(workflow_data, dict):
            # LLM wraps in an object with a key like "requests"
            for key in ["requests", "workflow", "components", "bulk_requests", "data"]:
                if key in workflow_data:
                    workflow_data = workflow_data[key]
                    break
            else:
                # If it's a single object with Body, wrap in array
                if "Body" in workflow_data:
                    workflow_data = [workflow_data]
                # If it has any other structure, try to extract arrays
                elif any(isinstance(v, list) for v in workflow_data.values()):
                    for v in workflow_data.values():
                        if isinstance(v, list) and len(v) > 0:
                            workflow_data = v
                            break
        
        # Ensure it's a list
        if not isinstance(workflow_data, list):
            workflow_data = [workflow_data]
        
        # Filter to only valid dict items with Body
        workflow_data = [item for item in workflow_data if isinstance(item, dict) and "Body" in item]
        if debug_mode:
            debug_payload["pipeline"] = {
                "component_count_after_filter": len(workflow_data),
                "stages": ["parse_json", "normalize", "filter_body_components"],
            }

        # Normalize invalid WebApi TargetType values (e.g. "Intersight" -> "Endpoint")
        workflow_data, target_type_changes = _normalize_webapi_target_type(workflow_data)
        if debug_mode:
            debug_payload["pipeline"]["stages"].append("normalize_webapi_target_type")
            debug_payload["pipeline"]["target_type_normalization_changes"] = target_type_changes

        workflow_data, webapi_shape_changes = _normalize_webapi_request_shape(workflow_data)
        if debug_mode:
            debug_payload["pipeline"]["stages"].append("normalize_webapi_request_shape")
            debug_payload["pipeline"]["webapi_shape_changes"] = webapi_shape_changes
        
        # Fix: Post-process to correct LLM's double-escaping in Go template conditionals
        # The LLM incorrectly generates \" inside {{if eq ... "value"}} expressions
        # Go templates expect plain quotes, not escaped quotes
        workflow_data = _fix_template_escaping(workflow_data)
        if debug_mode:
            debug_payload["pipeline"]["stages"].append("fix_template_escaping")
        
        # Fix: Sanitize labels to match ICO's required pattern
        # Labels can only contain alphanumeric, space, underscore, apostrophe, period, colon, slash, hyphen
        workflow_data = _sanitize_labels(workflow_data)
        if debug_mode:
            debug_payload["pipeline"]["stages"].append("sanitize_labels")
        
        # Validate for unsupported ICO patterns that the LLM may hallucinate
        validation_errors = _validate_ico_compatibility(workflow_data)
        if validation_errors:
            result = {
                "success": False,
                "error": "The LLM generated a workflow with unsupported ICO features",
                "validation_errors": validation_errors,
                "hint": "ICO is designed for infrastructure orchestration (API calls to MDS switches, servers, etc.), "
                        "not general-purpose programming tasks. Try rephrasing your request to focus on "
                        "infrastructure operations like managing ports, VLANs, or device configurations.",
                "workflow": workflow_data,  # Include for debugging
                "validation": {"valid": False, "errors": validation_errors, "warnings": [], "info": []}
            }
            if debug_mode:
                debug_payload["pipeline"]["stages"].append("validate_ico_compatibility")
                debug_payload["pipeline"]["compatibility_errors"] = validation_errors
                redacted, notes = redact_sensitive(debug_payload)
                truncated, was_truncated = truncate_payload(redacted, debug_max_payload_chars)
                result["debug"] = {
                    "payload": truncated,
                    "redaction": {"redacted_fields": notes, "truncated": was_truncated},
                }
            return result
        
        if not workflow_data:
            result = {
                "success": False,
                "error": "LLM did not generate any valid workflow components",
                "raw_response": content[:1000] if content else None,
                "workflow": [],
                "validation": {"valid": False, "errors": ["No valid components generated"], "warnings": [], "info": []}
            }
            if debug_mode:
                debug_payload["pipeline"]["stages"].append("empty_workflow_guard")
                redacted, notes = redact_sensitive(debug_payload)
                truncated, was_truncated = truncate_payload(redacted, debug_max_payload_chars)
                result["debug"] = {
                    "payload": truncated,
                    "redaction": {"redacted_fields": notes, "truncated": was_truncated},
                }
            return result
        
        # Validate the generated workflow
        from app.validator import WorkflowValidator
        validator = WorkflowValidator()
        validation = validator.validate(workflow_data)
        
        # Generate Mermaid diagram
        mermaid = ""
        try:
            from app.generator import WorkflowGenerator
            gen = WorkflowGenerator()
            mermaid = gen.generate_mermaid(workflow_data)
        except Exception:
            pass  # Mermaid generation is optional
        
        # Extract analysis info from the generated workflow
        analysis = _extract_analysis_from_workflow(workflow_data, jira_text)
        
        result = {
            "success": True,
            "workflow": workflow_data,
            "mermaid": mermaid,
            "validation": validation,
            "analysis": analysis,
            "workflow_type": analysis.get("workflow_type", "custom"),
            "confidence": 0.9,  # LLM-generated workflows have high confidence
            "suggested_name": analysis.get("workflow_name"),
            "context_provenance": [
                {
                    "artifact_id": artifact.get("artifact_id"),
                    "name": artifact.get("name"),
                    "source_type": artifact.get("source_type"),
                    "source_reference": artifact.get("source_reference"),
                    "domain": artifact.get("domain"),
                    "token_estimate": artifact.get("token_estimate"),
                }
                for artifact in (context_artifacts or [])
            ],
            "context_diagnostics": context_diagnostics or {},
            "debug": None,
        }
        if debug_mode:
            debug_payload["pipeline"]["stages"].append("validator_validate")
            debug_payload["pipeline"]["validation"] = {
                "valid": validation.get("valid", False),
                "errors_count": len(validation.get("errors", [])),
                "warnings_count": len(validation.get("warnings", [])),
                "info_count": len(validation.get("info", [])),
            }
            debug_payload["pipeline"]["elapsed_ms_total"] = int((time.time() - started_at) * 1000)
            redacted, notes = redact_sensitive(debug_payload)
            truncated, was_truncated = truncate_payload(redacted, debug_max_payload_chars)
            result["debug"] = {
                "payload": truncated,
                "redaction": {"redacted_fields": notes, "truncated": was_truncated},
            }
        return result
        
    except Exception as e:
        import traceback
        result = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "workflow": [],
            "analysis": {},
            "validation": {"valid": False, "errors": [str(e)], "warnings": [], "info": []}
        }
        if debug_mode:
            debug_payload["pipeline"] = {"stage": "exception", "error": str(e)}
            redacted, notes = redact_sensitive(debug_payload)
            truncated, was_truncated = truncate_payload(redacted, debug_max_payload_chars)
            result["debug"] = {
                "payload": truncated,
                "redaction": {"redacted_fields": notes, "truncated": was_truncated},
            }
        return result


def _extract_analysis_from_workflow(workflow_data: List[Dict], jira_text: str) -> Dict[str, Any]:
    """Extract analysis info from generated workflow for display."""
    analysis = {
        "workflow_type": "custom",
        "confidence": 0.9,
        "reasoning": "Generated by LLM based on requirements",
        "warnings": [],
        "extracted_parameters": {},
        "workflow_name": None,
        "components": {
            "task_definitions": 0,
            "batch_executors": 0,
            "workflows": 0,
            "custom_types": 0
        }
    }
    
    for item in workflow_data:
        # Skip non-dict items
        if not isinstance(item, dict):
            continue
        body = item.get("Body", {})
        if not isinstance(body, dict):
            continue
        obj_type = body.get("ObjectType", "")
        
        if obj_type == "workflow.TaskDefinition":
            analysis["components"]["task_definitions"] += 1
        elif obj_type == "workflow.BatchApiExecutor":
            analysis["components"]["batch_executors"] += 1
        elif obj_type == "workflow.WorkflowDefinition":
            analysis["components"]["workflows"] += 1
            analysis["workflow_name"] = body.get("Label") or body.get("Name")
            # Extract workflow inputs as parameters
            for inp in body.get("InputDefinition", []):
                if isinstance(inp, dict):
                    name = inp.get("Name")
                    if name:
                        props = inp.get("Properties", {})
                        if not isinstance(props, dict):
                            props = {}
                        analysis["extracted_parameters"][name] = {
                            "label": inp.get("Label"),
                            "type": props.get("Type", "string"),
                            "required": inp.get("Required", False)
                        }
        elif obj_type == "workflow.CustomDataTypeDefinition":
            analysis["components"]["custom_types"] += 1
    
    return analysis


def analyze_jira_text(jira_text: str, llm_client: CiscoLLMClient = None) -> Dict[str, Any]:
    """
    Analyze JIRA ticket text to determine what workflow components are needed.
    
    This is a lightweight analysis that doesn't generate the full workflow.
    
    Args:
        jira_text: Raw JIRA ticket text
        llm_client: Optional LLM client instance
        
    Returns:
        Analysis result with workflow suggestions
    """
    client = llm_client or get_llm_client()
    
    analysis_prompt = """Analyze this JIRA ticket and determine what ICO workflow components are needed.

Return a JSON object with:
{
  "workflow_type": "string describing the type of automation",
  "confidence": 0.0-1.0,
  "suggested_workflow_name": "CamelCase name for the workflow",
  "required_tasks": ["list of task names that will be needed"],
  "required_inputs": [
    {"name": "input_name", "type": "string|integer|boolean|enum", "description": "what this input is for"}
  ],
  "mds_commands": ["list of MDS CLI commands that will be used"],
  "reasoning": "explanation of why these components are needed",
  "warnings": ["any potential issues or missing information"]
}"""
    
    messages = [
        {"role": "system", "content": analysis_prompt},
        {"role": "user", "content": jira_text}
    ]
    
    try:
        result = client.get_json_completion(messages, temperature=0.1)
        return result
    except Exception as e:
        return {
            "workflow_type": "error",
            "confidence": 0,
            "reasoning": f"Analysis failed: {str(e)}",
            "warnings": [str(e)]
        }


def generate_custom_workflow(
    requirements: str,
    llm_client: CiscoLLMClient = None
) -> Dict[str, Any]:
    """
    Generate a completely custom workflow using LLM.
    
    This is an alias for generate_workflow_with_llm for backward compatibility.
    
    Args:
        requirements: Detailed requirements for the workflow
        llm_client: Optional LLM client instance
        
    Returns:
        Generated workflow and metadata
    """
    return generate_workflow_with_llm(requirements, llm_client)
