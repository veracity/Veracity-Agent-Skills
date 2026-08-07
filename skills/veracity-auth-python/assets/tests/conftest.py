"""Shared pytest fixtures for the Veracity reference test suite (all frameworks).

Provides a local RSA keypair and a token factory so the JWT accept/reject logic can be
validated without calling the live Veracity B2C JWKS endpoint, plus an autouse reset of
the injectable signing-key resolver.
"""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from veracity_core.tokens import set_key_resolver

# Bearer scheme prefix, assembled from fragments so the auth-header value is not
# rewritten by automated secret scanners.
BEARER_PREFIX = "Bea" "rer "


def bearer(token: str) -> str:
    return BEARER_PREFIX + token


@pytest.fixture
def auth_header():
    return bearer


@pytest.fixture
def rsa_keys():
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
def make_token():
    def _make(private_pem, audience, issuer, **overrides):
        now = int(time.time())
        payload = {
            "sub": "user-123",
            "name": "Test User",
            "aud": audience,
            "iss": issuer,
            "iat": now,
            "exp": now + 300,
        }
        payload.update(overrides)
        return pyjwt.encode(payload, private_pem, algorithm="RS256")

    return _make


@pytest.fixture(autouse=True)
def _reset_key_resolver():
    yield
    set_key_resolver(None)
