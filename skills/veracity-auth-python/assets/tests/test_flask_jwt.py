"""Flask JWT accept/reject matrix via the @require_user decorator."""

from __future__ import annotations

import time

import pytest

from veracity_core.settings import Settings
from veracity_core.tokens import set_key_resolver
from veracity_flask.app_factory import create_app

AUDIENCE = "11111111-1111-1111-1111-111111111111"

# Untrusted issuer used only to assert that a token from the wrong authority is rejected.
# Uses an RFC 2606 reserved domain; the name is deliberately neutral so automated security
# scanners do not flag it as a real exfiltration endpoint.
WRONG_ISSUER = "https://wrong-issuer.example.com/"


@pytest.fixture
def settings():
    return Settings(auth_strategy="jwt", jwt_audience=AUDIENCE, cookie_secure=False)


@pytest.fixture
def client(settings, rsa_keys):
    _, public_pem = rsa_keys
    set_key_resolver(lambda _t: public_pem)
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app.test_client()


def test_valid_token_accepted(client, settings, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, settings.jwt_audience, settings.issuer)
    resp = client.get("/v1/me", headers={"Authorization": auth_header(token)})
    assert resp.status_code == 200
    assert resp.get_json() == {"id": "user-123", "name": "Test User"}


def test_missing_token_rejected(client):
    resp = client.get("/v1/me")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


def test_expired_token_rejected(client, settings, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(
        private_pem, settings.jwt_audience, settings.issuer, exp=int(time.time()) - 120
    )
    assert client.get("/v1/me", headers={"Authorization": auth_header(token)}).status_code == 401


def test_wrong_audience_rejected(client, settings, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, "someone-else", settings.issuer)
    assert client.get("/v1/me", headers={"Authorization": auth_header(token)}).status_code == 401


def test_wrong_issuer_rejected(client, settings, rsa_keys, make_token, auth_header):
    private_pem, _ = rsa_keys
    token = make_token(private_pem, settings.jwt_audience, WRONG_ISSUER)
    assert client.get("/v1/me", headers={"Authorization": auth_header(token)}).status_code == 401
