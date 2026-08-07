"""Reference Flask application factory wiring the Veracity adapter together.

Shows the middleware/route ordering for a single-strategy project (``AUTH_STRATEGY``):

  security headers -> health -> (OIDC blueprint) OR (JWT-protected sample route)

In an existing Flask app you typically call ``register_security_headers(app)`` and either
``init_veracity_oidc(app)`` (BFF) or apply ``@require_user`` to your API views — you do
not need this factory.
"""

from __future__ import annotations

from flask import Flask, g, jsonify

from veracity_core.settings import Settings, get_settings
from veracity_flask import health, security
from veracity_flask import jwt as jwt_auth
from veracity_flask import oidc


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()

    app = Flask(__name__)
    security.register_security_headers(app)
    app.register_blueprint(health.bp)

    if settings.auth_strategy == "oidc":
        oidc.init_veracity_oidc(app, settings)
    else:
        app.extensions["veracity_settings"] = settings

        @app.get("/v1/me")
        @jwt_auth.require_user
        def me():
            return jsonify({"id": g.principal.subject, "name": g.principal.name})

    return app


app = create_app()
