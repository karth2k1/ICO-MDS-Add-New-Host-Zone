"""Route tests for LLM setup pages and APIs."""


def test_llm_setup_page_renders(client):
    response = client.get("/llm-setup")
    assert response.status_code == 200
    assert b"LLM Setup" in response.data


def test_llm_setup_get_returns_model_and_masked_settings(client, monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "env-client")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "env-secret-1234")
    monkeypatch.setenv("CISCO_APPKEY", "env-appkey-9876")

    response = client.get("/llm/setup")
    assert response.status_code == 200
    body = response.get_json()
    assert body["model"] == "Cisco Chat AI GPT-4.1"
    assert body["configured"] is True
    assert body["settings"]["client_secret"].endswith("1234")
    assert body["settings"]["appkey"].endswith("9876")


def test_llm_setup_post_validates_required_fields(client):
    response = client.post("/llm/setup", json={"client_id": "x"})
    assert response.status_code == 400
    body = response.get_json()
    assert "Missing required field" in body["error"]


def test_llm_setup_post_saves_and_masks(client):
    response = client.post(
        "/llm/setup",
        json={
            "client_id": "local-client",
            "client_secret": "local-secret-1234",
            "appkey": "local-appkey-5678",
            "username": "user1",
            "oauth_url": "https://id.cisco.com/oauth2/default/v1/token",
            "chat_url": "https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions",
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["settings"]["client_secret"].endswith("1234")
    assert body["settings"]["appkey"].endswith("5678")


def test_llm_test_success(client, monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "x")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "y")
    monkeypatch.setenv("CISCO_APPKEY", "z")

    import app.llm_client as llm_client_module

    monkeypatch.setattr(llm_client_module.CiscoLLMClient, "_get_access_token", lambda self: "token")
    response = client.post("/llm/test")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True


def test_llm_test_error_returns_400(client, monkeypatch):
    monkeypatch.setenv("CISCO_CLIENT_ID", "x")
    monkeypatch.setenv("CISCO_CLIENT_SECRET", "y")
    monkeypatch.setenv("CISCO_APPKEY", "z")

    import app.llm_client as llm_client_module

    def fail_token(self):
        raise RuntimeError("token failure")

    monkeypatch.setattr(llm_client_module.CiscoLLMClient, "_get_access_token", fail_token)
    response = client.post("/llm/test")
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert "token failure" in body["error"]

