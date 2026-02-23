"""Tests for OpenAPI-to-workflow generation."""

from app.openapi_generator import extract_operations, generate_workflow_from_openapi_spec, parse_openapi_spec


OPENAPI_SAMPLE = b"""
openapi: 3.0.0
info:
  title: Weather API
  version: 1.0.0
servers:
  - url: https://api.example.com
paths:
  /weather/{zip}:
    get:
      operationId: getWeather
      summary: Get weather
      parameters:
        - name: zip
          in: path
          required: true
          schema:
            type: string
        - name: units
          in: query
          required: false
          schema:
            type: string
    post:
      operationId: saveWeatherPref
      summary: Save preference
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
"""


def test_parse_openapi_spec_yaml():
    spec = parse_openapi_spec(OPENAPI_SAMPLE, "weather.yaml")
    assert spec["openapi"] == "3.0.0"
    assert "paths" in spec


def test_extract_operations():
    spec = parse_openapi_spec(OPENAPI_SAMPLE, "weather.yaml")
    ops = extract_operations(spec)
    assert len(ops) == 2
    assert {item["operation_id"] for item in ops} == {"getWeather", "saveWeatherPref"}


def test_generate_workflow_from_openapi_spec():
    spec = parse_openapi_spec(OPENAPI_SAMPLE, "weather.yaml")
    result = generate_workflow_from_openapi_spec(spec)
    assert result["success"] is True
    assert result["analysis"]["components"]["task_definitions"] == 2
    assert result["analysis"]["components"]["batch_executors"] == 2
    assert result["analysis"]["components"]["workflows"] == 1
    assert result["validation"]["valid"] is True

    # Ensure path parameters referenced in URL templates are defined as task inputs.
    task_defs = [
        item["Body"]
        for item in result["workflow"]
        if item.get("Body", {}).get("ObjectType") == "workflow.TaskDefinition"
    ]
    weather_task = next(item for item in task_defs if item.get("Name") == "GetweatherTask")
    input_names = {entry.get("Name") for entry in weather_task.get("Properties", {}).get("InputDefinition", [])}
    assert "zip" in input_names
