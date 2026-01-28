"""
Template for toggling server locator LED.
Based on: Toggle_Locator_LED_Task.json and WF_to_set_the_Locator_LED.json
"""

from typing import Dict, Any, List
from app.models import create_bulk_request


def get_task_definitions() -> List[Dict[str, Any]]:
    """Get task definitions for locator LED control."""
    return [{
        "ClassId": "workflow.TaskDefinition",
        "DefaultVersion": True,
        "Description": "Toggles the locator LED on a physical server",
        "Label": "Toggle Server Locator LED",
        "Name": "ToggleServerLocatorLED",
        "ObjectType": "workflow.TaskDefinition",
        "Properties": {
            "ExternalMeta": False,
            "InputDefinition": [
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "Select the target server",
                    "DisplayMeta": {
                        "InventorySelector": True,
                        "ObjectType": "workflow.DisplayMeta",
                        "WidgetType": "None"
                    },
                    "Label": "Server",
                    "Name": "server_moid",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [{
                            "DisplayAttributes": ["Name", "Serial", "Model", "ManagementMode"],
                            "ObjectType": "workflow.MoReferenceProperty",
                            "Selector": "/api/v1/compute/PhysicalSummaries",
                            "SelectorProperty": {"Method": "GET", "ObjectType": "workflow.SelectorProperty"},
                            "ValueAttribute": "Moid"
                        }],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "string"
                    },
                    "Required": True
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue", "Override": True, "Value": "On"},
                    "Description": "Turn the locator LED on or off",
                    "DisplayMeta": {
                        "InventorySelector": False,
                        "ObjectType": "workflow.DisplayMeta",
                        "WidgetType": "Radio"
                    },
                    "Label": "LED State",
                    "Name": "led_state",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {
                            "EnumList": [
                                {"Label": "Turn On", "ObjectType": "workflow.EnumEntry", "Value": "On"},
                                {"Label": "Turn Off", "ObjectType": "workflow.EnumEntry", "Value": "Off"}
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
                    "Description": "The Moid of the LocatorLed that was updated",
                    "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "LocatorLed Moid",
                    "Name": "locator_led_moid",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "string"
                    }
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "The result of the LED operation",
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
                },
                {
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "Full API response from LED update",
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
            {"Key": "subcategory", "Value": "Operations"},
            {"Key": "author", "Value": "ico-generator"}
        ],
        "Version": 1
    }]


def get_batch_api_executors() -> List[Dict[str, Any]]:
    """Get batch API executor definitions."""
    return [{
        "Batch": [
            {
                "Body": "",
                "ContentType": "json",
                "Description": "Get server with LocatorLed relationship expanded",
                "Label": "Get Server With LocatorLed",
                "Method": "GET",
                "Name": "GetServerInfo",
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
                            "Name": "server_response",
                            "ObjectType": "content.Parameter",
                            "Path": "$",
                            "Secure": False,
                            "Type": "json"
                        },
                        {
                            "AcceptSingleValue": True,
                            "ComplexType": "",
                            "ItemType": "simple",
                            "Name": "led_moid",
                            "ObjectType": "content.Parameter",
                            "Path": "$.LocatorLed.Moid",
                            "Secure": False,
                            "Type": "string"
                        },
                        {
                            "AcceptSingleValue": True,
                            "ComplexType": "",
                            "ItemType": "simple",
                            "Name": "server_name",
                            "ObjectType": "content.Parameter",
                            "Path": "$.Name",
                            "Secure": False,
                            "Type": "string"
                        }
                    ],
                    "Types": []
                },
                "Url": "/api/v1/compute/PhysicalSummaries/{{.global.task.input.server_moid}}?$expand=LocatorLed"
            },
            {
                "Body": '{\n  "AdminState": "{{.global.task.input.led_state}}"\n}',
                "ContentType": "json",
                "Description": "Update the locator LED admin state",
                "Label": "Set Locator LED",
                "Method": "PATCH",
                "Name": "SetLocatorLED",
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
                            "Name": "led_response",
                            "ObjectType": "content.Parameter",
                            "Path": "$",
                            "Secure": False,
                            "Type": "json"
                        },
                        {
                            "AcceptSingleValue": True,
                            "ComplexType": "",
                            "ItemType": "simple",
                            "Name": "admin_state",
                            "ObjectType": "content.Parameter",
                            "Path": "$.AdminState",
                            "Secure": False,
                            "Type": "string"
                        },
                        {
                            "AcceptSingleValue": True,
                            "ComplexType": "",
                            "ItemType": "simple",
                            "Name": "oper_state",
                            "ObjectType": "content.Parameter",
                            "Path": "$.OperState",
                            "Secure": False,
                            "Type": "string"
                        }
                    ],
                    "Types": []
                },
                "Url": "/api/v1/equipment/LocatorLeds/{{.global.GetServerInfo.output.led_moid}}"
            }
        ],
        "CancelAction": [],
        "ClassId": "workflow.BatchApiExecutor",
        "Constraints": {"ObjectType": "workflow.TaskConstraints"},
        "Description": "Toggles the locator LED on a physical server",
        "Name": "Toggle Server Locator LED",
        "ObjectType": "workflow.BatchApiExecutor",
        "Output": {
            "locator_led_moid": "{{.global.GetServerInfo.output.led_moid}}",
            "result": "Server '{{.global.GetServerInfo.output.server_name}}': LED AdminState set to {{.global.SetLocatorLED.output.admin_state}}, OperState is {{.global.SetLocatorLED.output.oper_state}}",
            "response": "{{.global.SetLocatorLED.output.led_response}}"
        },
        "SharedScope": "user",
        "TaskDefinition": {
            "ObjectType": "workflow.TaskDefinition",
            "Selector": "Name eq 'ToggleServerLocatorLED' and Version eq 1"
        }
    }]


def get_workflow_definition(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get the workflow definition for controlling server locator LED."""
    return {
        "ClassId": "workflow.WorkflowDefinition",
        "DefaultVersion": True,
        "Description": "Workflow to control the locator LED on a physical server - useful for identifying servers in the datacenter",
        "InputDefinition": [
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Select the server whose locator LED you want to control",
                "DisplayMeta": {
                    "InventorySelector": True,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "Target Server",
                "Name": "target_server_moid",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [{
                        "DisplayAttributes": ["Name", "Serial", "Model", "ManagementMode", "OperPowerState"],
                        "ObjectType": "workflow.MoReferenceProperty",
                        "Selector": "/api/v1/compute/PhysicalSummaries",
                        "SelectorProperty": {"Method": "GET", "ObjectType": "workflow.SelectorProperty"},
                        "ValueAttribute": "Moid"
                    }],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "string"
                },
                "Required": True
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue", "Override": True, "Value": "On"},
                "Description": "Choose whether to turn the LED on or off",
                "DisplayMeta": {
                    "InventorySelector": False,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "Radio"
                },
                "Label": "Desired LED State",
                "Name": "desired_led_state",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {
                        "EnumList": [
                            {"Label": "Turn LED On", "ObjectType": "workflow.EnumEntry", "Value": "On"},
                            {"Label": "Turn LED Off", "ObjectType": "workflow.EnumEntry", "Value": "Off"}
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
        "Label": "Control Server Locator LED",
        "Name": "ControlServerLocatorLED",
        "ObjectType": "workflow.WorkflowDefinition",
        "OutputDefinition": [
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Summary of the LED operation",
                "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Operation Result",
                "Name": "operation_result",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "string"
                }
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "The Moid of the LocatorLed object that was modified",
                "DisplayMeta": {"InventorySelector": False, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "LocatorLed Moid",
                "Name": "led_moid",
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
            "operation_result": "${ToggleServerLocatorLEDTask.output.result}",
            "led_moid": "${ToggleServerLocatorLEDTask.output.locator_led_moid}"
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
            {"Key": "subcategory", "Value": "Operations"},
            {"Key": "usecase", "Value": "datacenter-operations"},
            {"Key": "author", "Value": "ico-generator"}
        ],
        "Tasks": [
            {"Name": "StartTask", "NextTask": "ToggleServerLocatorLEDTask", "ObjectType": "workflow.StartTask"},
            {"Name": "SuccessEndTask", "ObjectType": "workflow.SuccessEndTask"},
            {"Name": "FailureEndTask", "ObjectType": "workflow.FailureEndTask"},
            {
                "CatalogMoid": "user",
                "Description": "Toggles the locator LED on a physical server",
                "InputParameters": {
                    "server_moid": "${workflow.input.target_server_moid}",
                    "led_state": "${workflow.input.desired_led_state}"
                },
                "Label": "Toggle Server Locator LED",
                "Name": "ToggleServerLocatorLEDTask",
                "ObjectType": "workflow.WorkerTask",
                "OnSuccess": "SuccessEndTask",
                "OnFailure": "FailureEndTask",
                "TaskDefinitionName": "ToggleServerLocatorLED",
                "Version": 1
            }
        ],
        "UiInputFilters": [],
        "UiRenderingData": {
            "Positions": [
                {"Name": "StartTask", "X": 250, "Y": 100},
                {"Name": "ToggleServerLocatorLEDTask", "X": 250, "Y": 200},
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
    "name": "toggle_locator_led",
    "label": "Control Server Locator LED",
    "description": "Toggle the locator LED on a physical server for identification in the datacenter",
    "category": "Compute",
    "keywords": ["toggle", "led", "locator", "server", "identify", "blink", "light"],
    "parameters": []
}
