"""Route-level tests for context APIs and LLM generation endpoint."""

import io
import os


def test_context_upload_and_list(client):
    payload = b"""[
      {
        "ClassId": "bulk.RestSubRequest",
        "ObjectType": "bulk.RestSubRequest",
        "TargetMoid": "",
        "Uri": "/v1/workflow/TaskDefinitions",
        "Verb": "POST",
        "Body": {
          "ClassId": "workflow.TaskDefinition",
          "ObjectType": "workflow.TaskDefinition",
          "Name": "UploadedTask",
          "Label": "Uploaded Task",
          "Description": "From upload",
          "Properties": {"InputDefinition": [], "OutputDefinition": []}
        }
      }
    ]"""
    response = client.post(
        "/context/upload",
        data={"files": (io.BytesIO(payload), "uploaded.json")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["accepted"]) == 1

    listed = client.get("/context")
    assert listed.status_code == 200
    listed_payload = listed.get_json()
    assert len(listed_payload["artifacts"]) == 1


def test_generate_llm_uses_context_selection(client, monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "x")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "y")
    monkeypatch.setenv("CISCO_APPKEY", "z")

    # Seed one artifact directly through upload route.
    payload = b"""[
      {
        "ClassId": "bulk.RestSubRequest",
        "ObjectType": "bulk.RestSubRequest",
        "TargetMoid": "",
        "Uri": "/v1/workflow/TaskDefinitions",
        "Verb": "POST",
        "Body": {
          "ClassId": "workflow.TaskDefinition",
          "ObjectType": "workflow.TaskDefinition",
          "Name": "SeedTask",
          "Label": "Seed Task",
          "Description": "From upload",
          "Properties": {"InputDefinition": [], "OutputDefinition": []}
        }
      }
    ]"""
    upload = client.post(
        "/context/upload",
        data={"files": (io.BytesIO(payload), "seed.json")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200

    import app.routes as routes_module

    def fake_generate(
        jira_text,
        llm_client=None,
        context_artifacts=None,
        context_diagnostics=None,
        debug_mode=False,
        debug_max_payload_chars=16000,
    ):
        return {
            "success": True,
            "workflow": [],
            "mermaid": "",
            "validation": {"valid": True, "errors": [], "warnings": [], "info": []},
            "analysis": {"workflow_type": "test"},
            "context_provenance": context_artifacts or [],
            "context_diagnostics": context_diagnostics or {},
            "debug": {"payload": {"enabled": debug_mode}} if debug_mode else None,
        }

    # Patch underlying function used by route.
    import app.llm_generator as llm_generator_module
    monkeypatch.setattr(llm_generator_module, "generate_workflow_with_llm", fake_generate)

    response = client.post(
        "/generate/llm",
        json={"jira_text": "Create MDS workflow", "context_ids": []},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "context_diagnostics" in body


def test_debug_not_returned_when_capability_disabled(client, monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "x")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "y")
    monkeypatch.setenv("CISCO_APPKEY", "z")

    def fake_generate(jira_text, **kwargs):
        return {
            "success": True,
            "workflow": [],
            "mermaid": "",
            "validation": {"valid": True, "errors": [], "warnings": [], "info": []},
            "analysis": {"workflow_type": "test"},
            "context_provenance": [],
            "context_diagnostics": {},
            "debug": {"payload": {"enabled": True}},
        }

    import app.llm_generator as llm_generator_module
    monkeypatch.setattr(llm_generator_module, "generate_workflow_with_llm", fake_generate)

    response = client.post("/generate/llm", json={"jira_text": "Create task", "debug": True})
    assert response.status_code == 200
    body = response.get_json()
    # Route will not request debug from generator when capability is disabled.
    assert body.get("debug") is None


def test_debug_returned_when_enabled_and_requested(app, client, monkeypatch):
    app.config["DEBUG_MODE_ENABLED"] = True
    monkeypatch.setenv("CISCO_CLIENT_ID", "x")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "y")
    monkeypatch.setenv("CISCO_APPKEY", "z")

    def fake_generate(
        jira_text,
        llm_client=None,
        context_artifacts=None,
        context_diagnostics=None,
        debug_mode=False,
        debug_max_payload_chars=16000,
    ):
        return {
            "success": True,
            "workflow": [],
            "mermaid": "",
            "validation": {"valid": True, "errors": [], "warnings": [], "info": []},
            "analysis": {"workflow_type": "test"},
            "context_provenance": [],
            "context_diagnostics": {},
            "debug": {"payload": {"enabled": debug_mode, "cap": debug_max_payload_chars}},
        }

    import app.llm_generator as llm_generator_module
    monkeypatch.setattr(llm_generator_module, "generate_workflow_with_llm", fake_generate)

    response = client.post("/generate/llm", json={"jira_text": "Create task", "debug": True})
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("debug") is not None
    assert body["debug"]["payload"]["enabled"] is True

