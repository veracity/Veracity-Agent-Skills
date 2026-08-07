"""Framework-agnostic JWT validation for Veracity B2C access tokens.

Analog of the .NET AddJwtBearerAuthentication. Validates tokens issued by the Veracity
B2C tenant:
  * signature against the B2C JWKS endpoint (PyJWKClient)
  * issuer, audience, expiry
  * 60s leeway (matches the skill's tighter-than-default clock skew)

This module has **no web-framework imports**. Each adapter (FastAPI dependency, Flask
decorator, Django/DRF authentication class) calls ``authenticate_bearer`` and translates
an :class:`AuthError` into that framework's 401 response.

The signing-key resolution is injectable (``set_key_resolver``) so unit tests can verify
the accept/reject logic with a locally generated RSA keypair, without calling B2C.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import jwt

from veracity_core.settings import Settings

# Resolves the verification key (PEM/JWK) for a given raw token.
KeyResolver = Callable[[str], object]


@dataclass
class Principal:
    """The authenticated caller, independent of any framework user model."""

    subject: str
    name: Optional[str] = None
    claims: dict = field(default_factory=dict)


class AuthError(Exception):
    """Framework-neutral authentication failure. Adapters map this to a 401 response."""

    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _b2c_key_resolver(settings: Settings) -> KeyResolver:
    """Production resolver: fetch the signing key from the Veracity B2C JWKS endpoint."""
    client = jwt.PyJWKClient(settings.jwks_uri)

    def resolve(token: str) -> object:
        return client.get_signing_key_from_jwt(token).key

    return resolve


# Module-level resolver hook. Production wires _b2c_key_resolver; tests override it.
_key_resolver: Optional[KeyResolver] = None


def set_key_resolver(resolver: Optional[KeyResolver]) -> None:
    global _key_resolver
    _key_resolver = resolver


def _resolver(settings: Settings) -> KeyResolver:
    return _key_resolver or _b2c_key_resolver(settings)


def decode_token(token: str, settings: Settings) -> dict:
    """Decode and validate a Veracity B2C access token. Raises jwt exceptions on failure."""
    key = _resolver(settings)(token)
    return jwt.decode(
        token,
        key=key,
        algorithms=["RS256"],
        audience=settings.jwt_audience or None,
        issuer=settings.issuer if settings.jwt_audience else None,
        leeway=settings.jwt_leeway_seconds,
        options={
            "require": ["exp", "iat"],
            "verify_aud": bool(settings.jwt_audience),
            "verify_iss": bool(settings.jwt_audience),
        },
    )


def principal_from_claims(claims: dict) -> Principal:
    return Principal(subject=claims.get("sub", ""), name=claims.get("name"), claims=claims)


def extract_bearer(authorization: Optional[str]) -> Optional[str]:
    """Return the token from an ``Authorization`` bearer header value, or None."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


def authenticate_bearer(authorization: Optional[str], settings: Settings) -> Principal:
    """Validate the bearer token from an Authorization header value.

    Raises :class:`AuthError` (status 401) for a missing or invalid token; adapters
    translate it to a framework-appropriate ``401`` with ``WWW-Authenticate: Bearer``.
    """
    token = extract_bearer(authorization)
    if not token:
        raise AuthError("Missing bearer token")
    try:
        claims = decode_token(token, settings)
    except jwt.PyJWTError as exc:  # signature/issuer/audience/expiry failures
        raise AuthError(f"Invalid token: {exc}") from exc
    return principal_from_claims(claims)
