"""Tests for LLM prompt assembly and generation envelope."""

import json

from app.llm_generator import (
    _normalize_webapi_target_type,
    _validate_ico_compatibility,
    build_system_prompt,
    generate_workflow_with_llm,
)


class FakeLLMClient:
    """Simple fake client returning deterministic JSON payloads."""

    def chat_completion(self, messages, temperature, max_tokens, response_format):
        assert messages[0]["role"] == "system"
        assert "Additional User-Supplied Context" in messages[0]["content"]
        payload = {
            "requests": [
                {
                    "ClassId": "bulk.RestSubRequest",
                    "ObjectType": "bulk.RestSubRequest",
                    "TargetMoid": "",
                    "Uri": "/v1/workflow/TaskDefinitions",
                    "Verb": "POST",
                    "Body": {
                        "ClassId": "workflow.TaskDefinition",
                        "ObjectType": "workflow.TaskDefinition",
                        "Name": "DemoTask",
                        "Label": "Demo Task",
                        "Description": "Demo",
                        "Properties": {"InputDefinition": [], "OutputDefinition": []},
                    },
                }
            ]
        }
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def test_build_system_prompt_includes_dynamic_context():
    prompt = build_system_prompt(
        [
            {
                "artifact_id": "ctx_1",
                "name": "MyUpload",
                "source_type": "upload",
                "source_reference": "my.json",
                "domain": "mds",
                "content": [],
            }
        ]
    )
    assert "Dynamic Context Example 1" in prompt
    assert "MyUpload" in prompt


def test_generate_workflow_with_context_provenance():
    result = generate_workflow_with_llm(
        jira_text="Create a test task",
        llm_client=FakeLLMClient(),
        context_artifacts=[
            {
                "artifact_id": "ctx_1",
                "name": "MyUpload",
                "source_type": "upload",
                "source_reference": "my.json",
                "domain": "mds",
                "token_estimate": 100,
                "content": [],
            }
        ],
        context_diagnostics={"selected_count": 1},
    )
    assert result["success"] is True
    assert result["context_provenance"][0]["artifact_id"] == "ctx_1"
    assert result["context_diagnostics"]["selected_count"] == 1


def test_normalize_webapi_target_type_intersight_to_endpoint():
    workflow_data = [
        {
            "Body": {
                "Name": "GetServersExecutor",
                "Batch": [
                    {
                        "ObjectType": "workflow.WebApi",
                        "Name": "GetServerList",
                        "TargetType": "Intersight",
                        "Url": "/api/v1/compute/PhysicalSummaries",
                    }
                ],
            }
        }
    ]
    normalized, changes = _normalize_webapi_target_type(workflow_data)
    batch_item = normalized[0]["Body"]["Batch"][0]
    assert batch_item["TargetType"] == "Endpoint"
    assert changes and changes[0]["from"] == "Intersight"


def test_validate_ico_compatibility_rejects_invalid_targettype():
    workflow_data = [
        {
            "Body": {
                "Name": "InvalidTargetTypeExecutor",
                "Batch": [
                    {
                        "ObjectType": "workflow.WebApi",
                        "Name": "BadCall",
                        "TargetType": "workflow.TargetType",
                        "Url": "/v1/compute/PhysicalSummaries",
                        "Protocol": "https",
                    }
                ],
            }
        }
    ]
    errors = _validate_ico_compatibility(workflow_data)
    assert errors
    assert "invalid TargetType" in errors[0]


def test_normalize_webapi_target_type_external_becomes_endpoint():
    workflow_data = [
        {
            "Body": {
                "Name": "DogApiExecutor",
                "Batch": [
                    {
                        "ObjectType": "workflow.WebApi",
                        "Name": "GetDogImage",
                        "TargetType": "External",
                        "Url": "https://dog.ceo/api/breeds/image/random",
                    }
                ],
            }
        }
    ]
    normalized, changes = _normalize_webapi_target_type(workflow_data)
    assert normalized[0]["Body"]["Batch"][0]["TargetType"] == "Endpoint"
    assert changes and changes[0]["from"] == "External"

