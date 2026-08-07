"""Security-headers middleware for Django — analog of the FastAPI SecurityHeadersMiddleware.

Add to ``MIDDLEWARE`` (Django also ships ``SecurityMiddleware`` for HSTS/redirects; this
adds the CSP + related headers with the Veracity-aligned defaults). Place it high in the
list so the headers apply to every response.
"""

from __future__ import annotations

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

_HEADERS = {
    "Content-Security-Policy": DEFAULT_CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class VeracitySecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for key, value in _HEADERS.items():
            response.setdefault(key, value)
        return response
