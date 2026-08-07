"""Health check endpoints — operational necessities, always anonymous.

Mirrors the .NET baseline's /health, /health/ready, /health/live.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Overall health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/health/ready", summary="Readiness probe")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/health/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    return {"status": "alive"}
