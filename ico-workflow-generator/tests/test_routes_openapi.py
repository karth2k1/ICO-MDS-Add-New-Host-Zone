"""Route tests for OpenAPI upload generation endpoint."""

import io


def test_generate_openapi_requires_file(client):
    response = client.post("/generate/openapi", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    body = response.get_json()
    assert "Missing OpenAPI file upload" in body["error"]


def test_generate_openapi_rejects_non_openapi_extension(client):
    payload = b'{"hello":"world"}'
    response = client.post(
        "/generate/openapi",
        data={"openapi_file": (io.BytesIO(payload), "not_openapi.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert "must be .json, .yaml, or .yml" in body["error"]


def test_generate_openapi_rejects_malformed_spec(client):
    payload = b"openapi: 3.0.0\ninfo:\n  title: broken\npaths: ["
    response = client.post(
        "/generate/openapi",
        data={"openapi_file": (io.BytesIO(payload), "broken.yaml")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert "Failed to parse OpenAPI file" in body["error"]


def test_generate_openapi_success(client):
    payload = b"""
openapi: 3.0.0
info:
  title: Demo API
  version: 1.0.0
paths:
  /pets:
    get:
      operationId: listPets
      summary: List pets
"""
    response = client.post(
        "/generate/openapi",
        data={"openapi_file": (io.BytesIO(payload), "demo.yaml")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["analysis"]["workflow_type"] == "openapi"
    assert len(body["workflow"]) >= 3
