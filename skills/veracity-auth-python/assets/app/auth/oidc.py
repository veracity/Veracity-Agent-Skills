"""OpenID Connect BFF strategy — analog of the .NET AddAppAuthentications + AuthEndpoints.

Implements the Backend-for-Frontend pattern against the Veracity B2C tenant:

  GET /auth/challenge?returnUrl=  -> redirect to Veracity login (Auth Code + PKCE)
  GET /auth/callback              -> exchange code, store user + tokens in session
  GET /auth                       -> { "result": <signed-in bool> }   (anonymous)
  GET /api/me                     -> current user info                (requires session)
  GET /signout                    -> clear session, redirect to Veracity logout

Session state is held in a signed cookie (Starlette SessionMiddleware). For multi-instance
deployments swap in a server-side store (e.g. Redis) — see references/oidc.md in the skill.

Any unauthenticated request to /api/* returns 401 (not a login redirect), matching the
.NET cookie handler's __Host- behaviour, so API/XHR callers get a machine-readable error.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.settings import VERACITY_OIDC_METADATA_URL, Settings, get_settings

oauth = OAuth()


def init_oauth(settings: Settings) -> None:
    """Register the Veracity OIDC client from B2C discovery metadata."""
    if "veracity" in oauth._clients:  # idempotent
        return
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


router = APIRouter(tags=["auth"])


def _user(request: Request) -> dict | None:
    return request.session.get("user")


@router.get("/auth", summary="Sign-in status")
async def auth_status(request: Request) -> dict[str, bool]:
    return {"result": _user(request) is not None}


@router.get("/auth/challenge", summary="Start OIDC login")
async def challenge(
    request: Request, returnUrl: str = "/", settings: Settings = Depends(get_settings)
):
    request.session["return_url"] = returnUrl
    # Prefer the configured redirect URI (e.g. the Vite proxy origin the SPA runs on) so
    # B2C returns the browser to the same origin that holds the session cookie. Fall back
    # to deriving the callback from the request when unset (single-origin / prod).
    redirect_uri = settings.redirect_uri or str(request.url_for("oidc_callback"))
    return await oauth.veracity.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", name="oidc_callback", summary="OIDC redirect callback")
async def callback(request: Request):
    token = await oauth.veracity.authorize_access_token(request)
    claims = token.get("userinfo") or {}
    request.session["user"] = {
        "id": claims.get("sub") or claims.get("oid", ""),
        "displayName": claims.get("name", ""),
        "email": claims.get("email")
        or (claims.get("emails", [None])[0] if claims.get("emails") else None),
        "firstName": claims.get("given_name"),
        "lastName": claims.get("family_name"),
    }
    # Store the API-scoped access token so the /api/v1/veracity/* proxy can call the
    # Platform API as the signed-in user (the login request included the Veracity API
    # scope). We intentionally do NOT keep the refresh token: the signed session cookie
    # is limited to ~4 KB and access_token + user already approach that. For silent token
    # refresh, switch to a server-side session store (see references/oidc.md).
    if "access_token" in token:
        request.session["access_token"] = token["access_token"]
    return_url = request.session.pop("return_url", "/")
    return RedirectResponse(url=return_url)


@router.get("/api/me", summary="Current user")
async def me(request: Request):
    user = _user(request)
    if user is None:
        # 401 for /api/* instead of a login redirect.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return JSONResponse(user)


@router.get("/signout", summary="Sign out")
async def sign_out(request: Request, settings: Settings = Depends(get_settings)):
    request.session.clear()
    return RedirectResponse(url=settings.logout_redirect_uri)
