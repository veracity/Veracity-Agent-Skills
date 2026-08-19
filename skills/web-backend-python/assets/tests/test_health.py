from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


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
    assert h["X-XSS-Protection"] == "0"
    assert h["X-Permitted-Cross-Domain-Policies"] == "none"
    assert "Strict-Transport-Security" in h


def test_csp_is_generic_self_only():
    # Baseline ships a locked-down 'self'-only CSP with no external hosts.
    csp = _client().get("/health").headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "base-uri 'none'" in csp
    assert "form-action 'self'" in csp
    assert "'unsafe-inline'" not in csp
    assert "https://" not in csp
