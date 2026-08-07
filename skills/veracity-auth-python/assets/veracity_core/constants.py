"""Veracity B2C tenant + Platform API constants (framework-agnostic).

All environments default to the **Production** Veracity B2C tenant (the same posture as
the .NET skills). Test/Staging values are provided for explicit overrides only.
"""

from __future__ import annotations

# --- Veracity Production B2C constants ---------------------------------------
VERACITY_INSTANCE = "https://login.veracity.com"
VERACITY_DOMAIN = "dnvglb2cprod.onmicrosoft.com"
VERACITY_POLICY = "B2C_1A_Identity"
VERACITY_TENANT_ID = "a68572e3-63ce-4bc1-acdc-b64943502e9d"
VERACITY_AUTHORITY = f"{VERACITY_INSTANCE}/{VERACITY_DOMAIN}/{VERACITY_POLICY}/v2.0"
VERACITY_OIDC_METADATA_URL = f"{VERACITY_AUTHORITY}/.well-known/openid-configuration"
VERACITY_LOGOUT_URI = "https://www.veracity.com/auth/logout"

# Veracity Platform APIs
VERACITY_API_V4_BASE = "https://api.veracity.com/veracity/graph/v4"
VERACITY_API_V3_BASE = "https://api.veracity.com/veracity/services/v3"
VERACITY_DEFAULT_SCOPE = (
    "https://dnvglb2cprod.onmicrosoft.com/"
    "83054ebf-1d7b-43f5-82ad-b2bde84d7b75/user_impersonation"
)
