"""FastAPI application factory (baseline, no authentication).

Pipeline order (mirrors the .NET baseline middleware ordering):
  SecurityHeaders -> ProblemDetails handlers -> health -> versioned /api/v1 router

This baseline adds no authentication, session, or provider-specific packages. The
versioned ``/api/v1`` group is not protected — protection is added later by an auth skill.
"""

from __future__ import annotations

from fastapi import FastAPI

from app import health
from app.api import v1
from app.problem_details import add_problem_details_handlers
from app.security_headers import SecurityHeadersMiddleware
from app.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="Web Backend (baseline)",
        version="0.1.0",
        description="Baseline FastAPI backend scaffold with health checks, security headers, "
        "a versioned API group, and ProblemDetails error handling. No authentication.",
    )

    # Security headers on every response (added first => outermost).
    app.add_middleware(SecurityHeadersMiddleware, csp=settings.content_security_policy)

    # Global RFC 9457 ProblemDetails error handling.
    add_problem_details_handlers(app)

    # Health endpoints — always anonymous.
    app.include_router(health.router)

    # Versioned API group — the seam future endpoints hang off. Unauthenticated in the baseline.
    app.include_router(v1.router)

    return app


app = create_app()
