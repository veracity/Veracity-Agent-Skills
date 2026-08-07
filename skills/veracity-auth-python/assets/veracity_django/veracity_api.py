"""Django views proxying the Veracity Platform API for the signed-in BFF user.

Exposes the endpoints the **veracity-auth-ui** SPA calls, wired up in
:mod:`veracity_django.urls` under the versioned mount the frontend expects:

    GET /api/v1/veracity/v3/services         -> the user's Veracity services (V3)
    GET /api/v1/veracity/v3/policy/validate   -> Veracity-wide policy/subscription check (V3)
    GET /api/v1/veracity/v4/me/applications   -> the user's licensed applications (V4)
    GET /api/v1/veracity/v4/policy/validate   -> policy/subscription check for the configured service (V4)

Generate only the endpoints for the API version the user chose (V3 **or** V4). Both
``policy/validate`` variants validate the signed-in user's policies, but V4 is service-specific
and needs ``SERVICE_ID`` while V3 is Veracity-wide and needs no service id; keep just the one
matching the chosen version.
"""

from __future__ import annotations

from django.http import JsonResponse

from veracity_core.proxy import (
    VeracityApiError,
    get_my_applications,
    get_my_services,
    validate_policy_v3,
    validate_policy_v4,
)
from veracity_core.settings import get_settings


def _user_token(request):
    if request.session.get("user") is None:
        return None
    return request.session.get("access_token")


def v3_services(request):
    token = _user_token(request)
    if not token:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    try:
        return JsonResponse(get_my_services(get_settings(), token), safe=False)
    except VeracityApiError as exc:
        return JsonResponse({"detail": exc.detail}, status=exc.status_code)


def v4_applications(request):
    token = _user_token(request)
    if not token:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    try:
        return JsonResponse(get_my_applications(get_settings(), token), safe=False)
    except VeracityApiError as exc:
        return JsonResponse({"detail": exc.detail}, status=exc.status_code)


def v3_policy_validate(request):
    token = _user_token(request)
    if not token:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    return_url = request.build_absolute_uri("/").rstrip("/")
    try:
        result = validate_policy_v3(get_settings(), token, return_url)
    except VeracityApiError as exc:
        return JsonResponse({"detail": exc.detail}, status=exc.status_code)
    return JsonResponse(result, status=(200 if result["compliant"] else 406))


def v4_policy_validate(request):
    token = _user_token(request)
    if not token:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    return_url = request.build_absolute_uri("/").rstrip("/")
    try:
        result = validate_policy_v4(get_settings(), token, return_url)
    except VeracityApiError as exc:
        return JsonResponse({"detail": exc.detail}, status=exc.status_code)
    return JsonResponse(result, status=(200 if result["compliant"] else 406))
