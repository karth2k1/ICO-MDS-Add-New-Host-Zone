"""Persistent storage and selection logic for user context artifacts."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.context_models import ContextArtifact


SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|apikey|api_key|client_secret|authorization)",
    re.IGNORECASE,
)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for budgeting.

    A practical approximation is ~4 characters per token for English/JSON.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _strip_sensitive_fields(value: Any) -> Any:
    """Recursively remove likely sensitive fields from nested content."""
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                continue
            sanitized[key] = _strip_sensitive_fields(item)
        return sanitized
    if isinstance(value, list):
        return [_strip_sensitive_fields(item) for item in value]
    return value


def sanitize_artifact_content(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize content before persistence and prompt use."""
    return _strip_sensitive_fields(content)


def is_ico_bulk_request_array(payload: Any) -> bool:
    """Check whether payload resembles ICO bulk request objects."""
    if not isinstance(payload, list) or not payload:
        return False
    for item in payload:
        if not isinstance(item, dict):
            return False
        if item.get("ClassId") != "bulk.RestSubRequest":
            return False
        if "Uri" not in item or "Body" not in item:
            return False
    return True


class ContextRepository:
    """Stores and retrieves reusable context artifacts."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._ensure_parent_dir()

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.storage_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _load_all(self) -> List[ContextArtifact]:
        if not os.path.exists(self.storage_path):
            return []
        with open(self.storage_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, list):
            return []
        return [ContextArtifact.from_dict(item) for item in raw]

    def _save_all(self, artifacts: List[ContextArtifact]) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump([artifact.to_dict() for artifact in artifacts], handle, indent=2)

    def list_artifacts(self) -> List[ContextArtifact]:
        """Return all stored artifacts."""
        return self._load_all()

    def get_artifact(self, artifact_id: str) -> Optional[ContextArtifact]:
        """Get one artifact by ID."""
        for artifact in self._load_all():
            if artifact.artifact_id == artifact_id:
                return artifact
        return None

    def upsert_artifact(self, artifact: ContextArtifact) -> ContextArtifact:
        """Insert or replace an artifact by ID."""
        all_artifacts = self._load_all()
        remaining = [item for item in all_artifacts if item.artifact_id != artifact.artifact_id]
        remaining.append(artifact)
        self._save_all(remaining)
        return artifact

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete artifact by ID, returning True if removed."""
        all_artifacts = self._load_all()
        new_items = [item for item in all_artifacts if item.artifact_id != artifact_id]
        if len(new_items) == len(all_artifacts):
            return False
        self._save_all(new_items)
        return True

    def select_for_prompt(
        self,
        jira_text: str,
        selected_artifact_ids: Optional[Iterable[str]],
        available_budget_tokens: int,
        max_artifacts: int = 5,
    ) -> Tuple[List[ContextArtifact], Dict[str, Any]]:
        """
        Select artifacts to include in prompt within token budget.

        If selected IDs are provided, that subset is used; otherwise top-ranked
        relevant artifacts are chosen.
        """
        all_artifacts = self._load_all()
        by_id = {artifact.artifact_id: artifact for artifact in all_artifacts}

        if selected_artifact_ids:
            candidates = [by_id[item] for item in selected_artifact_ids if item in by_id]
        else:
            candidates = all_artifacts

        ranked = sorted(
            candidates,
            key=lambda artifact: self._relevance_score(jira_text, artifact),
            reverse=True,
        )

        chosen: List[ContextArtifact] = []
        dropped: List[Dict[str, Any]] = []
        used_tokens = 0

        for artifact in ranked:
            if len(chosen) >= max_artifacts:
                dropped.append({"artifact_id": artifact.artifact_id, "reason": "max_artifacts"})
                continue

            artifact_tokens = artifact.token_estimate
            if used_tokens + artifact_tokens > available_budget_tokens:
                dropped.append(
                    {
                        "artifact_id": artifact.artifact_id,
                        "reason": "token_budget",
                        "token_estimate": artifact_tokens,
                    }
                )
                continue

            chosen.append(artifact)
            used_tokens += artifact_tokens

        diagnostics = {
            "available_budget_tokens": available_budget_tokens,
            "used_tokens": used_tokens,
            "selected_count": len(chosen),
            "dropped": dropped,
        }
        return chosen, diagnostics

    def _relevance_score(self, jira_text: str, artifact: ContextArtifact) -> int:
        """Basic lexical relevance scoring with domain weighting."""
        jira_words = set(re.findall(r"[a-zA-Z0-9_]+", jira_text.lower()))
        blob = f"{artifact.name} {artifact.domain} {artifact.content_preview}".lower()
        artifact_words = set(re.findall(r"[a-zA-Z0-9_]+", blob))
        overlap = len(jira_words.intersection(artifact_words))

        if "mds" in jira_words and artifact.domain == "mds":
            overlap += 3
        if "webapi" in jira_words and artifact.domain in {"generic", "webapi"}:
            overlap += 2
        return overlap

