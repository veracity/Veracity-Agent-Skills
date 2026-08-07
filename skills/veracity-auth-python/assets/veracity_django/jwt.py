"""Django JWT bearer adapter — analog of the FastAPI app/auth/jwt.py.

Two integration styles over the same framework-agnostic validation
(:mod:`veracity_core.tokens`):

  * **DRF (primary)** — ``VeracityJWTAuthentication`` plugs into DRF's authentication
    pipeline. Combine with ``permissions.IsAuthenticated`` on a view/router. A missing or
    invalid token yields **401** with ``WWW-Authenticate: Bearer``.
  * **Plain Django (secondary)** — ``@require_user`` decorator for function views in
    projects that don't use DRF; it sets ``request.veracity_principal`` and returns 401
    JSON on failure.
"""

from __future__ import annotations

from functools import wraps

from django.http import JsonResponse

from veracity_core.settings import get_settings
from veracity_core.tokens import AuthError, authenticate_bearer
from veracity_django.principal import VeracityUser

try:  # DRF is optional — the plain decorator works without it.
    from rest_framework import authentication, exceptions

    class VeracityJWTAuthentication(authentication.BaseAuthentication):
        """Validate a Veracity B2C bearer token for Django REST Framework."""

        def authenticate(self, request):
            header = request.META.get("HTTP_AUTHORIZATION")
            if not header:
                # No credentials: let IsAuthenticated produce a 401 (authenticate_header
                # below supplies the WWW-Authenticate challenge).
                return None
            try:
                principal = authenticate_bearer(header, get_settings())
            except AuthError as exc:
                raise exceptions.AuthenticationFailed(exc.detail)
            return (VeracityUser(principal), principal)

        def authenticate_header(self, request):
            return "Bearer"

except ImportError:  # pragma: no cover - DRF not installed
    VeracityJWTAuthentication = None  # type: ignore[assignment]


def require_user(view):
    """Plain-Django decorator alternative to the DRF authentication class."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            principal = authenticate_bearer(request.META.get("HTTP_AUTHORIZATION"), get_settings())
        except AuthError as exc:
            response = JsonResponse({"detail": exc.detail}, status=exc.status_code)
            response["WWW-Authenticate"] = "Bearer"
            return response
        request.veracity_principal = principal
        return view(request, *args, **kwargs)

    return wrapper
