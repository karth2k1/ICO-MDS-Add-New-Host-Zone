"""Tests for context artifact repository and selection."""

import json

from app.context_models import ContextArtifact
from app.context_store import ContextRepository, estimate_tokens, is_ico_bulk_request_array


SAMPLE_COMPONENT = {
    "ClassId": "bulk.RestSubRequest",
    "ObjectType": "bulk.RestSubRequest",
    "Uri": "/v1/workflow/TaskDefinitions",
    "Verb": "POST",
    "Body": {"ObjectType": "workflow.TaskDefinition", "Name": "TaskA"},
}


def test_ico_bulk_request_shape_check():
    assert is_ico_bulk_request_array([SAMPLE_COMPONENT])
    assert not is_ico_bulk_request_array({"requests": [SAMPLE_COMPONENT]})


def test_context_repository_upsert_and_select(tmp_path):
    store = ContextRepository(str(tmp_path / "context_artifacts.json"))
    artifact = ContextArtifact(
        artifact_id="ctx_1",
        name="MDS Sample",
        source_type="upload",
        source_reference="sample.json",
        domain="mds",
        content=[SAMPLE_COMPONENT],
        content_preview=json.dumps([SAMPLE_COMPONENT]),
        token_estimate=estimate_tokens(json.dumps([SAMPLE_COMPONENT])),
    )
    store.upsert_artifact(artifact)

    selected, diagnostics = store.select_for_prompt(
        jira_text="Create MDS VSAN workflow",
        selected_artifact_ids=None,
        available_budget_tokens=artifact.token_estimate + 5,
        max_artifacts=2,
    )
    assert len(selected) == 1
    assert selected[0].artifact_id == "ctx_1"
    assert diagnostics["selected_count"] == 1

