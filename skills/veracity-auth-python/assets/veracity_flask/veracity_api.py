"""Flask blueprint proxying the Veracity Platform API for the signed-in BFF user.

Exposes the endpoints the **veracity-auth-ui** SPA calls, under the versioned mount the
frontend expects (see :data:`veracity_core.proxy.VERACITY_API_MOUNT`):

    GET /api/v1/veracity/v3/services         -> the user's Veracity services (V3)
    GET /api/v1/veracity/v3/policy/validate   -> Veracity-wide policy/subscription check (V3)
    GET /api/v1/veracity/v4/me/applications   -> the user's licensed applications (V4)
    GET /api/v1/veracity/v4/policy/validate   -> policy/subscription check for the configured service (V4)

Generate only the endpoints for the API version the user chose (V3 **or** V4). Both
``policy/validate`` variants validate the signed-in user's policies, but V4 is service-specific
and needs ``SERVICE_ID`` while V3 is Veracity-wide and needs no service id; keep just the one
matching the chosen version.

Registered automatically by :func:`veracity_flask.oidc.init_veracity_oidc`.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, session

from veracity_core.proxy import (
    VERACITY_API_MOUNT,
    VeracityApiError,
    get_my_applications,
    get_my_services,
    validate_policy_v3,
    validate_policy_v4,
)
from veracity_core.settings import get_settings

bp = Blueprint("veracity_api", __name__, url_prefix=VERACITY_API_MOUNT)


def _settings():
    return current_app.extensions.get("veracity_settings") or get_settings()


def _user_token():
    if session.get("user") is None:
        return None
    return session.get("access_token")


@bp.get("/v3/services")
def v3_services():
    token = _user_token()
    if not token:
        return jsonify({"detail": "Not authenticated"}), 401
    try:
        return jsonify(get_my_services(_settings(), token))
    except VeracityApiError as exc:
        return jsonify({"detail": exc.detail}), exc.status_code


@bp.get("/v4/me/applications")
def v4_applications():
    token = _user_token()
    if not token:
        return jsonify({"detail": "Not authenticated"}), 401
    try:
        return jsonify(get_my_applications(_settings(), token))
    except VeracityApiError as exc:
        return jsonify({"detail": exc.detail}), exc.status_code


@bp.get("/v3/policy/validate")
def v3_policy_validate():
    token = _user_token()
    if not token:
        return jsonify({"detail": "Not authenticated"}), 401
    return_url = request.host_url.rstrip("/")
    try:
        result = validate_policy_v3(_settings(), token, return_url)
    except VeracityApiError as exc:
        return jsonify({"detail": exc.detail}), exc.status_code
    return jsonify(result), (200 if result["compliant"] else 406)


@bp.get("/v4/policy/validate")
def v4_policy_validate():
    token = _user_token()
    if not token:
        return jsonify({"detail": "Not authenticated"}), 401
    return_url = request.host_url.rstrip("/")
    try:
        result = validate_policy_v4(_settings(), token, return_url)
    except VeracityApiError as exc:
        return jsonify({"detail": exc.detail}), exc.status_code
    return jsonify(result), (200 if result["compliant"] else 406)
