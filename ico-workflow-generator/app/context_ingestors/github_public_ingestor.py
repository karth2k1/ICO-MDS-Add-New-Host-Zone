"""Ingest ICO context artifacts from public GitHub repositories."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import requests

from app.context_models import ContextArtifact, short_sha256
from app.context_store import estimate_tokens, is_ico_bulk_request_array, sanitize_artifact_content
from app.context_ingestors.upload_ingestor import UploadIngestor


class GitHubPublicIngestor:
    """Fetches JSON files from a public GitHub repository and ingests valid ICO payloads."""

    API_BASE = "https://api.github.com"
    RAW_BASE = "https://raw.githubusercontent.com"

    def __init__(self, max_files: int = 10):
        self.max_files = max_files
        self._upload_ingestor = UploadIngestor()

    def ingest_repo(self, repo_url: str, owner: str = "user") -> List[ContextArtifact]:
        org, repo = self._parse_repo_url(repo_url)
        tree = self._get_repo_tree(org, repo)

        json_paths = [item["path"] for item in tree if item.get("type") == "blob" and item.get("path", "").endswith(".json")]
        artifacts: List[ContextArtifact] = []

        for path in json_paths[: self.max_files]:
            raw = self._download_raw_file(org, repo, path)
            try:
                artifact = self._upload_ingestor.ingest(filename=path, raw_bytes=raw, owner=owner)
            except ValueError:
                # Only keep files that are valid ICO bulk request payloads
                continue

            # Re-key metadata for GitHub source provenance
            artifact.artifact_id = f"ctx_{short_sha256(f'github:{org}/{repo}:{path}')}"
            artifact.source_type = "github_public"
            artifact.source_reference = f"{org}/{repo}:{path}"
            artifact.name = path.split("/")[-1]
            artifact.metadata.update(
                {
                    "repo": f"{org}/{repo}",
                    "path": path,
                    "repo_url": repo_url,
                }
            )
            artifacts.append(artifact)

        return artifacts

    def _parse_repo_url(self, repo_url: str) -> List[str]:
        match = re.match(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git|/)?$", repo_url.strip())
        if not match:
            raise ValueError("Expected GitHub URL format: https://github.com/<org>/<repo>")
        return [match.group(1), match.group(2)]

    def _get_repo_tree(self, org: str, repo: str) -> List[Dict[str, Any]]:
        branch = self._resolve_default_branch(org, repo)
        response = requests.get(
            f"{self.API_BASE}/repos/{org}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("tree", [])

    def _resolve_default_branch(self, org: str, repo: str) -> str:
        response = requests.get(
            f"{self.API_BASE}/repos/{org}/{repo}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("default_branch", "main")

    def _download_raw_file(self, org: str, repo: str, path: str) -> bytes:
        response = requests.get(
            f"{self.RAW_BASE}/{org}/{repo}/HEAD/{path}",
            timeout=30,
        )
        response.raise_for_status()
        return response.content

