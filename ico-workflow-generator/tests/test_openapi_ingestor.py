"""Tests for OpenAPI ingestor parsing and extraction."""

from app.context_ingestors.openapi_ingestor import OpenAPIIngestor


OPENAPI_SPEC = b"""
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


def test_openapi_ingestor_parse_spec():
    ingestor = OpenAPIIngestor()
    spec = ingestor.parse_spec(OPENAPI_SPEC, "demo.yaml")
    assert spec["openapi"] == "3.0.0"
    assert "paths" in spec


def test_openapi_ingestor_extract_operations():
    ingestor = OpenAPIIngestor()
    spec = ingestor.parse_spec(OPENAPI_SPEC, "demo.yaml")
    operations = ingestor.extract_operations(spec)
    assert len(operations) == 1
    assert operations[0]["operation_id"] == "listPets"
    assert operations[0]["method"] == "GET"
