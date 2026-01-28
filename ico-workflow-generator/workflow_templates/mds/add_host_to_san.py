"""
Template for adding a new host to SAN workflow.
Based on: Workflow_Example-AddNewHosttoSAN_11-23-2022.json
"""

from typing import Dict, Any, List
from app.models import create_bulk_request, create_worker_task, create_sub_workflow_task


def get_custom_data_types() -> List[Dict[str, Any]]:
    """Get custom data type definitions required for this workflow."""
    return [
        {
            "ClassId": "workflow.CustomDataTypeDefinition",
            "Description": "MDS target device",
            "Label": "MDS Target Datatype",
            "Name": "MDSTargetDataType",
            "ObjectType": "workflow.CustomDataTypeDefinition",
            "ParameterSet": [],
            "Properties": {"ObjectType": "workflow.CustomDataTypeProperties"},
            "SharedScope": "shared",
            "TypeDefinition": [{
                "CustomDataTypeProperties": {"ObjectType": "workflow.CustomDataProperty"},
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "MDS target device",
                "DisplayMeta": {
                    "InventorySelector": True,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "MDS SAN Switch",
                "Name": "MDSDevice",
                "ObjectType": "workflow.TargetDataType",
                "Properties": [{
                    "ConnectorAttribute": "RegisteredDevice.Moid",
                    "ConstraintAttributes": ["SwitchType"],
                    "DisplayAttributes": ["Name", "RegisteredDevice.DeviceIpAddress", "SwitchType", "Vendor"],
                    "ObjectType": "workflow.TargetProperty",
                    "Selector": "/api/v1/network/ElementSummaries?$expand=RegisteredDevice($select=DeviceIpAddress)&$filter=SwitchType in ('MDSDevice')",
                    "SelectorProperty": {"Method": "GET", "ObjectType": "workflow.SelectorProperty"}
                }],
                "Required": True
            }]
        },
        {
            "ClassId": "workflow.CustomDataTypeDefinition",
            "Description": "Type definition for VSAN Id",
            "Label": "VSAN ID Type",
            "Name": "VsanIdType",
            "ObjectType": "workflow.CustomDataTypeDefinition",
            "ParameterSet": [],
            "Properties": {"ObjectType": "workflow.CustomDataTypeProperties"},
            "SharedScope": "shared",
            "TypeDefinition": [{
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "DisplayMeta": {
                    "InventorySelector": True,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "VSAN ID",
                "Name": "VsanId",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "Max": 4093, "Min": 2, "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [{
                        "DisplayAttributes": ["VsanId", "Name", "RegisteredDevice.DeviceHostname", "RegisteredDevice.DeviceIpAddress"],
                        "ObjectType": "workflow.MoReferenceProperty",
                        "Selector": "/api/v1/fabric/VsanInventories?$expand=RegisteredDevice($select=DeviceHostname,DeviceIpAddress)&$orderby=VsanId",
                        "SelectorProperty": {"Method": "GET", "ObjectType": "workflow.SelectorProperty"},
                        "ValueAttribute": "VsanId"
                    }],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "integer"
                },
                "Required": True
            }]
        },
        {
            "ClassId": "workflow.CustomDataTypeDefinition",
            "Label": "Fibre Channel Device WWPN",
            "Name": "device_wwpn",
            "ObjectType": "workflow.CustomDataTypeDefinition",
            "ParameterSet": [],
            "Properties": {"ObjectType": "workflow.CustomDataTypeProperties"},
            "SharedScope": "user",
            "Tags": [{"Key": "author", "Value": "ico-generator"}],
            "TypeDefinition": [{
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "DisplayMeta": {
                    "InventorySelector": True,
                    "ObjectType": "workflow.DisplayMeta",
                    "WidgetType": "None"
                },
                "Label": "Fibre Channel Device WWPN",
                "Name": "device_wwpn",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {
                        "EnumList": [],
                        "ObjectType": "workflow.Constraints",
                        "Regex": "([0-9a-fA-F]{2}:){7}[0-9a-fA-F]{2}"
                    },
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "string"
                }
            }]
        }
    ]


def get_task_definitions() -> List[Dict[str, Any]]:
    """Get task definitions required for this workflow."""
    return [
        # Add MDS Device Alias Task
        {
            "ClassId": "workflow.TaskDefinition",
            "DefaultVersion": True,
            "Description": "Adds a new device alias to an MDS switch",
            "Label": "Add MDS Device Alias",
            "Name": "AddMDSDeviceAlias",
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
                        "Description": "MDS target switch to execute commands on",
                        "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                        "Label": "MDS Switch",
                        "Name": "mds_switch",
                        "ObjectType": "workflow.TargetDataType",
                        "Properties": [],
                        "Required": True
                    },
                    {
                        "Default": {"ObjectType": "workflow.DefaultValue"},
                        "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                        "Label": "Device Alias Name",
                        "Name": "device_alias_name",
                        "ObjectType": "workflow.PrimitiveDataType",
                        "Properties": {
                            "Constraints": {"EnumList": [], "Max": 64, "ObjectType": "workflow.Constraints"},
                            "InventorySelector": [],
                            "ObjectType": "workflow.PrimitiveDataProperty",
                            "Type": "string"
                        },
                        "Required": True
                    },
                    {
                        "Default": {"ObjectType": "workflow.DefaultValue"},
                        "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                        "Label": "Device WWPN",
                        "Name": "device_wwpn",
                        "ObjectType": "workflow.CustomDataType",
                        "Properties": {
                            "CatalogMoid": "user",
                            "CustomDataTypeName": "device_wwpn",
                            "ObjectType": "workflow.CustomDataProperty"
                        },
                        "Required": True
                    }
                ],
                "ObjectType": "workflow.Properties",
                "OutputDefinition": [{
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "The list of output parameters extracted from the response.",
                    "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Parameters",
                    "Name": "Parameters",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "json"
                    }
                }],
                "RetryCount": 3,
                "RetryDelay": 60,
                "RetryPolicy": "Fixed",
                "SupportStatus": "Supported",
                "Timeout": 600,
                "TimeoutPolicy": "Timeout"
            },
            "RollbackTasks": [{
                "CatalogMoid": "user",
                "Description": "Used for task rollback. Removes device alias from an MDS switch, commits device alias DB and saves config.",
                "InputParameters": {
                    "device_alias_name": "${task.input.device_alias_name}",
                    "mds_switch": "${task.input.mds_switch}"
                },
                "Name": "RemoveMDSDeviceAliasRollback",
                "ObjectType": "workflow.RollbackTask",
                "Version": 1
            }],
            "SharedScope": "user",
            "Tags": [
                {"Key": "author", "Value": "ico-generator"},
                {"Key": "subcategory", "Value": "MDS"},
                {"Key": "category", "Value": "Networking"}
            ],
            "Version": 1
        },
        # Commit MDS Zone Database Task
        {
            "ClassId": "workflow.TaskDefinition",
            "DefaultVersion": True,
            "Description": "Used to commit the MDS zone DB with enhanced zoning mode enabled",
            "Label": "Commit MDS Zone Database",
            "Name": "CommitMDSZoneDatabase",
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
                        "Description": "MDS target switch to execute commands on",
                        "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                        "Label": "MDS Switch",
                        "Name": "mds_switch",
                        "ObjectType": "workflow.TargetDataType",
                        "Properties": [],
                        "Required": True
                    },
                    {
                        "Default": {"ObjectType": "workflow.DefaultValue"},
                        "Description": "VSAN ID",
                        "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                        "Label": "VSAN ID",
                        "Name": "vsan_id",
                        "ObjectType": "workflow.CustomDataType",
                        "Properties": {
                            "CatalogMoid": "shared",
                            "CustomDataTypeName": "VsanIdType",
                            "ObjectType": "workflow.CustomDataProperty"
                        },
                        "Required": True
                    }
                ],
                "ObjectType": "workflow.Properties",
                "OutputDefinition": [{
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "The list of output parameters extracted from the response.",
                    "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Parameters",
                    "Name": "Parameters",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "json"
                    }
                }],
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
                {"Key": "category", "Value": "Networking"}
            ],
            "Version": 1
        },
        # Copy MDS Running to Startup Task
        {
            "ClassId": "workflow.TaskDefinition",
            "DefaultVersion": True,
            "Description": "Copy MDS running config to startup config",
            "Label": "Copy MDS Running to Startup",
            "Name": "CopyMDSRunningtoStartup",
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
                    "Description": "MDS target switch to execute commands on",
                    "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "MDS Switch",
                    "Name": "mds_switch",
                    "ObjectType": "workflow.TargetDataType",
                    "Properties": [],
                    "Required": True
                }],
                "ObjectType": "workflow.Properties",
                "OutputDefinition": [{
                    "Default": {"ObjectType": "workflow.DefaultValue"},
                    "Description": "The list of output parameters extracted from the response.",
                    "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                    "Label": "Parameters",
                    "Name": "Parameters",
                    "ObjectType": "workflow.PrimitiveDataType",
                    "Properties": {
                        "Constraints": {"EnumList": [], "ObjectType": "workflow.Constraints"},
                        "InventorySelector": [],
                        "ObjectType": "workflow.PrimitiveDataProperty",
                        "Type": "json"
                    }
                }],
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
                {"Key": "category", "Value": "Networking"}
            ],
            "Version": 1
        }
    ]


def get_batch_api_executors() -> List[Dict[str, Any]]:
    """Get batch API executor definitions."""
    return [
        # Add MDS Device Alias Executor
        {
            "Batch": [{
                "Body": '{\n  "ins_api": {\n    "version": "1.2",\n    "type": "cli_conf",\n    "chunk": "0",\n    "sid": "1",\n    "input": "device-alias database ; device-alias name {{.global.task.input.device_alias_name}} pwwn {{.global.task.input.device_wwpn}} ; device-alias commit",\n    "output_format": "json"\n  }\n}',
                "ContentType": "json",
                "Description": "Device Alias Name, Device WWPN",
                "EndpointRequestType": "Internal",
                "Label": "Add MDS Device Alias",
                "Method": "POST",
                "Name": "InvokeGenericWebApi1",
                "ObjectType": "workflow.WebApi",
                "Outcomes": [],
                "Protocol": "https",
                "ResponseSpec": {
                    "ErrorParameters": [],
                    "ObjectType": "content.Grammar",
                    "Parameters": [{
                        "AcceptSingleValue": False,
                        "ComplexType": "",
                        "ItemType": "simple",
                        "Name": "api_response",
                        "ObjectType": "content.Parameter",
                        "Path": "$",
                        "Secure": False,
                        "Type": "json"
                    }],
                    "Types": []
                },
                "TargetType": "Endpoint",
                "Url": "/ins"
            }],
            "CancelAction": [],
            "ClassId": "workflow.BatchApiExecutor",
            "Constraints": {"ObjectType": "workflow.TaskConstraints"},
            "Description": "Adds a new device alias to an MDS switch",
            "Name": "Add MDS Device Alias",
            "ObjectType": "workflow.BatchApiExecutor",
            "Output": {"Parameters": "{{.global.InvokeGenericWebApi1.output.api_response}}"},
            "SharedScope": "user",
            "TaskDefinition": {
                "ObjectType": "workflow.TaskDefinition",
                "Selector": "Name eq 'AddMDSDeviceAlias' and Version eq 1"
            }
        },
        # Commit MDS Zone Database Executor
        {
            "Batch": [{
                "Body": '{\n  "ins_api": {\n    "version": "1.2",\n    "type": "cli_conf",\n    "chunk": "0",\n    "sid": "1",\n    "input": "zone commit vsan {{.global.task.input.vsan_id}}",\n    "output_format": "json"\n  }\n}',
                "ContentType": "json",
                "Description": "Commit MDS zone DB [Enhanced Zoning Mode]",
                "EndpointRequestType": "Internal",
                "Label": "Commit MDS Zone Database",
                "Method": "POST",
                "Name": "InvokeGenericWebApi1",
                "ObjectType": "workflow.WebApi",
                "Outcomes": [],
                "Protocol": "https",
                "ResponseSpec": {
                    "ErrorParameters": [],
                    "ObjectType": "content.Grammar",
                    "Parameters": [{
                        "AcceptSingleValue": False,
                        "ComplexType": "",
                        "ItemType": "simple",
                        "Name": "api_response",
                        "ObjectType": "content.Parameter",
                        "Path": "$",
                        "Secure": False,
                        "Type": "json"
                    }],
                    "Types": []
                },
                "TargetType": "Endpoint",
                "Url": "/ins"
            }],
            "CancelAction": [],
            "ClassId": "workflow.BatchApiExecutor",
            "Constraints": {"ObjectType": "workflow.TaskConstraints"},
            "Description": "Used to commit the MDS zone DB with enhanced zoning mode enabled",
            "Name": "Commit MDS Zone Database",
            "ObjectType": "workflow.BatchApiExecutor",
            "Output": {"Parameters": "{{.global.InvokeGenericWebApi1.output.api_response}}"},
            "SharedScope": "user",
            "TaskDefinition": {
                "ObjectType": "workflow.TaskDefinition",
                "Selector": "Name eq 'CommitMDSZoneDatabase' and Version eq 1"
            }
        },
        # Copy MDS Running to Startup Executor
        {
            "Batch": [{
                "Body": '{\n  "ins_api": {\n    "version": "1.2",\n    "type": "cli_conf",\n    "chunk": "0",\n    "sid": "1",\n    "input": "copy running-config startup-config",\n    "output_format": "json"\n  }\n}',
                "ContentType": "json",
                "Description": "copy running-config startup-config",
                "EndpointRequestType": "Internal",
                "Label": "Copy MDS Running to Startup",
                "Method": "POST",
                "Name": "InvokeGenericWebApi1",
                "ObjectType": "workflow.WebApi",
                "Outcomes": [],
                "ResponseSpec": {
                    "ErrorParameters": [],
                    "ObjectType": "content.Grammar",
                    "Parameters": [{
                        "AcceptSingleValue": False,
                        "ComplexType": "",
                        "ItemType": "simple",
                        "Name": "api_response",
                        "ObjectType": "content.Parameter",
                        "Path": "$",
                        "Secure": False,
                        "Type": "json"
                    }],
                    "Types": []
                },
                "TargetType": "Endpoint",
                "Url": "/ins"
            }],
            "CancelAction": [],
            "ClassId": "workflow.BatchApiExecutor",
            "Constraints": {"ObjectType": "workflow.TaskConstraints"},
            "Description": "Copy MDS running config to startup config",
            "Name": "Copy MDS Running to Startup",
            "ObjectType": "workflow.BatchApiExecutor",
            "Output": {"Parameters": "{{.global.InvokeGenericWebApi1.output.api_response}}"},
            "SharedScope": "user",
            "TaskDefinition": {
                "ObjectType": "workflow.TaskDefinition",
                "Selector": "Name eq 'CopyMDSRunningtoStartup' and Version eq 1"
            }
        }
    ]


def get_workflow_definition(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get the main workflow definition for adding a host to SAN.
    
    Args:
        params: Optional parameters to customize the workflow:
            - zone_name: Name for the zone (default from input)
            - use_fabric_b: Whether to include Fabric B (default True)
    """
    params = params or {}
    use_fabric_b = params.get("use_fabric_b", True)
    
    # Base workflow for single fabric
    workflow = {
        "ClassId": "workflow.WorkflowDefinition",
        "DefaultVersion": True,
        "Description": "Adds new host zone [device alias] to active zoneset for MDS SAN Fabric.",
        "InputDefinition": [
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Enter Zone name for new host.",
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Zone Name",
                "Name": "zone_name",
                "ObjectType": "workflow.PrimitiveDataType",
                "Properties": {
                    "Constraints": {"EnumList": [], "Max": 56, "ObjectType": "workflow.Constraints"},
                    "InventorySelector": [],
                    "ObjectType": "workflow.PrimitiveDataProperty",
                    "Type": "string"
                },
                "Required": True
            },
            {
                "CustomDataTypeProperties": {
                    "CatalogMoid": "shared",
                    "CustomDataTypeName": "MDSTargetDataType",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "MDS Fabric A",
                "Name": "mds_fabric_A",
                "ObjectType": "workflow.TargetDataType",
                "Properties": [],
                "Required": True
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "VSAN Fabric A",
                "Name": "vsan_fabric_A",
                "ObjectType": "workflow.CustomDataType",
                "Properties": {
                    "CatalogMoid": "shared",
                    "CustomDataTypeName": "VsanIdType",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Required": True
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Enter WWPN for new host. A Device Alias will be created and used as zone membership.",
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Host WWPN Fabric A",
                "Name": "host_wwpn_fabric_A",
                "ObjectType": "workflow.CustomDataType",
                "Properties": {
                    "CatalogMoid": "user",
                    "CustomDataTypeName": "device_wwpn",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Required": True
            }
        ],
        "InputParameterSet": [],
        "Label": "Add New Host to SAN",
        "Name": "AddNewHostToSAN",
        "ObjectType": "workflow.WorkflowDefinition",
        "OutputDefinition": [],
        "Properties": {
            "EnableDebug": True,
            "ExternalMeta": True,
            "ObjectType": "workflow.WorkflowProperties",
            "SupportStatus": "Supported"
        },
        "SharedScope": "user",
        "Tags": [
            {"Key": "author", "Value": "ico-generator"},
            {"Key": "usecase", "Value": "san-provisioning"}
        ],
        "Tasks": [
            {"Name": "SuccessEndTask", "ObjectType": "workflow.SuccessEndTask"},
            {"Name": "FailureEndTask", "ObjectType": "workflow.FailureEndTask"},
            {"Name": "StartTask", "NextTask": "ZoneNewHostFabricA", "ObjectType": "workflow.StartTask"},
            {
                "CatalogMoid": "user",
                "Description": "Zone new host to MDS Fabric A",
                "InputParameters": {
                    "host_wwpn": "${workflow.input.host_wwpn_fabric_A}",
                    "mds_switch": "${workflow.input.mds_fabric_A}",
                    "vsan_id": "${workflow.input.vsan_fabric_A}",
                    "zone_name": "${workflow.input.zone_name}"
                },
                "Label": "Zone New Host to MDS Fabric A",
                "Name": "ZoneNewHostFabricA",
                "ObjectType": "workflow.SubWorkflowTask",
                "OnSuccess": "SuccessEndTask" if not use_fabric_b else "ZoneNewHostFabricB",
                "Version": 1,
                "WorkflowDefinitionName": "ZoneNewHostToMDS"
            }
        ],
        "UiInputFilters": [],
        "UiRenderingData": {
            "Positions": [
                {"Name": "StartTask", "X": 234.5, "Y": 160},
                {"Name": "SuccessEndTask", "X": 234.5, "Y": 435},
                {"Name": "FailureEndTask", "X": 377.5, "Y": 435},
                {"Name": "ZoneNewHostFabricA", "X": 149.5, "Y": 237}
            ]
        },
        "VariableDefinition": [],
        "Version": 1
    }
    
    # Add Fabric B inputs and tasks if needed
    if use_fabric_b:
        workflow["Description"] = "Adds new host zone [device alias] to active zoneset for MDS Fabric A and B."
        
        # Add Fabric B inputs
        workflow["InputDefinition"].extend([
            {
                "CustomDataTypeProperties": {
                    "CatalogMoid": "shared",
                    "CustomDataTypeName": "MDSTargetDataType",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "MDS Fabric B",
                "Name": "mds_fabric_B",
                "ObjectType": "workflow.TargetDataType",
                "Properties": [],
                "Required": True
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "VSAN Fabric B",
                "Name": "vsan_fabric_B",
                "ObjectType": "workflow.CustomDataType",
                "Properties": {
                    "CatalogMoid": "shared",
                    "CustomDataTypeName": "VsanIdType",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Required": True
            },
            {
                "Default": {"ObjectType": "workflow.DefaultValue"},
                "Description": "Enter WWPN for new host. A Device Alias will be created and used as zone membership.",
                "DisplayMeta": {"InventorySelector": True, "ObjectType": "workflow.DisplayMeta", "WidgetType": "None"},
                "Label": "Host WWPN Fabric B",
                "Name": "host_wwpn_fabric_B",
                "ObjectType": "workflow.CustomDataType",
                "Properties": {
                    "CatalogMoid": "user",
                    "CustomDataTypeName": "device_wwpn",
                    "ObjectType": "workflow.CustomDataProperty"
                },
                "Required": True
            }
        ])
        
        # Add Fabric B task
        workflow["Tasks"].append({
            "CatalogMoid": "user",
            "Description": "Zone new host to MDS Fabric B",
            "InputParameters": {
                "host_wwpn": "${workflow.input.host_wwpn_fabric_B}",
                "mds_switch": "${workflow.input.mds_fabric_B}",
                "vsan_id": "${workflow.input.vsan_fabric_B}",
                "zone_name": "${workflow.input.zone_name}"
            },
            "Label": "Zone New Host to MDS Fabric B",
            "Name": "ZoneNewHostFabricB",
            "ObjectType": "workflow.SubWorkflowTask",
            "OnSuccess": "SuccessEndTask",
            "Version": 1,
            "WorkflowDefinitionName": "ZoneNewHostToMDS"
        })
        
        # Update UI positions
        workflow["UiRenderingData"]["Positions"].append(
            {"Name": "ZoneNewHostFabricB", "X": 149.5, "Y": 336}
        )
    
    return workflow


def generate_full_workflow(params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Generate the complete workflow including all dependencies.
    
    Returns a list of bulk REST sub-requests ready for import.
    """
    result = []
    
    # Add custom data types
    for dt in get_custom_data_types():
        result.append(create_bulk_request(dt, "/v1/workflow/CustomDataTypeDefinitions"))
    
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
    "name": "add_host_to_san",
    "label": "Add New Host to SAN",
    "description": "Adds a new host to SAN fabric(s) by creating device alias, zone, and adding to active zoneset",
    "category": "MDS",
    "keywords": ["add", "host", "san", "zone", "fabric", "wwpn", "device alias", "zoneset"],
    "parameters": [
        {"name": "zone_name", "type": "string", "required": True, "description": "Zone name for the new host"},
        {"name": "use_fabric_b", "type": "boolean", "required": False, "default": True, "description": "Include Fabric B"}
    ]
}
