import httpx

from app.main import create_app
from app.settings import Settings
from app.veracity.client import VeracityAuth
from fastapi.testclient import TestClient


def _oidc_client() -> TestClient:
    return TestClient(create_app(Settings(auth_strategy="oidc", cookie_secure=False)))


def test_auth_status_anonymous_is_false():
    resp = _oidc_client().get("/auth")
    assert resp.status_code == 200
    assert resp.json() == {"result": False}


def test_api_me_returns_401_not_redirect():
    # /api/* must return 401 for unauthenticated callers, never a login redirect.
    resp = _oidc_client().get("/api/me", follow_redirects=False)
    assert resp.status_code == 401


def test_veracity_auth_injects_headers():
    auth = VeracityAuth(token_provider=lambda: "test-access-token", subscription_key="sub-key-123")
    request = httpx.Request("GET", "https://api.veracity.com/veracity/graph/v4/my/profile")
    flow = auth.auth_flow(request)
    prepared = next(flow)
    assert prepared.headers["Authorization"] == "Bearer test-access-token"
    assert prepared.headers["Ocp-Apim-Subscription-Key"] == "sub-key-123"
