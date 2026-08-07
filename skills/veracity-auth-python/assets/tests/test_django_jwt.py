"""Django DRF JWT accept/reject matrix via VeracityJWTAuthentication."""

from __future__ import annotations

import time

import pytest
from rest_framework.test import APIClient

from veracity_core.settings import Settings, get_settings
from veracity_core.tokens import set_key_resolver

AUDIENCE = "11111111-1111-1111-1111-111111111111"


def _issuer() -> str:
    return Settings().issuer


@pytest.fixture
def api(rsa_keys, monkeypatch):
    _, public_pem = rsa_keys
    set_key_resolver(lambda _t: public_pem)
    # The DRF auth class reads get_settings(); point JWT_AUDIENCE at our test audience.
    monkeypatch.setenv("JWT_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    get_settings.cache_clear()
    yield APIClient()
    get_settings.cache_clear()


def test_valid_token_accepted(api, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, AUDIENCE, _issuer())
    resp = api.get("/drf/me", HTTP_AUTHORIZATION=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == {"id": "user-123", "name": "Test User"}


def test_missing_token_rejected(api):
    resp = api.get("/drf/me")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


def test_expired_token_rejected(api, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, AUDIENCE, _issuer(), exp=int(time.time()) - 120)
    assert api.get("/drf/me", HTTP_AUTHORIZATION=auth_header(token)).status_code == 401


def test_wrong_audience_rejected(api, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, "someone-else", _issuer())
    assert api.get("/drf/me", HTTP_AUTHORIZATION=auth_header(token)).status_code == 401


def test_wrong_issuer_rejected(api, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, AUDIENCE, "https://evil.example.com/")
    assert api.get("/drf/me", HTTP_AUTHORIZATION=auth_header(token)).status_code == 401
