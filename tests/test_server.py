import base64

import pytest
from fastapi.testclient import TestClient
from ncd_gemma import server
from ncd_gemma.config import allowed_hosts


@pytest.fixture(autouse=True)
def local_test_access(monkeypatch):
    # A developer's private .env may protect the running demo. Tests set their
    # own auth state explicitly instead of inheriting it from that file.
    monkeypatch.setenv('NCD_DEMO_PASSWORD', '')


def test_ui_health_and_no_secret_in_health():
    client = TestClient(server.app)
    assert client.get("/").status_code == 200
    body = client.get("/api/health").json()
    assert body["model"] == "gemma-4-E4B-it"
    assert "api_key" not in body
    assert client.get("/style.css").status_code == 200
    assert client.get("/tokens.css").status_code == 200
    assert client.get("/clinic.css").status_code == 200


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


def test_greeting_needs_no_retriever_or_proxy(monkeypatch):
    def fail():
        raise AssertionError('A standalone greeting must not load the model')
    monkeypatch.setattr(server, 'get_agent', fail)
    data = TestClient(server.app).post('/api/ask', json={'question': 'hello'}).json()
    assert data['status'] == 'out_of_scope'
    assert data['stats']['api_calls'] == data['stats']['searches'] == 0
    assert data['citations'] == []


def test_remote_host_requires_exact_name_and_password(monkeypatch):
    monkeypatch.setenv('NCD_PUBLIC_HOST', 'demo.example.org')
    monkeypatch.delenv('NCD_DEMO_PASSWORD', raising=False)
    with pytest.raises(ValueError, match='NCD_DEMO_PASSWORD'):
        allowed_hosts()
    monkeypatch.setenv('NCD_DEMO_PASSWORD', 'long-demo-secret')
    assert allowed_hosts() == ['127.0.0.1', 'localhost', 'testserver', 'demo.example.org']
    for bad_host in ('*', 'https://demo.example.org', 'demo.example.org:443', '*.example.org'):
        monkeypatch.setenv('NCD_PUBLIC_HOST', bad_host)
        with pytest.raises(ValueError, match='hostname'):
            allowed_hosts()


def test_demo_password_protects_page_and_ask_but_not_health(monkeypatch):
    monkeypatch.setenv('NCD_DEMO_PASSWORD', 'long-demo-secret')
    monkeypatch.setenv('NCD_DEMO_USER', 'grader')
    client = TestClient(server.app)
    assert client.get('/api/health').status_code == 200
    denied = client.get('/')
    assert denied.status_code == 401
    assert denied.headers['www-authenticate'] == 'Basic realm="NCD demo"'
    assert client.post('/api/ask', json={'question': 'hello'}).status_code == 401
    value = base64.b64encode(b'grader:long-demo-secret').decode()
    headers = {'Authorization': f'Basic {value}'}
    assert client.get('/', headers=headers).status_code == 200
    assert client.post('/api/ask', json={'question': 'hello'}, headers=headers).json()['status'] == 'out_of_scope'
    assert client.get('/', headers={'Authorization': 'Basic broken'}).status_code == 401


def test_same_host_https_origin_works_behind_tls_proxy():
    client = TestClient(server.app)
    response = client.post('/api/ask', json={'question': 'hello'}, headers={'Origin': 'https://testserver'})
    assert response.status_code == 200
    assert response.json()['status'] == 'out_of_scope'
