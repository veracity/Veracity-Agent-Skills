"""FastAPI application factory.

Picks the authentication strategy from settings (``AUTH_STRATEGY=oidc|jwt``) — a real
project uses exactly one (single-strategy-per-project). The reference app supports both
so each flow can be validated.

Pipeline order (mirrors the .NET middleware ordering):
  SecurityHeaders -> (Session, for OIDC) -> routers (auth + protected) -> health
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app import health
from app.auth import jwt as jwt_auth
from app.auth import oidc as oidc_auth
from app.security_headers import SecurityHeadersMiddleware
from app.settings import Settings, get_settings
from app.veracity import routes as veracity_routes


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="Veracity Python Backend (reference)",
        version="0.1.0",
        description="Reference FastAPI app integrating with Veracity Identity.",
    )

    # Security headers on every response (added first => outermost).
    app.add_middleware(SecurityHeadersMiddleware)

    # Health endpoints — always anonymous.
    app.include_router(health.router)

    if settings.auth_strategy == "oidc":
        # Signed-cookie session for the BFF. __Host- prefix requires Secure + path "/".
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.session_secret,
            session_cookie="__Host-session" if settings.cookie_secure else "session",
            https_only=settings.cookie_secure,
            same_site="lax",
        )
        oidc_auth.init_oauth(settings)
        app.include_router(oidc_auth.router)
        # Veracity Platform API proxy (/api/v1/veracity/...) consumed by veracity-auth-ui.
        app.include_router(veracity_routes.router)
    else:
        # Stateless JWT Bearer. A protected sample router demonstrates the guard.
        protected = APIRouter(prefix="/v1", tags=["protected"])

        @protected.get("/me", summary="Current principal (JWT)")
        async def me(user: jwt_auth.Principal = Depends(jwt_auth.require_user)):
            return {"id": user.subject, "name": user.name}

        app.include_router(protected)

    return app


app = create_app()
