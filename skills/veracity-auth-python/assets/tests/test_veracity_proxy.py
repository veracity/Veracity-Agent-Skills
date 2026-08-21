"""Veracity Platform API proxy routes (the paths the veracity-auth-ui SPA calls).

Verifies, per framework, that the mount matches the frontend contract
(`/api/v1/veracity/v3/services`, `/api/v1/veracity/v4/me/applications`), returns 401 when
the BFF session has no user, and relays upstream data on the authenticated path. The core
fetch helpers are monkeypatched so no MSAL/network call is made.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app as create_fastapi_app
from app.settings import Settings

V3_PATH = "/api/v1/veracity/v3/services"
V4_PATH = "/api/v1/veracity/v4/me/applications"
V3_POLICY_PATH = "/api/v1/veracity/v3/policy/validate"
V4_POLICY_PATH = "/api/v1/veracity/v4/policy/validate"


# --- FastAPI -----------------------------------------------------------------
def _fastapi_client() -> TestClient:
    return TestClient(create_fastapi_app(Settings(auth_strategy="oidc", cookie_secure=False)))


def test_fastapi_proxy_anonymous_is_401():
    client = _fastapi_client()
    assert client.get(V3_PATH).status_code == 401
    assert client.get(V4_PATH).status_code == 401
    assert client.get(V3_POLICY_PATH).status_code == 401
    assert client.get(V4_POLICY_PATH).status_code == 401


def test_fastapi_proxy_returns_upstream_data(monkeypatch):
    from app.veracity import routes

    monkeypatch.setattr(routes, "_user_token", lambda request: "user-token")
    monkeypatch.setattr(routes, "get_my_services", lambda s, t: [{"serviceId": "svc-1"}])
    monkeypatch.setattr(
        routes, "get_my_applications", lambda s, t: [{"id": "app-1", "name": "App"}]
    )
    client = _fastapi_client()
    assert client.get(V3_PATH).json() == [{"serviceId": "svc-1"}]
    assert client.get(V4_PATH).json() == [{"id": "app-1", "name": "App"}]


def test_fastapi_policy_validate(monkeypatch):
    from app.veracity import routes

    monkeypatch.setattr(routes, "_user_token", lambda request: "user-token")
    for path, helper in ((V3_POLICY_PATH, "validate_policy_v3"), (V4_POLICY_PATH, "validate_policy_v4")):
        monkeypatch.setattr(
            routes, helper, lambda s, t, r: {"compliant": True, "redirectUrl": None}
        )
        client = _fastapi_client()
        ok = client.get(path)
        assert ok.status_code == 200
        assert ok.json() == {"compliant": True, "redirectUrl": None}

        monkeypatch.setattr(
            routes,
            helper,
            lambda s, t, r: {"compliant": False, "redirectUrl": "https://accept"},
        )
        not_ok = client.get(path)
        assert not_ok.status_code == 406
        assert not_ok.json() == {"compliant": False, "redirectUrl": "https://accept"}


# --- Flask -------------------------------------------------------------------
def _flask_client():
    from veracity_flask.app_factory import create_app

    app = create_app(Settings(auth_strategy="oidc", cookie_secure=False))
    app.config.update(TESTING=True)
    return app.test_client()


def test_flask_proxy_anonymous_is_401():
    client = _flask_client()
    assert client.get(V3_PATH).status_code == 401
    assert client.get(V4_PATH).status_code == 401
    assert client.get(V3_POLICY_PATH).status_code == 401
    assert client.get(V4_POLICY_PATH).status_code == 401


def test_flask_proxy_returns_upstream_data(monkeypatch):
    from veracity_flask import veracity_api

    monkeypatch.setattr(veracity_api, "_user_token", lambda: "user-token")
    monkeypatch.setattr(veracity_api, "get_my_services", lambda s, t: [{"serviceId": "svc-1"}])
    monkeypatch.setattr(
        veracity_api, "get_my_applications", lambda s, t: [{"id": "app-1"}]
    )
    client = _flask_client()
    assert client.get(V3_PATH).get_json() == [{"serviceId": "svc-1"}]
    assert client.get(V4_PATH).get_json() == [{"id": "app-1"}]


def test_flask_policy_validate(monkeypatch):
    from veracity_flask import veracity_api

    monkeypatch.setattr(veracity_api, "_user_token", lambda: "user-token")
    for path, helper in ((V3_POLICY_PATH, "validate_policy_v3"), (V4_POLICY_PATH, "validate_policy_v4")):
        monkeypatch.setattr(
            veracity_api, helper, lambda s, t, r: {"compliant": True, "redirectUrl": None}
        )
        client = _flask_client()
        ok = client.get(path)
        assert ok.status_code == 200
        assert ok.get_json() == {"compliant": True, "redirectUrl": None}

        monkeypatch.setattr(
            veracity_api,
            helper,
            lambda s, t, r: {"compliant": False, "redirectUrl": "https://accept"},
        )
        not_ok = client.get(path)
        assert not_ok.status_code == 406
        assert not_ok.get_json() == {"compliant": False, "redirectUrl": "https://accept"}


# --- Django ------------------------------------------------------------------
def test_django_proxy_anonymous_is_401():
    from django.test import Client

    client = Client()
    assert client.get(V3_PATH).status_code == 401
    assert client.get(V4_PATH).status_code == 401
    assert client.get(V3_POLICY_PATH).status_code == 401
    assert client.get(V4_POLICY_PATH).status_code == 401


def test_django_proxy_returns_upstream_data(monkeypatch):
    from django.test import Client

    from veracity_django import veracity_api

    monkeypatch.setattr(veracity_api, "_user_token", lambda request: "user-token")
    monkeypatch.setattr(veracity_api, "get_my_services", lambda s, t: [{"serviceId": "svc-1"}])
    monkeypatch.setattr(
        veracity_api, "get_my_applications", lambda s, t: [{"id": "app-1"}]
    )
    client = Client()
    assert client.get(V3_PATH).json() == [{"serviceId": "svc-1"}]
    assert client.get(V4_PATH).json() == [{"id": "app-1"}]


def test_django_policy_validate(monkeypatch):
    from django.test import Client

    from veracity_django import veracity_api

    monkeypatch.setattr(veracity_api, "_user_token", lambda request: "user-token")
    for path, helper in ((V3_POLICY_PATH, "validate_policy_v3"), (V4_POLICY_PATH, "validate_policy_v4")):
        monkeypatch.setattr(
            veracity_api, helper, lambda s, t, r: {"compliant": True, "redirectUrl": None}
        )
        client = Client()
        ok = client.get(path)
        assert ok.status_code == 200
        assert ok.json() == {"compliant": True, "redirectUrl": None}

        monkeypatch.setattr(
            veracity_api,
            helper,
            lambda s, t, r: {"compliant": False, "redirectUrl": "https://accept"},
        )
        not_ok = client.get(path)
        assert not_ok.status_code == 406
        assert not_ok.json() == {"compliant": False, "redirectUrl": "https://accept"}


# --- Policy result translation (proxy helper) --------------------------------
def test_policy_result_403_with_redirect_is_treated_as_406():
    import httpx

    from veracity_core.proxy import _policy_result

    resp = httpx.Response(status_code=403, json={"url": "https://accept"})
    assert _policy_result(resp, redirect_on_403=True) == {
        "compliant": False,
        "redirectUrl": "https://accept",
    }


def test_policy_result_403_without_redirect_raises():
    import httpx
    import pytest

    from veracity_core.proxy import VeracityApiError, _policy_result

    resp = httpx.Response(status_code=403, json={"message": "forbidden"})
    with pytest.raises(VeracityApiError) as exc_info:
        _policy_result(resp, redirect_on_403=True)
    assert exc_info.value.status_code == 403


def test_policy_result_403_not_redirected_without_opt_in():
    import httpx
    import pytest

    from veracity_core.proxy import VeracityApiError, _policy_result

    resp = httpx.Response(status_code=403, json={"url": "https://accept"})
    with pytest.raises(VeracityApiError) as exc_info:
        _policy_result(resp)
    assert exc_info.value.status_code == 403


def test_validate_policy_v4_maps_403_redirect(monkeypatch):
    import httpx

    from veracity_core import proxy

    class _FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, path, params=None):
            return httpx.Response(status_code=403, json={"redirectUrl": "https://accept"})

    monkeypatch.setattr(proxy, "make_v4_client", lambda s, p: _FakeClient())
    settings = Settings(auth_strategy="oidc", cookie_secure=False, service_id="svc-1")
    assert proxy.validate_policy_v4(settings, "token", "https://app") == {
        "compliant": False,
        "redirectUrl": "https://accept",
    }
