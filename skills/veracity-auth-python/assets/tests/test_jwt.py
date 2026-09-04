import time

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import jwt as jwt_auth
from app.main import create_app
from app.settings import Settings, get_settings

AUDIENCE = "11111111-1111-1111-1111-111111111111"

# Untrusted issuer used only to assert that a token from the wrong authority is rejected.
# Uses an RFC 2606 reserved domain; the name is deliberately neutral so automated security
# scanners do not flag it as a real exfiltration endpoint.
WRONG_ISSUER = "https://wrong-issuer.example.com/"


@pytest.fixture
def keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_pem, public_pem


@pytest.fixture
def settings():
    return Settings(auth_strategy="jwt", jwt_audience=AUDIENCE, cookie_secure=False)


@pytest.fixture
def client(settings, keys):
    _, public_pem = keys
    jwt_auth.set_key_resolver(lambda token: public_pem)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    jwt_auth.set_key_resolver(None)
    app.dependency_overrides.clear()


def _make_token(private_pem, settings, **overrides):
    now = int(time.time())
    payload = {
        "sub": "user-123",
        "name": "Test User",
        "aud": settings.jwt_audience,
        "iss": settings.issuer,
        "iat": now,
        "exp": now + 300,
    }
    payload.update(overrides)
    return pyjwt.encode(payload, private_pem, algorithm="RS256")


def test_valid_token_accepted(client, keys, settings):
    private_pem, _ = keys
    token = _make_token(private_pem, settings)
    resp = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"id": "user-123", "name": "Test User"}


def test_missing_token_rejected(client):
    resp = client.get("/v1/me")
    assert resp.status_code == 401


def test_expired_token_rejected(client, keys, settings):
    private_pem, _ = keys
    token = _make_token(private_pem, settings, exp=int(time.time()) - 120)
    resp = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_wrong_audience_rejected(client, keys, settings):
    private_pem, _ = keys
    token = _make_token(private_pem, settings, aud="someone-else")
    resp = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_wrong_issuer_rejected(client, keys, settings):
    private_pem, _ = keys
    token = _make_token(private_pem, settings, iss=WRONG_ISSUER)
    resp = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
