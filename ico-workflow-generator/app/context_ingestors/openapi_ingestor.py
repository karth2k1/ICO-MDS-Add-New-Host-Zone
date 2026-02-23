"""Parse OpenAPI/Swagger specs for OpenAPI generation mode."""

from __future__ import annotations

import json
from typing import Any, Dict, List

import yaml


HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


class OpenAPIIngestor:
    """Utility parser that normalizes OpenAPI operations."""

    def parse_spec(self, raw_bytes: bytes, filename: str = "openapi") -> Dict[str, Any]:
        """Parse uploaded OpenAPI JSON/YAML payload."""
        if not raw_bytes:
            raise ValueError("Uploaded OpenAPI file is empty")

        lowered = (filename or "").lower()
        try:
            if lowered.endswith(".json"):
                spec = json.loads(raw_bytes.decode("utf-8"))
            else:
                # Some specs are emitted as multi-document YAML. Prefer the first
                # document that looks like an OpenAPI object.
                docs = list(yaml.safe_load_all(raw_bytes.decode("utf-8")))
                spec = docs[0] if docs else None
                if isinstance(spec, list):
                    # Occasionally wrappers emit a one-item list.
                    for item in spec:
                        if isinstance(item, dict) and ("paths" in item) and (item.get("openapi") or item.get("swagger")):
                            spec = item
                            break
                if not isinstance(spec, dict):
                    # If there are multiple documents, choose the first dict-like OpenAPI doc.
                    for doc in docs:
                        if isinstance(doc, dict) and ("paths" in doc) and (doc.get("openapi") or doc.get("swagger")):
                            spec = doc
                            break
        except Exception as exc:
            raise ValueError("Failed to parse OpenAPI file. Ensure valid JSON/YAML.") from exc

        if not isinstance(spec, dict):
            raise ValueError(
                "OpenAPI spec must parse to an object. "
                f"Parsed top-level type: {type(spec).__name__}."
            )
        if "paths" not in spec or not isinstance(spec["paths"], dict):
            raise ValueError("OpenAPI spec missing required 'paths' object")
        if not (spec.get("openapi") or spec.get("swagger")):
            raise ValueError("OpenAPI spec must contain 'openapi' or 'swagger' version key")
        return spec

    def extract_operations(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract operation models from OpenAPI paths."""
        operations: List[Dict[str, Any]] = []
        for path, path_item in (spec.get("paths") or {}).items():
            if not isinstance(path_item, dict):
                continue
            for method in HTTP_METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue
                op_id = operation.get("operationId") or f"{method}_{path}"
                description = operation.get("summary") or operation.get("description") or f"{method.upper()} {path}"
                tags = operation.get("tags") if isinstance(operation.get("tags"), list) else []
                params = self._merge_parameters(path_item, operation)

                has_body = False
                if isinstance(operation.get("requestBody"), dict):
                    has_body = True
                else:
                    has_body = any(p.get("in") == "body" for p in params if isinstance(p, dict))

                operations.append(
                    {
                        "operation_id": op_id,
                        "method": method.upper(),
                        "path": path,
                        "description": description,
                        "tags": [str(t) for t in tags if t is not None and str(t).strip()],
                        "parameters": params,
                        "has_request_body": has_body,
                    }
                )
        # Deterministic ordering across runs
        operations.sort(key=lambda o: (o.get("path", ""), o.get("method", ""), o.get("operation_id", "")))
        return operations

    def _merge_parameters(self, path_item: Dict[str, Any], operation: Dict[str, Any]) -> List[Dict[str, Any]]:
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

