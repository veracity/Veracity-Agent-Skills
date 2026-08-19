"""Application configuration via pydantic-settings.

The Python analog of the .NET ``appsettings`` + ``IOptions`` pattern. Values are read from
environment variables and an optional ``.env`` file (the local analog of
``dotnet user-secrets``).

This is the **baseline** settings model — it carries only the generic web-backend concerns
(environment, host/port, local HTTPS certificate paths, and the Content-Security-Policy).
It intentionally contains **no authentication or provider-specific fields**; auth skills
(for example ``veracity-auth-python``) extend this model when they layer authentication on
top of the baseline.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Locked-down Content-Security-Policy mirroring the web-backend-net / web-backend-node baseline
# (base-uri 'none', 'self'-only sources, no external hosts), with intentionally *stricter*
# framing than .NET: frame-ancestors 'none' (paired with X-Frame-Options: DENY). Auth skills
# extend these sources when they add their own CDN / login endpoints.
DEFAULT_CSP = (
    "base-uri 'none'; "
    "default-src 'self'; "
    "connect-src 'self'; "
    "script-src 'self'; "
    "font-src 'self' data:; "
    "media-src 'self'; "
    "worker-src 'self' blob:; "
    "img-src 'self' data:; "
    "frame-src 'none'; "
    "style-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["Development", "Test", "Stag", "Prod"] = "Development"
    app_host: str = "localhost"
    app_port: int = 54438

    # Local HTTPS certificate/key used by the dev server. Generate a trusted localhost
    # certificate (for example with mkcert) and point these at the generated files.
    https_cert_file: str = ".certs/localhost.pem"
    https_key_file: str = ".certs/localhost-key.pem"

    # Content-Security-Policy applied by SecurityHeadersMiddleware to every response.
    content_security_policy: str = DEFAULT_CSP


@lru_cache
def get_settings() -> Settings:
    return Settings()
