"""Django OpenID Connect (BFF) views — analog of the FastAPI app/auth/oidc.py.

Uses Authlib's Django integration and Django's session for state:

  GET /auth/challenge?returnUrl=  -> redirect to Veracity login (Auth Code + PKCE)
  GET /auth/callback                -> exchange code, store user + tokens in session
  GET /auth                       -> { "result": <signed-in bool> }   (anonymous)
  GET /api/me                     -> current user info                (requires session)
  GET /signout                    -> clear session, redirect to Veracity logout

Django's session framework is server-side by default (database/cache backend), so the
BFF token state is not size-limited the way a signed cookie is — a natural fit for the
multi-instance posture described in references/frameworks/django.md.

Any unauthenticated request to /api/* returns 401 (not a login redirect).
"""

from __future__ import annotations

from authlib.integrations.django_client import OAuth
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse

from veracity_core.constants import VERACITY_OIDC_METADATA_URL
from veracity_core.settings import Settings, get_settings

oauth = OAuth()


def _client(settings: Settings):
    if "veracity" not in oauth._registry:  # idempotent registration
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
    return oauth.veracity


def auth_status(request):
    return JsonResponse({"result": "user" in request.session})


def challenge(request):
    settings = get_settings()
    request.session["return_url"] = request.GET.get("returnUrl", "/")
    # Prefer the configured redirect URI (e.g. the Vite proxy origin the SPA runs on) so
    # B2C returns the browser to the same origin that holds the session cookie.
    redirect_uri = settings.redirect_uri or request.build_absolute_uri(
        reverse("veracity_callback")
    )
    return _client(settings).authorize_redirect(request, redirect_uri)


def callback(request):
    settings = get_settings()
    token = _client(settings).authorize_access_token(request)
    claims = token.get("userinfo") or {}
    request.session["user"] = {
        "id": claims.get("sub") or claims.get("oid", ""),
        "displayName": claims.get("name", ""),
        "email": claims.get("email")
        or (claims.get("emails", [None])[0] if claims.get("emails") else None),
        "firstName": claims.get("given_name"),
        "lastName": claims.get("family_name"),
    }
    # Store the API-scoped access token so the Veracity API proxy views can call the
    # Platform API as the signed-in user (the login request included the Veracity API
    # scope, so no on-behalf-of exchange is needed). Django sessions are server-side by
    # default, so the refresh token can safely be kept here for future silent refresh.
    if "access_token" in token:
        request.session["access_token"] = token["access_token"]
    if "refresh_token" in token:
        request.session["refresh_token"] = token["refresh_token"]
    return HttpResponseRedirect(request.session.pop("return_url", "/"))


def me(request):
    user = request.session.get("user")
    if user is None:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    return JsonResponse(user)


def sign_out(request):
    request.session.flush()
    return HttpResponseRedirect(get_settings().logout_redirect_uri)
