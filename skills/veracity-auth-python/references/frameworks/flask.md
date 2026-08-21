# Veracity Auth — Flask Reference

Use this file when integrating Veracity Identity into an **existing Flask** project. The auth
logic is the framework-agnostic `veracity_core`; this adapter (`veracity_flask`) only wires it into
Flask. Copy **both** `veracity_core/` and `veracity_flask/` into the project.

The shared concepts — Veracity B2C authority/tenant values, per-environment overrides, OIDC flow
semantics, JWT issuer/audience/leeway, MSAL OBO, secrets handling — are documented once in
`references/oidc.md`, `references/jwt.md`, `references/apiclient.md`, and
`references/config-and-secrets.md`. This file only covers the Flask-specific wiring.

## Install

Add the dependencies the project doesn't already have (Flask is already present):

```
authlib msal pyjwt[crypto] httpx pydantic-settings
```

## OpenID Connect (BFF)

`veracity_flask/oidc.py` uses Authlib's Flask integration and the Flask session. Wire it into the
existing app **factory** (or module-level `app`):

```python
from veracity_flask.oidc import init_veracity_oidc
from veracity_flask.security import register_security_headers

register_security_headers(app)
init_veracity_oidc(app)   # reads veracity_core Settings from env/.env
```

`init_veracity_oidc` registers the Veracity OIDC client from B2C discovery metadata, sets a secure
session cookie (`SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE=Lax`), and registers the auth
blueprint plus the Veracity Platform API proxy blueprint:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth` | GET | Anonymous | `{ "result": <bool> }` |
| `/auth/challenge?returnUrl=` | GET | Anonymous | Redirect to Veracity login (Auth Code + PKCE) |
| `/auth/callback` | GET | Anonymous | Exchange code, store user + tokens in session |
| `/api/me` | GET | Required | Current user; **401** if not signed in |
| `/signout` | GET | Anonymous | Clear session, redirect to `logout_redirect_uri` |
| `/api/v1/veracity/v3/services` | GET | Required | Proxy: the user's Veracity services (V3) |
| `/api/v1/veracity/v4/me/applications` | GET | Required | Proxy: the user's applications (V4) |

`/api/*` returns **401** (not a login redirect) for unauthenticated callers. These paths/casing
match the **veracity-auth-ui** SPA exactly, so the generated frontend works unchanged. Set
`REDIRECT_URI=https://localhost:5173/auth/callback` (the Vite proxy origin) when the SPA fronts this
BFF, so B2C returns the browser to the origin that holds the session cookie; leave it empty for a
single-origin deployment.

### Session store & multi-instance

The default Flask session is a **signed cookie** (state stored client-side, size-limited, signed
with `SECRET_KEY`). For multi-instance deployments — or once you cache OBO tokens server-side —
switch to **Flask-Session** with a Redis backend so all instances share session + token-cache
state (the Python analog of the .NET Data Protection + Redis distributed cache):

```python
from flask_session import Session
app.config.update(SESSION_TYPE="redis", SESSION_REDIS=redis_client)
Session(app)
```

## JWT Bearer (stateless API)

`veracity_flask/jwt.py` exposes a `@require_user` decorator over `veracity_core.tokens`. Set the
settings on the app once (so the decorator can read the audience), then guard views:

```python
from flask import g, jsonify
from veracity_flask.jwt import require_user
from veracity_core.settings import get_settings

app.extensions["veracity_settings"] = get_settings()

@app.get("/v1/me")
@require_user
def me():
    return jsonify({"id": g.principal.subject, "name": g.principal.name})
```

The route decorator (`@app.get`) must be **outermost**; `@require_user` sits directly on the view.
Missing/invalid tokens return **401** with `WWW-Authenticate: Bearer`. Validation (signature via the
B2C JWKS, issuer, audience, 60s leeway) is identical to the FastAPI path — see `references/jwt.md`.

## Security headers

`register_security_headers(app)` adds CSP/HSTS/X-Frame-Options/etc. via an `after_request` hook,
with the same Veracity-aligned CSP as the FastAPI middleware. (Alternatively use `flask-talisman`.)

## Local HTTPS development

For OIDC the BFF needs HTTPS locally (secure session cookie + exact callback URL). Use the bundled
runner:

```python
from veracity_flask.dev_https import run_dev
run_dev(app)   # auto-generates the localhost cert/key if missing, then serves HTTPS
```

`run_dev` calls `scripts/generate_dev_cert.py` on startup when `HTTPS_CERT_FILE` / `HTTPS_KEY_FILE`
are missing (mkcert when available, self-signed `cryptography` fallback otherwise), so no manual
`mkcert` step is needed. Default callback URL: `https://localhost:54438/auth/callback`. In
production run behind gunicorn/uwsgi with TLS terminated at a reverse proxy.

## Downstream Veracity API (OBO)

Reuse `veracity_core.obo.build_obo_token_provider` + `veracity_core.apiclient` exactly as in
`references/apiclient.md`. The signed-in user's access token (kept in `session`) is the
`user_assertion`.

## Verify

- Run `pytest` (the reference suite includes `tests/test_flask_oidc.py` and `tests/test_flask_jwt.py`).
- `GET /auth` → `{"result": false}` when not signed in.
- `GET /api/me` → `401` when not signed in (never a redirect).
- JWT: `GET /v1/me` without a token → `401`; with a valid Veracity token → `200`.

## Error recovery

- **`mismatching_state` on callback** — the session cookie didn't round-trip. Ensure `SECRET_KEY`
  is set, `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_SECURE=True`, and the app is served over
  the configured HTTPS certificate.
- **Redirect URI mismatch from B2C** — add the exact callback URL (`https://<host>/auth/callback`,
  or the `REDIRECT_URI` Vite proxy URL when a SPA fronts the BFF) to the app registration's reply
  URLs.
- **Valid token still 401 (audience)** — `JWT_AUDIENCE` must equal the token's `aud` claim.
