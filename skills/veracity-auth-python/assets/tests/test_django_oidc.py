"""Django OIDC BFF anonymous status + /api/me 401, and health/security headers."""

from __future__ import annotations

from django.test import Client


def test_auth_status_anonymous_is_false():
    resp = Client().get("/auth")
    assert resp.status_code == 200
    assert resp.json() == {"result": False}


def test_api_me_returns_401_not_redirect():
    resp = Client().get("/api/me")
    assert resp.status_code == 401


def test_health_and_security_headers():
    client = Client()
    for path, key in [("/health", "healthy"), ("/health/ready", "ready"), ("/health/live", "alive")]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json()["status"] == key
    resp = client.get("/health")
    assert "Content-Security-Policy" in resp
    assert resp["X-Content-Type-Options"] == "nosniff"
    assert resp["X-Frame-Options"] == "DENY"
    assert "veracity.com" in resp["Content-Security-Policy"]
