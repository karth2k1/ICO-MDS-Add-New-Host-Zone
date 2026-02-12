"""Tests for GitHub public context ingestor behavior."""

from app.context_ingestors.github_public_ingestor import GitHubPublicIngestor


class _FakeResponse:
    def __init__(self, payload=None, content=b"[]"):
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_ingest_repo_uses_default_branch_for_raw_download(monkeypatch):
    ingestor = GitHubPublicIngestor(max_files=1)
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        if "/repos/acme/workflows" in url and "/git/trees/" not in url:
            return _FakeResponse({"default_branch": "main"})
        if "/git/trees/main" in url:
            return _FakeResponse({"tree": [{"type": "blob", "path": "samples/ok.json"}]})
        if "raw.githubusercontent.com/acme/workflows/main/samples/ok.json" in url:
            return _FakeResponse(content=b'[{"ClassId":"bulk.RestSubRequest","Uri":"/v1/workflow/TaskDefinitions","Verb":"POST","Body":{"ClassId":"workflow.TaskDefinition"}}]')
        raise AssertionError(f"Unexpected URL called: {url}")

    monkeypatch.setattr("app.context_ingestors.github_public_ingestor.requests.get", fake_get)

    artifacts = ingestor.ingest_repo("https://github.com/acme/workflows")

    assert len(artifacts) == 1
    assert any("raw.githubusercontent.com/acme/workflows/main/samples/ok.json" in url for url in calls)
