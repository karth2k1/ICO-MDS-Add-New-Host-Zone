"""Models and factory functions for Intersight workflow entities."""

from typing import Any, Dict, List, Optional


# ============================================================================
# Factory Functions for Building Workflow Components
# ============================================================================

def create_primitive_input(
    name: str,
    label: str,
    data_type: str = "string",
    required: bool = False,
    description: str = "",
    default_value: Any = None,
    enum_list: List[Dict[str, str]] = None,
    widget_type: str = "None",
    constraints: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a primitive input definition."""
    input_def = {
        "Default": {
            "ObjectType": "workflow.DefaultValue"
        },
        "Description": description,
        "DisplayMeta": {
            "InventorySelector": False,
            "ObjectType": "workflow.DisplayMeta",
            "WidgetType": widget_type
        },
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.PrimitiveDataType",
        "Properties": {
            "Constraints": {
                "EnumList": enum_list or [],
                "ObjectType": "workflow.Constraints"
            },
            "InventorySelector": [],
            "ObjectType": "workflow.PrimitiveDataProperty",
            "Type": data_type
        },
        "Required": required
    }
    
    if default_value is not None:
        input_def["Default"]["Override"] = True
        input_def["Default"]["Value"] = default_value
    
    if constraints:
        input_def["Properties"]["Constraints"].update(constraints)
    
    return input_def


def create_target_input(
    name: str,
    label: str,
    custom_type_name: str,
    catalog_moid: str = "shared",
    required: bool = True,
    description: str = ""
) -> Dict[str, Any]:
    """Create a target data type input definition."""
    return {
        "CustomDataTypeProperties": {
            "CatalogMoid": catalog_moid,
            "CustomDataTypeName": custom_type_name,
            "ObjectType": "workflow.CustomDataProperty"
        },
        "Default": {
            "ObjectType": "workflow.DefaultValue"
        },
        "Description": description,
        "DisplayMeta": {
            "InventorySelector": True,
            "ObjectType": "workflow.DisplayMeta",
            "WidgetType": "None"
        },
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.TargetDataType",
        "Properties": [],
        "Required": required
    }


def create_custom_input(
    name: str,
    label: str,
    custom_type_name: str,
    catalog_moid: str = "shared",
    required: bool = True,
    description: str = ""
) -> Dict[str, Any]:
    """Create a custom data type input definition."""
    return {
        "Default": {
            "ObjectType": "workflow.DefaultValue"
        },
        "Description": description,
        "DisplayMeta": {
            "InventorySelector": True,
            "ObjectType": "workflow.DisplayMeta",
            "WidgetType": "None"
        },
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.CustomDataType",
        "Properties": {
            "CatalogMoid": catalog_moid,
            "CustomDataTypeName": custom_type_name,
            "ObjectType": "workflow.CustomDataProperty"
        },
        "Required": required
    }


def create_output_definition(
    name: str,
    label: str,
    data_type: str = "json",
    description: str = ""
) -> Dict[str, Any]:
    """Create an output definition."""
    return {
        "Default": {
            "ObjectType": "workflow.DefaultValue"
        },
        "Description": description,
        "DisplayMeta": {
            "InventorySelector": False,
            "ObjectType": "workflow.DisplayMeta",
            "WidgetType": "None"
        },
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.PrimitiveDataType",
        "Properties": {
            "Constraints": {
                "EnumList": [],
                "ObjectType": "workflow.Constraints"
            },
            "InventorySelector": [],
            "ObjectType": "workflow.PrimitiveDataProperty",
            "Type": data_type
        }
    }


def create_worker_task(
    name: str,
    label: str,
    task_definition_name: str,
    input_parameters: Dict[str, str],
    on_success: str,
    on_failure: str = "FailureEndTask",
    description: str = "",
    version: int = 1,
    catalog_moid: str = "user"
) -> Dict[str, Any]:
    """Create a worker task for a workflow."""
    return {
        "CatalogMoid": catalog_moid,
        "Description": description,
        "InputParameters": input_parameters,
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.WorkerTask",
        "OnSuccess": on_success,
        "OnFailure": on_failure,
        "TaskDefinitionName": task_definition_name,
        "Version": version
    }


def create_sub_workflow_task(
    name: str,
    label: str,
    workflow_name: str,
    input_parameters: Dict[str, str],
    on_success: str,
    on_failure: str = "FailureEndTask",
    description: str = "",
    version: int = 1,
    catalog_moid: str = "user"
) -> Dict[str, Any]:
    """Create a sub-workflow task for a workflow."""
    return {
        "CatalogMoid": catalog_moid,
        "Description": description,
        "InputParameters": input_parameters,
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.SubWorkflowTask",
        "OnSuccess": on_success,
        "OnFailure": on_failure,
        "Version": version,
        "WorkflowDefinitionName": workflow_name
    }


def create_decision_task(
    name: str,
    label: str,
    condition: str,
    decision_cases: List[Dict[str, Any]],
    default_task: str,
    description: str = ""
) -> Dict[str, Any]:
    """Create a decision task for conditional branching."""
    return {
        "Condition": condition,
        "DecisionCases": decision_cases,
        "DefaultTask": default_task,
        "Description": description,
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.DecisionTask"
    }


def create_decision_case(
    value: str,
    next_task: str,
    description: str = ""
) -> Dict[str, Any]:
    """Create a decision case."""
    return {
        "Description": description,
        "NextTask": next_task,
        "ObjectType": "workflow.DecisionCase",
        "Value": value
    }


def create_start_task(next_task: str) -> Dict[str, Any]:
    """Create a start task."""
    return {
        "Name": "StartTask",
        "NextTask": next_task,
        "ObjectType": "workflow.StartTask"
    }


def create_success_end_task() -> Dict[str, Any]:
    """Create a success end task."""
    return {
        "Name": "SuccessEndTask",
        "ObjectType": "workflow.SuccessEndTask"
    }


def create_failure_end_task() -> Dict[str, Any]:
    """Create a failure end task."""
    return {
        "Name": "FailureEndTask",
        "ObjectType": "workflow.FailureEndTask"
    }


def create_tag(key: str, value: str) -> Dict[str, str]:
    """Create a tag."""
    return {"Key": key, "Value": value}


def create_task_properties(
    input_definitions: List[Dict[str, Any]] = None,
    output_definitions: List[Dict[str, Any]] = None,
    external_meta: bool = False,
    timeout: int = 600,
    retry_count: int = 3,
    retry_delay: int = 60
) -> Dict[str, Any]:
    """Create task properties."""
    return {
        "ExternalMeta": external_meta,
        "InputDefinition": input_definitions or [],
        "ObjectType": "workflow.Properties",
        "OutputDefinition": output_definitions or [],
        "RetryCount": retry_count,
        "RetryDelay": retry_delay,
        "RetryPolicy": "Fixed",
        "SupportStatus": "Supported",
        "Timeout": timeout,
        "TimeoutPolicy": "Timeout"
    }


def create_task_definition(
    name: str,
    label: str,
    description: str,
    properties: Dict[str, Any],
    tags: List[Dict[str, str]] = None,
    rollback_tasks: List[Dict[str, Any]] = None,
    version: int = 1
) -> Dict[str, Any]:
    """Create a task definition."""
    return {
        "ClassId": "workflow.TaskDefinition",
        "DefaultVersion": True,
        "Description": description,
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.TaskDefinition",
        "Properties": properties,
        "RollbackTasks": rollback_tasks or [],
        "SharedScope": "user",
        "Tags": tags or [],
        "Version": version
    }


def create_workflow_properties(
    enable_debug: bool = True,
    external_meta: bool = False
) -> Dict[str, Any]:
    """Create workflow properties."""
    return {
        "EnableDebug": enable_debug,
        "ExternalMeta": external_meta,
        "ObjectType": "workflow.WorkflowProperties",
        "SupportStatus": "Supported"
    }


def create_ui_position(name: str, x: float, y: float) -> Dict[str, Any]:
    """Create a UI position for a task."""
    return {"Name": name, "X": x, "Y": y}


def create_workflow_definition(
    name: str,
    label: str,
    description: str,
    input_definitions: List[Dict[str, Any]],
    output_definitions: List[Dict[str, Any]],
    output_parameters: Dict[str, str],
    tasks: List[Dict[str, Any]],
    ui_positions: List[Dict[str, Any]],
    tags: List[Dict[str, str]] = None,
    version: int = 1
) -> Dict[str, Any]:
    """Create a workflow definition."""
    return {
        "ClassId": "workflow.WorkflowDefinition",
        "DefaultVersion": True,
        "Description": description,
        "InputDefinition": input_definitions,
        "InputParameterSet": [],
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.WorkflowDefinition",
        "OutputDefinition": output_definitions,
        "OutputParameters": output_parameters,
        "Properties": create_workflow_properties(),
        "SharedScope": "user",
        "Tags": tags or [],
        "Tasks": tasks,
        "UiInputFilters": [],
        "UiRenderingData": {"Positions": ui_positions},
        "VariableDefinition": [],
        "Version": version
    }


def create_web_api(
    name: str,
    label: str,
    method: str,
    url: str,
    body: str = "",
    description: str = "",
    response_parameters: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a Web API call definition."""
    return {
        "Body": body,
        "ContentType": "json",
        "Description": description,
        "Label": label,
        "Method": method,
        "Name": name,
        "ObjectType": "workflow.WebApi",
        "Outcomes": [],
        "ResponseSpec": {
            "ErrorParameters": [],
            "ObjectType": "content.Grammar",
            "Parameters": response_parameters or [],
            "Types": []
        },
        "Url": url
    }


def create_response_parameter(
    name: str,
    path: str,
    param_type: str = "json",
    accept_single_value: bool = False
) -> Dict[str, Any]:
    """Create a response parameter for parsing API responses."""
    return {
        "AcceptSingleValue": accept_single_value,
        "ComplexType": "",
        "ItemType": "simple",
        "Name": name,
        "ObjectType": "content.Parameter",
        "Path": path,
        "Secure": False,
        "Type": param_type
    }


def create_batch_api_executor(
    name: str,
    description: str,
    batch: List[Dict[str, Any]],
    output: Dict[str, str],
    task_selector: str
) -> Dict[str, Any]:
    """Create a batch API executor."""
    return {
        "Batch": batch,
        "CancelAction": [],
        "ClassId": "workflow.BatchApiExecutor",
        "Constraints": {"ObjectType": "workflow.TaskConstraints"},
        "Description": description,
        "Name": name,
        "ObjectType": "workflow.BatchApiExecutor",
        "Output": output,
        "SharedScope": "user",
        "TaskDefinition": {
            "ObjectType": "workflow.TaskDefinition",
            "Selector": task_selector
        }
    }


def create_custom_data_type_definition(
    name: str,
    label: str,
    type_definition: List[Dict[str, Any]],
    description: str = "",
    shared_scope: str = "user",
    tags: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create a custom data type definition."""
    return {
        "ClassId": "workflow.CustomDataTypeDefinition",
        "Description": description,
        "Label": label,
        "Name": name,
        "ObjectType": "workflow.CustomDataTypeDefinition",
        "ParameterSet": [],
        "Properties": {"ObjectType": "workflow.CustomDataTypeProperties"},
        "SharedScope": shared_scope,
        "Tags": tags or [],
        "TypeDefinition": type_definition
    }


def create_bulk_request(body: Dict[str, Any], uri: str) -> Dict[str, Any]:
    """Create a bulk REST sub-request for import."""
    return {
        "Body": body,
        "ClassId": "bulk.RestSubRequest",
        "ObjectType": "bulk.RestSubRequest",
        "TargetMoid": "",
        "Uri": uri,
        "Verb": "POST"
    }


# ============================================================================
# Constants for URIs
# ============================================================================

URI_TASK_DEFINITIONS = "/v1/workflow/TaskDefinitions"
URI_WORKFLOW_DEFINITIONS = "/v1/workflow/WorkflowDefinitions"
URI_BATCH_API_EXECUTORS = "/v1/workflow/BatchApiExecutors"
URI_CUSTOM_DATA_TYPE_DEFINITIONS = "/v1/workflow/CustomDataTypeDefinitions"
