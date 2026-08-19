"""Application configuration via pydantic-settings (shared across FastAPI/Flask/Django).

Mirrors the .NET appsettings + IOptions pattern. Values are read from environment
variables and an optional .env file (the local analog of dotnet user-secrets).

Secrets (CLIENT_SECRET, SUBSCRIPTION_KEY, SESSION_SECRET) must NEVER be committed.
Locally they live in .env (gitignored); in deployed environments they are injected
from Azure Key Vault / pipeline variables.

Every web framework in this skill reads the same ``Settings`` model, so the Veracity
constants and derived URLs (jwks_uri, issuer) live in exactly one place.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from veracity_core.constants import (
    VERACITY_API_V3_BASE,
    VERACITY_API_V4_BASE,
    VERACITY_AUTHORITY,
    VERACITY_DEFAULT_SCOPE,
    VERACITY_INSTANCE,
    VERACITY_LOGOUT_URI,
    VERACITY_TENANT_ID,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["Development", "Test", "Stag", "Prod"] = "Development"
    app_host: str = "localhost"
    app_port: int = 54438
    https_cert_file: str = ".certs/localhost.pem"
    https_key_file: str = ".certs/localhost-key.pem"

    # Which authentication strategy this instance runs. A real project picks one
    # (single-strategy-per-project, like the .NET skill); the reference app supports
    # both so we can validate each flow.
    auth_strategy: Literal["oidc", "jwt"] = "oidc"

    # --- OIDC (BFF) ----------------------------------------------------------
    client_id: str = Field(default="", description="Veracity app registration Client ID")
    client_secret: str = Field(default="", description="Secret — from .env / Key Vault only")
    oidc_scopes: str = "openid profile email offline_access"
    # HTTP timeout (seconds) for Authlib's calls to the Veracity B2C discovery/metadata
    # and token endpoints. Raised above httpx's 5s default so a slow network or a
    # corporate/VPN proxy's TLS handshake doesn't fail the login with a ConnectTimeout.
    oidc_http_timeout: float = 30.0
    logout_redirect_uri: str = VERACITY_LOGOUT_URI
    # Absolute OIDC callback (redirect) URL registered with Veracity B2C — the analog of
    # the .NET skill's `Veracity:CallbackPath`. When a SPA (veracity-auth-ui) talks to this
    # BFF through the Vite dev proxy, set this to the *frontend* origin so B2C returns the
    # browser to the same origin that holds the session cookie, e.g.
    #   REDIRECT_URI=https://localhost:5173/auth/callback
    # Leave empty to derive the callback from the incoming request (backend-hosted SPA/prod
    # behind a single origin). The path segment must stay `/auth/callback` to match the Vite
    # proxy in veracity-auth-ui.
    redirect_uri: str = Field(default="")
    # Used to sign the session cookie (Starlette / Flask / Django session). Secret — must be
    # supplied via .env / Key Vault, NEVER a hard-coded default (CWE-259). Empty by default so no
    # credential lives in source; required + validated for OIDC below (fails fast if missing/weak).
    session_secret: str = Field(default="")
    # __Host- prefix requires Secure + path=/ + no Domain. Keep this true for local HTTPS dev.
    cookie_secure: bool = True

    # --- JWT bearer validation ----------------------------------------------
    # Audience = the API's own app-registration Client ID (the `aud` claim).
    jwt_audience: str = Field(default="", description="API app registration Client ID")
    jwt_authority: str = VERACITY_AUTHORITY
    jwt_leeway_seconds: int = 60  # matches the .NET skill's 1-minute clock skew

    # --- Veracity API client -------------------------------------------------
    api_v4_base_url: str = VERACITY_API_V4_BASE
    api_v3_base_url: str = VERACITY_API_V3_BASE
    veracity_scope: str = VERACITY_DEFAULT_SCOPE
    # The Veracity service this app is connected to. Used **only** by the V4 policy/validate
    # endpoint (``POST /me/policy-verifications/{serviceId}``) to check the signed-in user's
    # subscription and service-specific terms. V3 policy validation is Veracity-wide and does not
    # use it. Not a secret; analog of the .NET skill's top-level ``ServiceId``. Leave empty for
    # V3-only projects or when V4 policy validation is unused.
    service_id: str = Field(default="", description="Veracity service ID (V4 policy/validate only)")
    # Ocp-Apim-Subscription-Key — secret, from .env / Key Vault only.
    subscription_key: str = Field(default="")

    @property
    def login_scopes(self) -> str:
        """Scopes requested at OIDC login.

        Combines the OIDC scopes with the Veracity Platform API scope so the
        authorization-code exchange returns an access token already scoped for
        ``api.veracity.com`` (mirrors Microsoft.Identity.Web / the .NET skill). No
        on-behalf-of exchange is then needed. The Veracity app registration must be
        authorized for this API scope. Leave ``veracity_scope`` empty for a login-only
        BFF that never calls the Veracity API.
        """
        parts = [self.oidc_scopes]
        if self.veracity_scope:
            parts.append(self.veracity_scope)
        return " ".join(p for p in parts if p)

    @property
    def jwks_uri(self) -> str:
        # Veracity B2C JWKS endpoint derived from the authority.
        return f"{self.jwt_authority}/discovery/v2.0/keys"

    @property
    def issuer(self) -> str:
        # v2.0 issuer format for B2C.
        return f"{VERACITY_INSTANCE}/{VERACITY_TENANT_ID}/v2.0/"

    @model_validator(mode="after")
    def _require_session_secret_for_oidc(self) -> "Settings":
        # Fail fast instead of falling back to a hard-coded default (CWE-259). The session
        # signing key is only needed for the OIDC (cookie-session) strategy.
        if self.auth_strategy == "oidc" and len(self.session_secret) < 32:
            raise ValueError(
                "SESSION_SECRET must be set to a strong value (>= 32 chars) for the OIDC "
                "strategy. Provide it via .env (local) or Key Vault / environment (deployed); "
                "never hard-code a fallback."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
