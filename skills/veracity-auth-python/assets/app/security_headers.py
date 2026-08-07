"""Security headers middleware — analog of the .NET SecurityHeadersMiddleware.

Adds CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy and
Permissions-Policy to every response. CSP defaults align with the Veracity
defaults used by the .NET skill (allow the Veracity CDN).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

DEFAULT_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https://*.veracity.com; "
    "style-src 'self' 'unsafe-inline' https://*.veracity.com; "
    "script-src 'self' https://*.veracity.com; "
    "connect-src 'self' https://*.veracity.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self' https://login.veracity.com"
)


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
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if self._hsts:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
