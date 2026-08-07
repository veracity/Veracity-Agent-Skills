"""Flask JWT bearer adapter — analog of the FastAPI app/auth/jwt.py.

Validation lives in :mod:`veracity_core.tokens`; this module only adapts it to Flask as
a ``@require_user`` decorator. A protected view is guarded with::

    @app.get("/v1/me")
    @require_user
    def me():
        return jsonify({"id": g.principal.subject, "name": g.principal.name})

Missing/invalid tokens produce a 401 JSON response with ``WWW-Authenticate: Bearer`` —
never a redirect, correct for an API.
"""

from __future__ import annotations

from functools import wraps

from flask import current_app, g, jsonify, request

from veracity_core.settings import Settings, get_settings
from veracity_core.tokens import AuthError, authenticate_bearer


def _settings() -> Settings:
    return current_app.extensions.get("veracity_settings") or get_settings()


def require_user(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            principal = authenticate_bearer(request.headers.get("Authorization"), _settings())
        except AuthError as exc:
            response = jsonify({"detail": exc.detail})
            response.status_code = exc.status_code
            response.headers["WWW-Authenticate"] = "Bearer"
            return response
        g.principal = principal
        return view(*args, **kwargs)

    return wrapper
