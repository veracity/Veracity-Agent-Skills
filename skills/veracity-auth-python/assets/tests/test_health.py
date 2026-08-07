from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def _client(strategy: str = "jwt") -> TestClient:
    return TestClient(create_app(Settings(auth_strategy=strategy, cookie_secure=False)))


def test_health_endpoints():
    client = _client()
    for path, key in [("/health", "healthy"), ("/health/ready", "ready"), ("/health/live", "alive")]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json()["status"] == key


def test_security_headers_present():
    resp = _client().get("/health")
    h = resp.headers
    assert "Content-Security-Policy" in h
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in h
    assert "veracity.com" in h["Content-Security-Policy"]
