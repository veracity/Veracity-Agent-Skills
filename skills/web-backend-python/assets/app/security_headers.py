"""Security headers middleware — the Python analog of the .NET SecurityHeadersMiddleware.

Adds CSP, HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection,
X-Permitted-Cross-Domain-Policies, Referrer-Policy and Permissions-Policy to every response.
The CSP is a locked-down 'self'-only policy (see ``Settings.content_security_policy`` /
``DEFAULT_CSP``) mirroring the .NET / Node baselines, and can be overridden per-environment or
extended by an auth skill. Framing is intentionally stricter than .NET: ``X-Frame-Options: DENY``
paired with ``frame-ancestors 'none'``.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.settings import DEFAULT_CSP


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, csp: str = DEFAULT_CSP, hsts: bool = True) -> None:
        super().__init__(app)
        self._csp = csp
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("Content-Security-Policy", self._csp)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("X-XSS-Protection", "0")
        headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if self._hsts:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
