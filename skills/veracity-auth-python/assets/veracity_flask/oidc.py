"""Flask OpenID Connect (BFF) — analog of the FastAPI app/auth/oidc.py.

Implements the Backend-for-Frontend pattern against the Veracity B2C tenant using
Authlib's Flask integration and the Flask session for state:

  GET /auth/challenge?returnUrl=  -> redirect to Veracity login (Auth Code + PKCE)
  GET /auth/callback                -> exchange code, store user + tokens in session
  GET /auth                       -> { "result": <signed-in bool> }   (anonymous)
  GET /api/me                     -> current user info                (requires session)
  GET /signout                    -> clear session, redirect to Veracity logout

The signed Flask session cookie holds state (Flask signs it with SECRET_KEY). For
multi-instance deployments switch to a server-side store (e.g. Flask-Session + Redis) —
see references/frameworks/flask.md.

Any unauthenticated request to /api/* returns 401 (not a login redirect), so API/XHR
callers get a machine-readable error.
"""

from __future__ import annotations

from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint,
    Flask,
    current_app,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)

from veracity_core.constants import VERACITY_OIDC_METADATA_URL
from veracity_core.redirects import safe_return_url
from veracity_core.settings import Settings, get_settings
from veracity_flask import veracity_api

oauth = OAuth()
bp = Blueprint("veracity_auth", __name__)


def init_veracity_oidc(app: Flask, settings: Settings | None = None) -> None:
    """Register the Veracity OIDC client + auth blueprint on an existing Flask app."""
    settings = settings or get_settings()

    # Flask signs the session cookie with SECRET_KEY; keep it a real secret in prod.
    # Direct assignment is required — Flask pre-populates SECRET_KEY as None, so
    # setdefault() would find the key already present and silently skip the update.
    app.config["SECRET_KEY"] = settings.session_secret
    app.config.update(
        SESSION_COOKIE_SECURE=settings.cookie_secure,
        SESSION_COOKIE_HTTPONLY=True,
        # "Lax" lets the cookie survive the top-level redirect back from B2C.
        SESSION_COOKIE_SAMESITE="Lax",
    )
    app.extensions["veracity_settings"] = settings

    oauth.init_app(app)
    if "veracity" not in oauth._registry:  # idempotent
        oauth.register(
            name="veracity",
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            server_metadata_url=VERACITY_OIDC_METADATA_URL,
            client_kwargs={
                "scope": settings.login_scopes,
                # Generous timeout so the B2C metadata/token fetch survives a slow network
                # or a corporate/VPN proxy TLS handshake (httpx defaults to only 5s).
                "timeout": settings.oidc_http_timeout,
            },
        )

    app.register_blueprint(bp)
    app.register_blueprint(veracity_api.bp)


def _settings() -> Settings:
    return current_app.extensions.get("veracity_settings") or get_settings()


@bp.get("/auth")
def auth_status():
    return jsonify({"result": "user" in session})


@bp.get("/auth/challenge")
def challenge():
    session["return_url"] = safe_return_url(request.args.get("returnUrl", "/"))
    # Prefer the configured redirect URI (e.g. the Vite proxy origin the SPA runs on) so
    # B2C returns the browser to the same origin that holds the session cookie.
    redirect_uri = _settings().redirect_uri or url_for(
        "veracity_auth.callback", _external=True
    )
    return oauth.veracity.authorize_redirect(redirect_uri)


@bp.get("/auth/callback")
def callback():
    token = oauth.veracity.authorize_access_token()
    claims = token.get("userinfo") or {}
    session["user"] = {
        "id": claims.get("sub") or claims.get("oid", ""),
        "displayName": claims.get("name", ""),
        "email": claims.get("email")
        or (claims.get("emails", [None])[0] if claims.get("emails") else None),
        "firstName": claims.get("given_name"),
        "lastName": claims.get("family_name"),
    }
    # Store the API-scoped access token so the /api/v1/veracity/* proxy can call the
    # Platform API as the signed-in user (the login request included the Veracity API
    # scope). We intentionally do NOT keep the refresh token: the signed Flask session
    # cookie is limited to ~4 KB and access_token + user already approach that. For
    # silent refresh, switch to a server-side session store (see references/frameworks/flask.md).
    if "access_token" in token:
        session["access_token"] = token["access_token"]
    return redirect(safe_return_url(session.pop("return_url", "/")))


@bp.get("/api/me")
def me():
    user = session.get("user")
    if user is None:
        # 401 for /api/* instead of a login redirect.
        return jsonify({"detail": "Not authenticated"}), 401
    return jsonify(user)


@bp.get("/signout")
def sign_out():
    session.clear()
    return redirect(_settings().logout_redirect_uri)
