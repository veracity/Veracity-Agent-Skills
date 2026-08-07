"""FastAPI Veracity API client shim.

The httpx auth layer and MSAL token providers now live in the framework-agnostic core
(:mod:`veracity_core.apiclient`, :mod:`veracity_core.obo`). This module re-exports them
so existing imports (``from app.veracity.client import VeracityAuth``) keep working.
"""

from __future__ import annotations

from veracity_core.apiclient import (  # noqa: F401
    VeracityAuth,
    make_v3_client,
    make_v4_client,
)
from veracity_core.obo import (  # noqa: F401
    TokenProvider,
    build_client_credentials_token_provider,
    build_obo_token_provider,
)

__all__ = [
    "VeracityAuth",
    "make_v3_client",
    "make_v4_client",
    "TokenProvider",
    "build_obo_token_provider",
    "build_client_credentials_token_provider",
]
