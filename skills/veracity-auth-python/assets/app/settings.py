"""FastAPI settings shim — the canonical model now lives in :mod:`veracity_core.settings`.

Kept so existing imports (``from app.settings import Settings, get_settings``) and the
Veracity constants continue to work while the shared logic is framework-agnostic.
"""

from __future__ import annotations

from veracity_core.constants import (  # noqa: F401  (re-exported for convenience)
    VERACITY_API_V3_BASE,
    VERACITY_API_V4_BASE,
    VERACITY_AUTHORITY,
    VERACITY_DEFAULT_SCOPE,
    VERACITY_DOMAIN,
    VERACITY_INSTANCE,
    VERACITY_LOGOUT_URI,
    VERACITY_OIDC_METADATA_URL,
    VERACITY_POLICY,
    VERACITY_TENANT_ID,
)
from veracity_core.settings import Settings, get_settings  # noqa: F401

__all__ = [
    "Settings",
    "get_settings",
    "VERACITY_INSTANCE",
    "VERACITY_DOMAIN",
    "VERACITY_POLICY",
    "VERACITY_TENANT_ID",
    "VERACITY_AUTHORITY",
    "VERACITY_OIDC_METADATA_URL",
    "VERACITY_LOGOUT_URI",
    "VERACITY_API_V4_BASE",
    "VERACITY_API_V3_BASE",
    "VERACITY_DEFAULT_SCOPE",
]
