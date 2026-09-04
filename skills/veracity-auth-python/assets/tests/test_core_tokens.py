"""Framework-agnostic core: bearer extraction + JWT accept/reject via veracity_core."""

from __future__ import annotations

import time

import pytest

from veracity_core.settings import Settings
from veracity_core.tokens import (
    AuthError,
    authenticate_bearer,
    extract_bearer,
    set_key_resolver,
)

AUDIENCE = "11111111-1111-1111-1111-111111111111"

# Untrusted issuer used only to assert that a token from the wrong authority is rejected.
# Uses an RFC 2606 reserved domain; the name is deliberately neutral so automated security
# scanners do not flag it as a real exfiltration endpoint.
WRONG_ISSUER = "https://wrong-issuer.example.com/"


def _settings() -> Settings:
    return Settings(jwt_audience=AUDIENCE, cookie_secure=False)


def test_extract_bearer_variants(auth_header):
    assert extract_bearer(auth_header("abc.def")) == "abc.def"
    assert extract_bearer("bearer abc.def") == "abc.def"  # scheme is case-insensitive
    assert extract_bearer(None) is None
    assert extract_bearer("") is None
    assert extract_bearer("Basic xyz") is None
    assert extract_bearer(auth_header("")) is None


def test_valid_token_accepted(rsa_keys, make_token, auth_header):
    private_pem, public_pem = rsa_keys
    settings = _settings()
    set_key_resolver(lambda _t: public_pem)
    token = make_token(private_pem, settings.jwt_audience, settings.issuer)
    principal = authenticate_bearer(auth_header(token), settings)
    assert principal.subject == "user-123"
    assert principal.name == "Test User"


def test_missing_token_rejected():
    with pytest.raises(AuthError):
        authenticate_bearer(None, _settings())


def test_expired_token_rejected(rsa_keys, make_token, auth_header):
    private_pem, public_pem = rsa_keys
    settings = _settings()
    set_key_resolver(lambda _t: public_pem)
    token = make_token(
        private_pem, settings.jwt_audience, settings.issuer, exp=int(time.time()) - 120
    )
    with pytest.raises(AuthError):
        authenticate_bearer(auth_header(token), settings)


def test_wrong_audience_rejected(rsa_keys, make_token, auth_header):
    private_pem, public_pem = rsa_keys
    settings = _settings()
    set_key_resolver(lambda _t: public_pem)
    token = make_token(private_pem, "someone-else", settings.issuer)
    with pytest.raises(AuthError):
        authenticate_bearer(auth_header(token), settings)


def test_wrong_issuer_rejected(rsa_keys, make_token, auth_header):
    private_pem, public_pem = rsa_keys
    settings = _settings()
    set_key_resolver(lambda _t: public_pem)
    token = make_token(private_pem, settings.jwt_audience, WRONG_ISSUER)
    with pytest.raises(AuthError):
        authenticate_bearer(auth_header(token), settings)
