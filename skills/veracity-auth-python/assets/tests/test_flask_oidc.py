"""Flask OIDC BFF anonymous status + /api/me 401, and health/security headers."""

from __future__ import annotations

from veracity_core.settings import Settings
from veracity_flask.app_factory import create_app


def _oidc_client():
    app = create_app(Settings(auth_strategy="oidc", cookie_secure=False))
    app.config.update(TESTING=True)
    return app.test_client()


def test_auth_status_anonymous_is_false():
    resp = _oidc_client().get("/auth")
    assert resp.status_code == 200
    assert resp.get_json() == {"result": False}


def test_api_me_returns_401_not_redirect():
    resp = _oidc_client().get("/api/me")
    assert resp.status_code == 401


def test_health_and_security_headers():
    app = create_app(Settings(auth_strategy="jwt", cookie_secure=False))
    app.config.update(TESTING=True)
    client = app.test_client()
    for path, key in [("/health", "healthy"), ("/health/ready", "ready"), ("/health/live", "alive")]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == key
    headers = client.get("/health").headers
    assert "Content-Security-Policy" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "veracity.com" in headers["Content-Security-Policy"]
