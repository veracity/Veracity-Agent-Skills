"""Flask adapter for Veracity Identity.

Thin Flask wiring over :mod:`veracity_core`. Designed to be dropped into an **existing
Flask project** (copy this package plus ``veracity_core``):

  * :mod:`veracity_flask.oidc`     — Authlib BFF blueprint (/auth, /auth/challenge,
    /auth/callback, /api/me, /signout) backed by the Flask session, and the Veracity
    Platform API proxy (/api/v1/veracity/...) consumed by the veracity-auth-ui SPA.
  * :mod:`veracity_flask.jwt`      — ``@require_user`` decorator for stateless JWT APIs.
  * :mod:`veracity_flask.security` — security-headers ``after_request`` hook.
  * :mod:`veracity_flask.health`   — anonymous health blueprint.
  * :mod:`veracity_flask.dev_https`— HTTPS-first local dev runner.
  * :mod:`veracity_flask.app_factory` — reference ``create_app`` wiring it together.
"""

from __future__ import annotations
