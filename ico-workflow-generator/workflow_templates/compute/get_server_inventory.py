"""
Template for getting server inventory.
Based on: GetServerInventory_task.json
"""

from typing import Dict, Any, List
from app.models import create_bulk_request


def get_task_definitions() -> List[Dict[str, Any]]:
    """Get task definitions for server inventory."""
    return [{
        "ClassId": "workflow.TaskDefinition",
        "DefaultVersion": True,
        "Description": "Retrieves a list of all physical compute servers managed by Intersight",
        "Label": "Get Server Inventory",
        "Name": "GetServerInventory",
        "ObjectType": "workflow.TaskDefinition",
        "Properties": {
            "ExternalMeta": False,
            "InputDefinition": [
                {
                    "Default": {"ObjectType": "workflow.DefaultValue", "Override": True, "Value": 100},
                    "Description": "Maximum number of servers to return",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Top Results",
                    "Name": "top",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "Max": 1000, "Min": 1, "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "integer"
                    },
                    "Required": False
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue", "Override": True, "Value": ""},
                    "Description": "Optional OData filter (e.g., ManagementMode eq 'Intersight')",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Filter",
                    "Name": "filter",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "string"
                    },
                    "Required": False
                }
            ],
            "ObjectType": "workflow.Properties",
            "OutputDefinition": [
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "Total number of servers found",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Server Count",
                    "Name": "server_count",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "integer"
                    }
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "List of all server details",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Servers",
                    "Name": "servers",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "json"
                    }
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "Complete API response",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Full Response",
                    "Name": "full_response",
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
            "RetryDelay": 10,
            "RetryPolicy": "Fixed",
            "SupportStatus": "Supported",
            "Timeout": 300,
            "TimeoutPolicy": "Timeout"
        },
        "RollbackTasks": [],
        "SharedScope": "user",
        "Tags": [
            {"Key": "category", "Value": "Compute"},
            {"Key": "subcategory", "Value": "Inventory"},
            {"Key": "author", "Value": "ico-generator"}
        ],
        "Version": 1
    }]


def get_batch_api_executors() -> List[Dict[str, Any]]:
    """Get batch API executor definitions."""
    return [{
        "Batch": [{
            "Body": "",
            "ContentType": "json",
            "Description": "Retrieve compute physical summaries from Intersight API",
            "Label": "Get Server List",
            "Method": "GET",
            "Name": "GetServers",
            "ObjectType": "workflow.WebApi",
            "Outcomes": [],
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
                    },
                    {
                        "AcceptSingleValue": False,
                        "ComplexType": "",
                        "ItemType": "simple",
                        "Name": "server_list",
                        "ObjectType": "content.Parameter",
                        "Path": "$.Results",
                        "Secure": False,
                        "Type": "json"
                    },
                    {
                        "AcceptSingleValue": True,
                        "ComplexType": "",
                        "ItemType": "simple",
                        "Name": "count",
                        "ObjectType": "content.Parameter",
                        "Path": "$.Count",
                        "Secure": False,
                        "Type": "integer"
                    }
                ],
                "Types": []
            },
            "Url": "/api/v1/compute/PhysicalSummaries?$top={{.global.task.input.top}}{{if .global.task.input.filter}}&$filter={{.global.task.input.filter}}{{end}}"
        }],
        "CancelAction": [],
        "ClassId": "workflow.BatchApiExecutor",
        "Constraints": {"ObjectType": "workflow.TaskConstraints"},
        "Description": "Retrieves a list of all physical compute servers managed by Intersight",
        "Name": "Get Server Inventory",
        "ObjectType": "workflow.BatchApiExecutor",
        "Output": {
            "server_count": "{{.global.GetServers.output.count}}",
            "servers": "{{.global.GetServers.output.server_list}}",
            "full_response": "{{.global.GetServers.output.api_response}}"
        },
        "SharedScope": "user",
        "TaskDefinition": {
            "ObjectType": "workflow.TaskDefinition",
            "Selector": "Name eq 'GetServerInventory' and Version eq 1"
        }
    }]


def get_workflow_definition(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get the workflow definition for getting server inventory."""
    return {
        "ClassId": "workflow.WorkflowDefinition",
        "DefaultVersion": True,
        "Description": "Retrieves a list of all physical compute servers managed by Intersight",
        "InputDefinition": [
            {
                "Default": {"ObjectType": "workflow.DefaultValue", "Override": True, "Value": 100},
                "Description": "Maximum number of servers to return",
                "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Max Results",
                "Name": "max_results",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "Max": 1000, "Min": 1, "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "integer"
                },
                "Required": False
            }
        ],
        "InputParameterSet": [],
        "Label": "Get Server Inventory",
        "Name": "GetServerInventoryWorkflow",
        "ObjectType": "workflow.WorkflowDefinition",
        "OutputDefinition": [
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Number of servers found",
                "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Server Count",
                "Name": "server_count",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "integer"
                }
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "List of servers",
                "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Servers",
                "Name": "servers",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "json"
                }
            }
        ],
        "OutputParameters": {
            "server_count": "${GetInventoryTask.output.server_count}",
            "servers": "${GetInventoryTask.output.servers}"
        },
        "Properties": {
            "EnableDebug": True,
            "ExternalMeta": False,
            "ObjectType": "workflow.WorkflowProperties",
            "SupportStatus": "Supported"
        },
        "SharedScope": "user",
        "Tags": [
            {"Key": "category", "Value": "Compute"},
            {"Key": "subcategory", "Value": "Inventory"},
            {"Key": "author", "Value": "ico-generator"}
        ],
        "Tasks": [
            {"Name": "StartTask", "NextTask": "GetInventoryTask", "ObjectType": "workflow.StartTask"},
            {"Name": "SuccessEndTask", "ObjectType": "workflow.SuccessEndTask"},
            {"Name": "FailureEndTask", "ObjectType": "workflow.FailureEndTask"},
            {
                "CatalogMoid": "user",
                "Description": "Get server inventory from Intersight",
                "InputParameters": {
                    "top": "${workflow.input.max_results}",
                    "filter": ""
                },
                "Label": "Get Server Inventory",
                "Name": "GetInventoryTask",
                "ObjectType": "workflow.WorkerTask",
                "OnSuccess": "SuccessEndTask",
                "OnFailure": "FailureEndTask",
                "TaskDefinitionName": "GetServerInventory",
                "Version": 1
            }
        ],
        "UiInputFilters": [],
        "UiRenderingData": {
            "Positions": [
                {"Name": "StartTask", "X": 250, "Y": 100},
                {"Name": "GetInventoryTask", "X": 250, "Y": 200},
                {"Name": "SuccessEndTask", "X": 250, "Y": 300},
                {"Name": "FailureEndTask", "X": 400, "Y": 300}
            ]
        },
        "VariableDefinition": [],
        "Version": 1
    }


def generate_full_workflow(params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Generate the complete workflow including all dependencies."""
    result = []
    
    # Add task definitions
    for task in get_task_definitions():
        result.append(create_bulk_request(task, "/v1/workflow/TaskDefinitions"))
    
    # Add batch API executors
    for executor in get_batch_api_executors():
        result.append(create_bulk_request(executor, "/v1/workflow/BatchApiExecutors"))
    
    # Add the main workflow
    workflow = get_workflow_definition(params)
    result.append(create_bulk_request(workflow, "/v1/workflow/WorkflowDefinitions"))
    
    return result


# Template metadata for rule engine
TEMPLATE_METADATA = {
    "name": "get_server_inventory",
    "label": "Get Server Inventory",
    "description": "Retrieve a list of all physical compute servers managed by Intersight",
    "category": "Compute",
    "keywords": ["inventory", "server", "list", "compute", "get", "query"],
    "parameters": [
        {"name": "max_results", "type": "integer", "required": False, "default": 100, "description": "Maximum servers to return"}
    ]
}
