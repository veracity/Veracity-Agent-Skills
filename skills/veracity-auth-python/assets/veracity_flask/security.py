"""Security-headers hook for Flask — analog of the FastAPI SecurityHeadersMiddleware.

Adds CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy and
Permissions-Policy to every response. CSP defaults align with the Veracity defaults used
by the .NET/FastAPI skills (allow the Veracity CDN).
"""

from __future__ import annotations

from flask import Flask

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


def register_security_headers(app: Flask, csp: str = DEFAULT_CSP, hsts: bool = True) -> None:
    @app.after_request
    def _add_headers(response):
        headers = response.headers
        headers.setdefault("Content-Security-Policy", csp)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if hsts:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
