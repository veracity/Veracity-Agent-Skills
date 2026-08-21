# Veracity Auth — Django / Django REST Framework Reference

Use this file when integrating Veracity Identity into an **existing Django** project. The auth
logic is the framework-agnostic `veracity_core`; this adapter (`veracity_django`) only wires it into
Django. Copy **both** `veracity_core/` and `veracity_django/` into the project.

Shared concepts (B2C authority/tenant values, per-environment overrides, OIDC flow semantics, JWT
issuer/audience/leeway, MSAL OBO, secrets) live in `references/oidc.md`, `references/jwt.md`,
`references/apiclient.md`, and `references/config-and-secrets.md`. This file covers Django-specific
wiring only.

## Install

Add the dependencies the project doesn't already have (Django is already present):

```
authlib msal pyjwt[crypto] httpx pydantic-settings
# for local HTTPS dev (runserver_plus):
django-extensions Werkzeug pyOpenSSL
# for the JWT strategy (primary path uses DRF):
djangorestframework
```

## Register the app

`settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "django_extensions",       # required for runserver_plus (local HTTPS dev)
    "rest_framework",          # only needed for the JWT strategy
    "veracity_django",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",   # required for OIDC
    "veracity_django.middleware.VeracitySecurityHeadersMiddleware",
    # ... Django's own SecurityMiddleware still handles HSTS/redirects
]
```

`urls.py` (project root):

```python
from django.urls import include, path
urlpatterns = [
    path("", include("veracity_django.urls")),
    # ... your routes
]
```

## OpenID Connect (BFF)

`veracity_django/oidc.py` uses Authlib's Django integration and **Django's session framework**.
Included endpoints (from `veracity_django/urls.py`):

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth` | GET | Anonymous | `{ "result": <bool> }` |
| `/auth/challenge?returnUrl=` | GET | Anonymous | Redirect to Veracity login (Auth Code + PKCE) |
| `/auth/callback` | GET | Anonymous | Exchange code, store user + tokens in session |
| `/api/me` | GET | Required | Current user; **401** if not signed in |
| `/signout` | GET | Anonymous | Flush session, redirect to `logout_redirect_uri` |
| `/api/v1/veracity/v3/services` | GET | Required | Proxy: the user's Veracity services (V3) |
| `/api/v1/veracity/v4/me/applications` | GET | Required | Proxy: the user's applications (V4) |

`/api/*` returns **401** (not a login redirect) for unauthenticated callers. These paths/casing
match the **veracity-auth-ui** SPA exactly, so the generated frontend works unchanged. Set
`REDIRECT_URI=https://localhost:5173/auth/callback` (the Vite proxy origin) when the SPA fronts this
BFF; leave it empty for a single-origin deployment.

### Session store — a Django advantage

Django sessions are **server-side by default** (database or cache backend), so BFF token state is
not size-limited the way a signed cookie is, and multi-instance deployments work once you point the
session backend at a shared store (`django.contrib.sessions.backends.cache` with Redis/Memcached).
This is the natural fit for caching MSAL OBO tokens server-side.

## JWT Bearer (stateless API) — DRF (primary)

`veracity_django/jwt.py` provides `VeracityJWTAuthentication`, a DRF authentication class over
`veracity_core.tokens`. Register it globally or per-view:

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "veracity_django.jwt.VeracityJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

```python
# a protected DRF view
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def me(request):
    return Response({"id": request.user.principal.subject, "name": request.user.principal.name})
```

- A **missing** token → DRF returns **401** with `WWW-Authenticate: Bearer` (from
  `authenticate_header`).
- An **invalid** token (bad signature/issuer/audience/expired) → `AuthenticationFailed` → **401**.
- `request.user` is a lightweight `VeracityUser` (`is_authenticated == True`) wrapping the validated
  `Principal`; the API is stateless and does **not** create Django ORM users.

### Plain Django (secondary, no DRF)

For projects without DRF, use the `@require_user` decorator on function views:

```python
from veracity_django.jwt import require_user

@require_user
def me(request):
    p = request.veracity_principal
    return JsonResponse({"id": p.subject, "name": p.name})
```

Validation (signature via the B2C JWKS, issuer, audience, 60s leeway) is identical to the FastAPI
path — see `references/jwt.md`.

## Security headers

`VeracitySecurityHeadersMiddleware` adds the Veracity-aligned CSP + related headers. Django's own
`SecurityMiddleware` continues to handle HSTS/SSL redirects; keep both.

## Local HTTPS development

OIDC needs HTTPS locally (secure session cookie + exact callback URL). Use `django-extensions`
`runserver_plus`, pointing at a localhost cert/key pair.

Generate the cert/key **automatically** with the bundled script before starting the server (it is
idempotent — a no-op when the files already exist):

```bash
uv run veracity-dev-cert   # creates .certs/localhost.pem + .certs/localhost-key.pem
```

The script prefers `mkcert` (trusted cert) when it is on `PATH` and otherwise falls back to a
self-signed localhost pair via the `cryptography` library, so no manual `mkcert` step is required.

**Prerequisites** — `django-extensions`, `Werkzeug`, and `pyOpenSSL` must be installed **and** `"django_extensions"` must be in `INSTALLED_APPS`. Without `django_extensions` in `INSTALLED_APPS`, Django will report `Unknown command: 'runserver_plus'`; without `pyOpenSSL`, it will report `Python OpenSSL Library is required`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_extensions",   # ← required for runserver_plus
    "veracity_django",
]
```

With `runserver_plus`, **always pass `--key-file` explicitly** alongside `--cert-file`:

```bash
uv run python manage.py runserver_plus --cert-file .certs/localhost.pem --key-file .certs/localhost-key.pem
```

> **Pitfall — `KEY_VALUES_MISMATCH`:** if you omit `--key-file`, `runserver_plus` derives the key
> path by swapping the cert's extension (`localhost.pem` → `localhost.key`). That is **not** the
> mkcert key file (`localhost-key.pem`), so it either fails to find a key or, if a differently-keyed
> `localhost.key` exists, loads a mismatched cert/key pair and crashes with
> `ssl.SSLError: [X509: KEY_VALUES_MISMATCH]`. Keep the paths aligned with `HTTPS_CERT_FILE` /
> `HTTPS_KEY_FILE` from `.env`.

Default callback URL: `https://localhost:54438/auth/callback` —
add it to the app registration reply URLs (or the `REDIRECT_URI` Vite proxy URL when a SPA fronts
the BFF). In production terminate TLS at the reverse proxy.

## Downstream Veracity API (OBO)

Reuse `veracity_core.obo.build_obo_token_provider` + `veracity_core.apiclient` exactly as in
`references/apiclient.md`; the signed-in user's access token (in `request.session`) is the
`user_assertion`.

## Verify

- Run `pytest` with `DJANGO_SETTINGS_MODULE` set (the reference uses `tests/django_settings.py`,
  signed-cookie sessions so no DB is needed). Suites: `tests/test_django_oidc.py`,
  `tests/test_django_jwt.py`.
- `GET /auth` → `{"result": false}`; `GET /api/me` → `401` when anonymous.
- DRF: `GET /drf/me` without a token → `401`; with a valid Veracity token → `200`; expired /
  wrong-audience / wrong-issuer → `401`.

## Error recovery

- **All requests 401 with issuer/JWKS errors** — authority/issuer mismatch for the environment;
  see the authority table in `references/jwt.md`.
- **Valid token still 401 (audience)** — `JWT_AUDIENCE` must equal the token's `aud` claim.
- **`SessionMiddleware` not configured** — the OIDC views need it; add it to `MIDDLEWARE`.
- **Permission returns 403 instead of 401** — ensure `VeracityJWTAuthentication` is in
  `DEFAULT_AUTHENTICATION_CLASSES` so DRF emits the `WWW-Authenticate: Bearer` challenge.
