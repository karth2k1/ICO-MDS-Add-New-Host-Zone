"""
Template for saving MDS configuration.
Based on: MDS_Save_Configuration_Task_and_Workflow.json
"""

from typing import Dict, Any, List
from app.models import create_bulk_request


def get_task_definitions() -> List[Dict[str, Any]]:
    """Get task definitions for save configuration."""
    return [{
        "ClassId": "workflow.TaskDefinition",
        "DefaultVersion": True,
        "Description": "Saves the running configuration to startup configuration on an MDS switch",
        "Label": "Save MDS Configuration",
        "Name": "SaveMDSConfiguration",
        "ObjectType": "workflow.TaskDefinition",
        "Properties": {
            "ExternalMeta": True,
            "InputDefinition": [{
                "CustomDataTypeProperties": {
                    "CatalogMoid": "shared",
                    "CustomDataTypeName": "MDSTargetDataType",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "MDS target switch to save configuration on",
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "MDS Switch",
                "Name": "mds_switch",
                "ObjectType": "workflow.TargetDataType",
                "Properties": [],
                "Required": True
            }],
            "ObjectType": "workflow.Properties",
            "OutputDefinition": [
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "API response from save operation",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Response",
                    "Name": "response",
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
                    "Description": "Result message",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
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
            {"Key": "author", "Value": "ico-generator"},
            {"Key": "subcategory", "Value": "MDS"},
            {"Key": "category", "Value": "Networking"},
            {"Key": "feature", "Value": "Configuration-Management"}
        ],
        "Version": 1
    }]


def get_batch_api_executors() -> List[Dict[str, Any]]:
    """Get batch API executor definitions."""
    return [{
        "Batch": [{
            "Body": '{\n  "ins_api": {\n    "version": "1.2",\n    "type": "cli_conf",\n    "chunk": "0",\n    "sid": "1",\n    "input": "copy running-config startup-config",\n    "output_format": "json"\n  }\n}',
            "ContentType": "json",
            "Description": "Execute copy running-config startup-config on MDS switch",
            "EndpointRequestType": "Internal",
            "Label": "Save Running to Startup",
            "Method": "POST",
            "Name": "CopyRunningToStartup",
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
        }],
        "CancelAction": [],
        "ClassId": "workflow.BatchApiExecutor",
        "Constraints": {"ObjectType": "workflow.TaskConstraints"},
        "Description": "Saves the running configuration to startup configuration on an MDS switch",
        "Name": "Save MDS Configuration",
        "ObjectType": "workflow.BatchApiExecutor",
        "Output": {
            "response": "{{.global.CopyRunningToStartup.output.api_response}}",
            "result": "Configuration saved successfully. Running-config copied to startup-config."
        },
        "SharedScope": "user",
        "TaskDefinition": {
            "ObjectType": "workflow.TaskDefinition",
            "Selector": "Name eq 'SaveMDSConfiguration' and Version eq 1"
        }
    }]


def get_workflow_definition(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get the workflow definition for saving MDS configuration."""
    return {
        "ClassId": "workflow.WorkflowDefinition",
        "DefaultVersion": True,
        "Description": "Simple workflow to save MDS switch configuration. Copies running-config to startup-config.",
        "InputDefinition": [{
            "CustomDataTypeProperties": {
                "CatalogMoid": "shared",
                "CustomDataTypeName": "MDSTargetDataType",
                "ObjectType": "workflow.CustomDataProperty"
            },
            "Default": {"ObjectType": "workflow.DefaultValue"},
            "Description": "Select the MDS switch to save configuration on",
            "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
            "Label": "MDS Switch",
            "Name": "mds_switch",
            "ObjectType": "workflow.TargetDataType",
            "Properties": [],
            "Required": True
        }],
        "InputParameterSet": [],
        "Label": "Save MDS Switch Configuration",
        "Name": "SaveMDSSwitchConfiguration",
        "ObjectType": "workflow.WorkflowDefinition",
        "OutputDefinition": [{
            "Default": {"ObjectType": "workflow.DefaultValue"},
            "Description": "Result of the save operation",
            "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
            "Label": "Result",
            "Name": "result",
            "ObjectType": "workflow.PrimitiveDataType",
            "Properties": {
                "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                "InventorySelector": [],
                "ObjectType": "workflow.PrimitiveDataProperty",
                "Type": "string"
            }
        }],
        "OutputParameters": {
            "result": "${SaveConfigTask.output.result}"
        },
        "Properties": {
            "EnableDebug": True,
            "ExternalMeta": True,
            "ObjectType": "workflow.WorkflowProperties",
            "SupportStatus": "Supported"
        },
        "SharedScope": "user",
        "Tags": [
            {"Key": "author", "Value": "ico-generator"},
            {"Key": "subcategory", "Value": "MDS"},
            {"Key": "category", "Value": "Networking"},
            {"Key": "feature", "Value": "Configuration-Management"}
        ],
        "Tasks": [
            {"Name": "StartTask", "NextTask": "SaveConfigTask", "ObjectType": "workflow.StartTask"},
            {"Name": "SuccessEndTask", "ObjectType": "workflow.SuccessEndTask"},
            {"Name": "FailureEndTask", "ObjectType": "workflow.FailureEndTask"},
            {
                "CatalogMoid": "user",
                "Description": "Save the running configuration to startup configuration",
                "InputParameters": {"mds_switch": "${workflow.input.mds_switch}"},
                "Label": "Save Configuration",
                "Name": "SaveConfigTask",
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
                {"Name": "StartTask", "X": 300, "Y": 100},
                {"Name": "SaveConfigTask", "X": 300, "Y": 200},
                {"Name": "SuccessEndTask", "X": 300, "Y": 300},
                {"Name": "FailureEndTask", "X": 450, "Y": 300}
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
    "name": "save_mds_config",
    "label": "Save MDS Configuration",
    "description": "Save running configuration to startup configuration on an MDS switch",
    "category": "MDS",
    "keywords": ["save", "config", "running", "startup", "persist", "mds"],
    "parameters": []
}
