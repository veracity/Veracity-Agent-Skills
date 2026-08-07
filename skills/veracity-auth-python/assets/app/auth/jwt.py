"""FastAPI JWT bearer adapter — thin wrapper over :mod:`veracity_core.tokens`.

The token validation itself (signature/issuer/audience/expiry, injectable key resolver)
is framework-agnostic and lives in the core. This module only adapts it to FastAPI:
a ``require_user`` dependency that a protected route declares as
``user: Principal = Depends(require_user)``. Missing or invalid tokens raise 401
(never a redirect) — correct for an API.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from veracity_core.settings import Settings, get_settings
from veracity_core.tokens import (  # noqa: F401  (re-exported for tests/back-compat)
    AuthError,
    KeyResolver,
    Principal,
    authenticate_bearer,
    decode_token,
    set_key_resolver,
)

_bearer = HTTPBearer(auto_error=False)


async def require_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> Principal:
    header = (
        f"{credentials.scheme} {credentials.credentials}"
        if credentials and credentials.credentials
        else None
    )
    try:
        return authenticate_bearer(header, settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
