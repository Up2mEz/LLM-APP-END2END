import re
from fastapi.testclient import TestClient
from ncd_gemma import server


def test_built_frontend_assets_and_csp(monkeypatch):
    monkeypatch.setenv('NCD_DEMO_PASSWORD', '')
    client = TestClient(server.app)
    page = client.get('/')
    assert page.status_code == 200
    assert page.headers['cache-control'] == 'no-cache'
    assert "script-src 'self'" in page.headers['content-security-policy']
    assert "connect-src 'self'" in page.headers['content-security-policy']
    if (server.ROOT / 'static/app/index.html').is_file():
        assert '<div id="root"></div>' in page.text
        script = re.search(r'<script[^>]+src="([^"]+)"', page.text).group(1)
        response = client.get(script)
        assert response.status_code == 200
        assert 'javascript' in response.headers['content-type']
        assert client.get('/app/favicon.svg').status_code == 200
    assert client.get('/index.html').status_code == 200


def test_root_falls_back_when_build_missing(tmp_path, monkeypatch):
    (tmp_path / 'static').mkdir()
    (tmp_path / 'static/index.html').write_text('<h1>legacy</h1>', encoding='utf8')
    monkeypatch.setattr(server, 'ROOT', tmp_path)
    assert server.frontend().path == tmp_path / 'static/index.html'
