"""URL patterns for the Veracity Django adapter.

Include from the project's root urls.py::

    path("", include("veracity_django.urls")),

The OIDC (BFF) endpoints are only meaningful for a web-app strategy; for a stateless DRF
API you typically expose only the health views and secure your own routes with
``VeracityJWTAuthentication`` instead.
"""

from __future__ import annotations

from django.urls import path

from veracity_django import health, oidc, veracity_api

urlpatterns = [
    # OIDC BFF (web app)
    path("auth", oidc.auth_status, name="veracity_auth_status"),
    path("auth/challenge", oidc.challenge, name="veracity_challenge"),
    path("auth/callback", oidc.callback, name="veracity_callback"),
    path("api/me", oidc.me, name="veracity_me"),
    path("signout", oidc.sign_out, name="veracity_sign_out"),
    # Veracity Platform API proxy (/api/v1/veracity/...) consumed by veracity-auth-ui
    path("api/v1/veracity/v3/services", veracity_api.v3_services, name="veracity_v3_services"),
    path(
        "api/v1/veracity/v3/policy/validate",
        veracity_api.v3_policy_validate,
        name="veracity_v3_policy_validate",
    ),
    path(
        "api/v1/veracity/v4/me/applications",
        veracity_api.v4_applications,
        name="veracity_v4_applications",
    ),
    path(
        "api/v1/veracity/v4/policy/validate",
        veracity_api.v4_policy_validate,
        name="veracity_v4_policy_validate",
    ),
    # Health (both strategies)
    path("health", health.health, name="veracity_health"),
    path("health/ready", health.ready, name="veracity_health_ready"),
    path("health/live", health.live, name="veracity_health_live"),
]
