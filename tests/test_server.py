from fastapi.testclient import TestClient
from ncd_gemma import server


def test_ui_health_and_no_secret_in_health():
    client = TestClient(server.app)
    assert client.get("/").status_code == 200
    body = client.get("/api/health").json()
    assert body["model"] == "gemma-4-E4B-it"
    assert "api_key" not in body
    assert client.get("/style.css").status_code == 200


def test_reject_empty_and_extra_fields():
    client = TestClient(server.app)
    assert client.post("/api/ask", json={"question": " "}).status_code == 422
    assert client.post("/api/ask", json={"question": "x", "api_key": "bad"}).status_code == 422


def test_cross_origin_and_host_are_rejected():
    client = TestClient(server.app)
    assert client.post("/api/ask", json={"question": "x"}, headers={"Origin": "https://malicious.example"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "malicious.example"}).status_code == 400


def test_busy_response_has_no_second_model_call():
    client = TestClient(server.app)
    server._request_slot.acquire()
    try:
        assert client.post("/api/ask", json={"question": "x"}).status_code == 429
    finally:
        server._request_slot.release()


def test_runtime_configuration_error_is_sanitized(monkeypatch):
    def fail():
        raise RuntimeError("secret key must not leak")
    monkeypatch.setattr(server, "get_agent", fail)
    response = TestClient(server.app).post("/api/ask", json={"question": "x"})
    assert response.status_code == 503
    assert "secret" not in response.text
