"""Ingest context artifacts from uploaded ICO JSON files."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from app.context_models import ContextArtifact, short_sha256
from app.context_store import estimate_tokens, is_ico_bulk_request_array, sanitize_artifact_content


MAX_UPLOAD_FILE_BYTES = 2 * 1024 * 1024


class UploadIngestor:
    """Handles ad-hoc upload ingestion for ICO workflow/task JSON."""

    def ingest(self, filename: str, raw_bytes: bytes, owner: str = "user") -> ContextArtifact:
        if not filename:
            raise ValueError("Uploaded file must have a filename")
        if len(raw_bytes) > MAX_UPLOAD_FILE_BYTES:
            raise ValueError("Uploaded file exceeds size limit (2MB)")

        lower_name = filename.lower()
        if not lower_name.endswith(".json"):
            raise ValueError("Only .json files are accepted for context upload")

        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Uploaded file is not valid UTF-8 JSON") from exc

        normalized = self._normalize_payload(payload)
        if not is_ico_bulk_request_array(normalized):
            raise ValueError(
                "Uploaded JSON does not look like ICO bulk requests. "
                "Expected an array of bulk.RestSubRequest objects."
            )

        sanitized = sanitize_artifact_content(normalized)
        preview = json.dumps(sanitized, separators=(",", ":"), ensure_ascii=True)[:1200]
        artifact_key = f"upload:{filename}:{len(raw_bytes)}:{preview[:200]}"
        artifact_id = f"ctx_{short_sha256(artifact_key)}"

        return ContextArtifact(
            artifact_id=artifact_id,
            name=os.path.basename(filename),
            source_type="upload",
            source_reference=filename,
            domain=self._detect_domain(filename, preview),
            owner=owner,
            content=sanitized,
            content_preview=preview,
            token_estimate=estimate_tokens(preview),
            metadata={"size_bytes": len(raw_bytes)},
        )

    def _normalize_payload(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("requests", "workflow", "components", "bulk_requests", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            if "Body" in payload and payload.get("ClassId") == "bulk.RestSubRequest":
                return [payload]
        raise ValueError("Unsupported JSON structure for context upload")

    def _detect_domain(self, filename: str, preview: str) -> str:
        hint = f"{filename} {preview}".lower()
        if "mds" in hint or "/ins" in hint or "vsan" in hint:
            return "mds"
        if "server" in hint or "locator" in hint or "compute" in hint:
            return "compute"
        if "webapi" in hint or "external" in hint:
            return "webapi"
        return "generic"

