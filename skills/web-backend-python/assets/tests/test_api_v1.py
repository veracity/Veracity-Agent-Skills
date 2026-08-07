from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_versioned_ping_endpoint():
    resp = _client().get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"message": "pong"}


def test_unknown_route_returns_problem_details():
    resp = _client().get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert body["status"] == 404
    assert "title" in body
