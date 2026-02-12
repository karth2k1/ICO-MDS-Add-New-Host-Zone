"""Unit tests for Cisco Chat AI client wire format."""

import json

from app.llm_client import CiscoLLMClient


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_client_requires_appkey(monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "id")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "secret")
    monkeypatch.delenv("CISCO_APPKEY", raising=False)

    try:
        CiscoLLMClient()
        assert False, "Expected ValueError when CISCO_APPKEY is missing"
    except ValueError as exc:
        assert "CISCO_APPKEY" in str(exc)


def test_chat_completion_uses_expected_user_and_headers(monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "id")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("CISCO_APPKEY", "app-key")

    calls = []

    def fake_post(url, data=None, json=None, headers=None, timeout=None):
        calls.append(
            {
                "url": url,
                "data": data,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if "oauth2" in url:
            return _FakeResponse({"access_token": "oauth-token", "expires_in": 3600})
        return _FakeResponse({"choices": [{"message": {"content": "{\"ok\":true}"}}]})

    monkeypatch.setattr("app.llm_client.requests.post", fake_post)

    client = CiscoLLMClient()
    response = client.chat_completion(messages=[{"role": "user", "content": "hello"}])

    assert "choices" in response
    assert len(calls) == 2

    chat_call = calls[1]
    assert chat_call["headers"]["api-key"] == "oauth-token"
    assert chat_call["json"]["user"] == json.dumps({"appkey": "app-key"})
    assert isinstance(chat_call["json"]["user"], str)
