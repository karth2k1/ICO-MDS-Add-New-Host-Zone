"""Generate ICO workflow components from an OpenAPI spec upload."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from app.context_ingestors.openapi_ingestor import OpenAPIIngestor
from app.generator import WorkflowGenerator
from app.models import (
    URI_BATCH_API_EXECUTORS,
    URI_TASK_DEFINITIONS,
    URI_WORKFLOW_DEFINITIONS,
    create_batch_api_executor,
    create_bulk_request,
    create_failure_end_task,
    create_output_definition,
    create_primitive_input,
    create_response_parameter,
    create_start_task,
    create_success_end_task,
    create_task_definition,
    create_task_properties,
    create_web_api,
    create_workflow_definition,
    create_worker_task,
    create_ui_position,
)
from app.validator import WorkflowValidator


HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

OPENAPI_HARD_MAX_OPERATIONS = 200
OPENAPI_DEFAULT_MAX_OPERATIONS = 100
OPENAPI_SKIP_MERMAID_ABOVE_OPERATIONS = 50


def _to_identifier(value: str, fallback: str = "value") -> str:
    text = (value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"n_{text}"
    return text.lower()


def _to_pascal(value: str, fallback: str = "Operation") -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", value or "")
    words = [part.capitalize() for part in parts if part]
    return "".join(words) or fallback


def parse_openapi_spec(raw_bytes: bytes, filename: str = "openapi") -> Dict[str, Any]:
    """Backward-compatible helper that delegates to OpenAPI ingestor."""
    return OpenAPIIngestor().parse_spec(raw_bytes, filename)


def _merge_parameters(path_item: Dict[str, Any], operation: Dict[str, Any]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for source in (path_item.get("parameters", []), operation.get("parameters", [])):
        if not isinstance(source, list):
            continue
        for param in source:
            if not isinstance(param, dict):
                continue
            name = param.get("name")
            location = param.get("in")
            if not name or not location:
                continue
            key = f"{location}:{name}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(param)
    return merged


def extract_operations(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Backward-compatible helper that delegates to OpenAPI ingestor."""
    return OpenAPIIngestor().extract_operations(spec)


def _render_path_with_templates(path: str) -> Tuple[str, List[str]]:
    names = re.findall(r"\{([^{}]+)\}", path or "")
    rendered = path or ""
    for name in names:
        ident = _to_identifier(name, "path_param")
        rendered = rendered.replace("{" + name + "}", "{{.global.task.input." + ident + "}}")
    return rendered, [_to_identifier(name, "path_param") for name in names]


def _tag_counts(ops: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for op in ops:
        for tag in op.get("tags") or []:
            if isinstance(tag, str) and tag.strip():
                counts[tag.strip()] += 1
    return dict(counts)


def _apply_filters(
    ops: List[Dict[str, Any]],
    path_prefix: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filtered = ops
    if path_prefix:
        prefix = path_prefix.strip()
        if prefix:
            filtered = [op for op in filtered if str(op.get("path") or "").startswith(prefix)]
    if tag:
        wanted = tag.strip()
        if wanted:
            wanted_l = wanted.lower()
            filtered = [
                op
                for op in filtered
                if any(isinstance(t, str) and t.lower() == wanted_l for t in (op.get("tags") or []))
            ]
    return filtered


def generate_workflow_from_openapi_spec(
    spec: Dict[str, Any],
    *,
    max_operations: Optional[int] = None,
    path_prefix: Optional[str] = None,
    tag: Optional[str] = None,
    include_sample_workflow: bool = True,
) -> Dict[str, Any]:
    """Build ICO workflow JSON from parsed OpenAPI spec."""
    all_ops = extract_operations(spec)
    if not all_ops:
        return {
            "success": False,
            "error": "No API operations found in OpenAPI spec paths.",
            "validation": {"valid": False, "errors": ["No operations found"], "warnings": [], "info": []},
            "workflow": [],
        }

    filtered_ops = _apply_filters(all_ops, path_prefix=path_prefix, tag=tag)
    total_ops = len(all_ops)
    filtered_total = len(filtered_ops)

    if filtered_total == 0 and (path_prefix or tag):
        counts = _tag_counts(all_ops)
        top_tags = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
        tag_hint = ", ".join([f"{name}({count})" for name, count in top_tags]) if top_tags else "none"
        sample_paths = [op.get("path") for op in all_ops[:10]]
        return {
            "success": False,
            "error": "No API operations matched the provided filters.",
            "hint": (
                "Clear 'Tag' and 'Path prefix' to generate an unfiltered subset, "
                "or use a valid tag/path prefix from this spec."
            ),
            "analysis": {
                "workflow_type": "openapi",
                "total_operations": total_ops,
                "filters": {"tag": tag or "", "path_prefix": path_prefix or "", "max_operations": max_operations},
                "top_tags": tag_hint,
                "sample_paths": sample_paths,
            },
            "validation": {"valid": False, "errors": ["No operations after filters"], "warnings": [], "info": []},
            "workflow": [],
        }

    # Guardrail: very large OpenAPI specs can generate import payloads that are too large for Intersight.
    # Return an actionable error instead of producing an unusable result.
    if filtered_total > OPENAPI_HARD_MAX_OPERATIONS and max_operations is None:
        counts = _tag_counts(filtered_ops) or _tag_counts(all_ops)
        top_tags = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
        tag_hint = ", ".join([f"{name}({count})" for name, count in top_tags]) if top_tags else "none"
        return {
            "success": False,
            "error": (
                f"OpenAPI spec contains {filtered_total} operations after filters "
                f"(total {total_ops}). Generating one task per operation can exceed "
                f"Intersight import limits (HTTP 413)."
            ),
            "hint": (
                "Use 'max_operations' (e.g. 100 or 200) and/or filter by 'tag' or 'path_prefix' "
                "to generate a smaller subset per import."
            ),
            "analysis": {
                "workflow_type": "openapi",
                "total_operations": total_ops,
                "filtered_operations": filtered_total,
                "hard_max_operations": OPENAPI_HARD_MAX_OPERATIONS,
                "top_tags": tag_hint,
                "filters": {"tag": tag or "", "path_prefix": path_prefix or "", "max_operations": None},
            },
            "validation": {"valid": False, "errors": ["Too many operations"], "warnings": [], "info": []},
            "workflow": [],
        }

    if max_operations is None:
        max_operations = OPENAPI_DEFAULT_MAX_OPERATIONS
    try:
        max_operations = int(max_operations)
    except Exception:
        max_operations = OPENAPI_DEFAULT_MAX_OPERATIONS
    if max_operations <= 0:
        max_operations = OPENAPI_DEFAULT_MAX_OPERATIONS
    if max_operations > OPENAPI_HARD_MAX_OPERATIONS:
        max_operations = OPENAPI_HARD_MAX_OPERATIONS

    ops = filtered_ops[:max_operations]
    if not ops:
        return {
            "success": False,
            "error": "No API operations matched the provided filters.",
            "validation": {"valid": False, "errors": ["No operations after filters"], "warnings": [], "info": []},
            "workflow": [],
        }

    info = spec.get("info", {}) if isinstance(spec.get("info"), dict) else {}
    title = info.get("title") or "OpenAPI Generated"
    version = str(info.get("version") or "1.0.0")
    workflow_base = _to_pascal(title, "OpenApiWorkflow")
    workflow_name = f"{workflow_base}SampleWorkflow"

    server_url = ""
    servers = spec.get("servers")
    if isinstance(servers, list) and servers and isinstance(servers[0], dict):
        server_url = str(servers[0].get("url") or "")

    lower_title = str(title).lower()
    lower_server = server_url.lower()
    # Intersight specs commonly expose placeholder server URLs (e.g. https://{server})
    # and execute correctly with relative /api/v1 paths inside ICO.
    use_relative_intersight_urls = (
        "intersight" in lower_title
        or "intersight.com" in lower_server
        or "{server}" in server_url
    )

    components: List[Dict[str, Any]] = []
    task_sequence: List[Dict[str, str]] = []

    for op in ops:
        op_pascal = _to_pascal(op["operation_id"], "ApiOperation")
        task_def_name = f"{op_pascal}Task"
        executor_name = op_pascal
        worker_task_name = f"{op_pascal}Worker"

        input_defs = []
        input_param_map = {}
        if not use_relative_intersight_urls:
            input_defs.append(
                create_primitive_input(
                    name="api_base_url",
                    label="API Base URL",
                    data_type="string",
                    required=True,
                    description="Base URL for API endpoint",
                    default_value=server_url if server_url else None,
                )
            )
            input_param_map["api_base_url"] = "${workflow.input.api_base_url}"

        path_templated, path_param_names = _render_path_with_templates(op["path"])
        param_names = set(path_param_names)
        # Path template params are referenced in URL templates and must be
        # explicitly defined as task inputs even when they also appear in
        # OpenAPI parameters.
        for path_param in path_param_names:
            input_defs.append(
                create_primitive_input(
                    name=path_param,
                    label=_to_pascal(path_param, "PathParam"),
                    data_type="string",
                    required=True,
                    description=f"path parameter: {path_param}",
                )
            )
            input_param_map[path_param] = "${workflow.input." + path_param + "}"

        query_params: List[str] = []
        for param in op["parameters"]:
            location = param.get("in")
            raw_name = str(param.get("name"))
            pname = _to_identifier(raw_name, "param")
            if pname in param_names:
                continue
            param_names.add(pname)
            required = bool(param.get("required", False))
            input_defs.append(
                create_primitive_input(
                    name=pname,
                    label=_to_pascal(raw_name, "Param"),
                    data_type="string",
                    required=required,
                    description=f"{location} parameter: {raw_name}",
                )
            )
            input_param_map[pname] = "${workflow.input." + pname + "}"
            if location == "query":
                query_params.append(f"{raw_name}={{{{.global.task.input.{pname}}}}}")

        if op["has_request_body"]:
            input_defs.append(
                create_primitive_input(
                    name="request_body",
                    label="Request Body",
                    data_type="json",
                    required=False,
                    description="Raw JSON request body",
                )
            )
            input_param_map["request_body"] = "${workflow.input.request_body}"

        output_defs = [create_output_definition(name="api_response", label="API Response", data_type="json")]
        task_properties = create_task_properties(input_definitions=input_defs, output_definitions=output_defs)
        task_body = create_task_definition(
            name=task_def_name,
            label=_to_pascal(op["operation_id"], "Operation"),
            description=op["description"],
            properties=task_properties,
            tags=[{"Key": "source", "Value": "openapi"}, {"Key": "version", "Value": version}],
        )
        components.append(create_bulk_request(task_body, URI_TASK_DEFINITIONS))

        relative_url = path_templated if path_templated.startswith("/") else "/" + path_templated
        if query_params:
            relative_url = relative_url + "?" + "&".join(query_params)
        full_url = relative_url if use_relative_intersight_urls else "{{.global.task.input.api_base_url}}" + relative_url

        webapi_body = ""
        if op["method"] not in {"GET", "DELETE"}:
            webapi_body = "{{.global.task.input.request_body}}"

        webapi = create_web_api(
            name=executor_name,
            label=_to_pascal(op["operation_id"], "Operation"),
            method=op["method"],
            url=full_url,
            body=webapi_body,
            description=op["description"],
            response_parameters=[create_response_parameter(name="api_response", path="$", param_type="json")],
        )
        executor_body = create_batch_api_executor(
            name=_to_pascal(op["operation_id"], "Operation"),
            description=op["description"],
            batch=[webapi],
            output={"api_response": "{{.global." + executor_name + ".output.api_response}}"},
            task_selector=f"Name eq '{task_def_name}' and Version eq 1",
        )
        components.append(create_bulk_request(executor_body, URI_BATCH_API_EXECUTORS))

        task_sequence.append(
            {
                "worker_name": worker_task_name,
                "worker_label": _to_pascal(op["operation_id"], "Operation"),
                "task_definition_name": task_def_name,
                "description": op["description"],
                "input_parameters": input_param_map,
            }
        )

    workflow_inputs = []
    seen_input_names = set()
    if not use_relative_intersight_urls:
        workflow_inputs.append(
            create_primitive_input(
                name="api_base_url",
                label="API Base URL",
                data_type="string",
                required=True,
                description="Base URL for API endpoint",
                default_value=server_url if server_url else None,
            )
        )
        seen_input_names.add("api_base_url")
    for task_item in task_sequence:
        for name in task_item["input_parameters"].keys():
            if name in seen_input_names:
                continue
            seen_input_names.add(name)
            dtype = "json" if name == "request_body" else "string"
            workflow_inputs.append(
                create_primitive_input(
                    name=name,
                    label=_to_pascal(name, "Input"),
                    data_type=dtype,
                    required=name not in {"request_body"},
                    description=f"Workflow input for {name}",
                )
            )

    wf_tasks: List[Dict[str, Any]] = []
    wf_tasks.append(create_start_task(task_sequence[0]["worker_name"]))
    wf_tasks.append(create_success_end_task())
    wf_tasks.append(create_failure_end_task())

    for idx, task_item in enumerate(task_sequence):
        on_success = "SuccessEndTask" if idx == len(task_sequence) - 1 else task_sequence[idx + 1]["worker_name"]
        wf_tasks.append(
            create_worker_task(
                name=task_item["worker_name"],
                label=task_item["worker_label"],
                task_definition_name=task_item["task_definition_name"],
                input_parameters=task_item["input_parameters"],
                on_success=on_success,
                on_failure="FailureEndTask",
                description=task_item["description"],
            )
        )

    ui_positions = [
        create_ui_position("StartTask", 300, 50),
        create_ui_position("SuccessEndTask", 300, 150 + (len(task_sequence) * 120)),
        create_ui_position("FailureEndTask", 520, 150 + (len(task_sequence) * 120)),
    ]
    for idx, task_item in enumerate(task_sequence):
        ui_positions.append(create_ui_position(task_item["worker_name"], 300, 150 + (idx * 120)))

    if include_sample_workflow:
        workflow_body = create_workflow_definition(
            name=workflow_name,
            label=f"{title} Sample Workflow",
            description=f"Generated from OpenAPI spec '{title}'",
            input_definitions=workflow_inputs,
            output_definitions=[create_output_definition("result", "Result", "string", "Workflow completion status")],
            output_parameters={"result": "Completed OpenAPI sample workflow run."},
            tasks=wf_tasks,
            ui_positions=ui_positions,
            tags=[{"Key": "source", "Value": "openapi"}, {"Key": "version", "Value": version}],
        )
        components.append(create_bulk_request(workflow_body, URI_WORKFLOW_DEFINITIONS))

    validator = WorkflowValidator()
    validation = validator.validate(components)
    mermaid = ""
    if len(ops) <= OPENAPI_SKIP_MERMAID_ABOVE_OPERATIONS:
        mermaid = WorkflowGenerator().generate_mermaid(components)

    return {
        "success": True,
        "workflow": components,
        "workflow_type": "openapi",
        "suggested_name": workflow_name,
        "analysis": {
            "workflow_type": "openapi",
            "workflow_name": workflow_name,
            "total_operations": total_ops,
            "filtered_operations": filtered_total,
            "generated_operations": len(ops),
            "truncated": filtered_total > len(ops),
            "filters": {"tag": tag or "", "path_prefix": path_prefix or "", "max_operations": len(ops)},
            "execution_url_mode": "relative_intersight" if use_relative_intersight_urls else "absolute_with_base_url",
            "components": {
                "task_definitions": len(ops),
                "batch_executors": len(ops),
                "workflows": 1 if include_sample_workflow else 0,
                "custom_types": 0,
            },
            "reasoning": "Generated from uploaded OpenAPI specification with one task per operation.",
            "warnings": ([] if len(ops) == filtered_total else ["Result truncated by max_operations"]),
            "confidence": 0.9,
        },
        "mermaid": mermaid,
        "validation": validation,
    }

