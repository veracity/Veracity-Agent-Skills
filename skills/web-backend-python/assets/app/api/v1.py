"""Versioned API router — the seam new endpoints hang off.

The Python analog of the .NET baseline's versioned ``apiGroup``
(``MapGroup("/api/v{version:apiVersion}")``). All application endpoints should be mounted
on this router so they share a stable ``/api/v1`` prefix and OpenAPI tag.

The group is **unauthenticated** in the baseline scaffold. An auth skill
(for example ``veracity-auth-python``) protects it later by adding an auth dependency to
the router and marking specific public endpoints anonymous.

Add new endpoints here (or in feature modules that expose their own ``APIRouter`` and are
included on this one). See ``references/new-endpoints.md``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/ping", summary="Sample versioned endpoint")
async def ping() -> dict[str, str]:
    """A placeholder endpoint proving the versioned group is wired. Replace or remove it."""
    return {"message": "pong"}
