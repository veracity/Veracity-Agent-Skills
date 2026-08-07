"""FastAPI routes that proxy the Veracity Platform API for the signed-in BFF user.

Exposes exactly the endpoints the **veracity-auth-ui** SPA calls (see its
``src/api/veracity.ts``), under the versioned mount the frontend expects:

    GET /api/v1/veracity/v3/services         -> the user's Veracity services (V3)
    GET /api/v1/veracity/v3/policy/validate   -> Veracity-wide policy/subscription check (V3)
    GET /api/v1/veracity/v4/me/applications   -> the user's licensed applications (V4)
    GET /api/v1/veracity/v4/policy/validate   -> policy/subscription check for the configured service (V4)

Generate only the endpoints for the API version the user chose (V3 **or** V4). Both
``policy/validate`` variants validate the signed-in user's policies, but V4 is service-specific
and needs ``SERVICE_ID`` while V3 is Veracity-wide and needs no service id; keep just the one
matching the chosen version.

The heavy lifting (OBO token exchange + subscription key) lives in
:mod:`veracity_core.proxy`; these routes only read the user's access token from the BFF
session and translate a :class:`~veracity_core.proxy.VeracityApiError` into an HTTP error.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.settings import Settings, get_settings
from veracity_core.proxy import (
    VERACITY_API_MOUNT,
    VeracityApiError,
    get_my_applications,
    get_my_services,
    validate_policy_v3,
    validate_policy_v4,
)

router = APIRouter(prefix=VERACITY_API_MOUNT, tags=["veracity-api"])


def _user_token(request: Request) -> str:
    if request.session.get("user") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    token = request.session.get("access_token")
    if not token:
        # Session cookie is valid but the downstream token lapsed — surface a 401 so the
        # SPA silently re-challenges (matches the .NET token-cache-recovery behaviour).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Veracity access token in session",
        )
    return token


@router.get("/v3/services", summary="Current user's Veracity services (V3)")
async def v3_services(request: Request, settings: Settings = Depends(get_settings)):
    try:
        return get_my_services(settings, _user_token(request))
    except VeracityApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/v4/me/applications", summary="Current user's applications (V4)")
async def v4_applications(request: Request, settings: Settings = Depends(get_settings)):
    try:
        return get_my_applications(settings, _user_token(request))
    except VeracityApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/v3/policy/validate", summary="Validate the current user's policies (V3)")
async def v3_policy_validate(
    request: Request, response: Response, settings: Settings = Depends(get_settings)
):
    return_url = str(request.base_url).rstrip("/")
    try:
        result = validate_policy_v3(settings, _user_token(request), return_url)
    except VeracityApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    if not result["compliant"]:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
    return result


@router.get("/v4/policy/validate", summary="Validate the current user's policies (V4)")
async def v4_policy_validate(
    request: Request, response: Response, settings: Settings = Depends(get_settings)
):
    return_url = str(request.base_url).rstrip("/")
    try:
        result = validate_policy_v4(settings, _user_token(request), return_url)
    except VeracityApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    if not result["compliant"]:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
    return result
