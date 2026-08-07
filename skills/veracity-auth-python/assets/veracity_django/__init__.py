"""Django adapter for Veracity Identity.

Thin Django wiring over :mod:`veracity_core`. Drop this package (plus ``veracity_core``)
into an existing Django project and add ``veracity_django`` to ``INSTALLED_APPS``.

  * :mod:`veracity_django.oidc`       — Authlib BFF views (/auth, /auth/challenge,
    /auth/callback, /api/me, /signout) backed by Django's server-side session, plus the
    Veracity Platform API proxy views (/api/v1/veracity/...) for the veracity-auth-ui SPA.
  * :mod:`veracity_django.jwt`        — DRF ``VeracityJWTAuthentication`` (primary) and a
    plain-Django ``@require_user`` decorator (for non-DRF views).
  * :mod:`veracity_django.middleware` — security-headers middleware.
  * :mod:`veracity_django.health`     — anonymous health views.
  * :mod:`veracity_django.urls`       — ready-to-include URL patterns.
"""

from __future__ import annotations
