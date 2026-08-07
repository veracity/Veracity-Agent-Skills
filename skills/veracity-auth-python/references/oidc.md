# Veracity OpenID Connect (BFF) — Python / FastAPI Reference

Use this file when the chosen strategy is **OpenID Connect**. It mirrors the .NET
`AddAppAuthentications` + `AuthEndpoints` behaviour using **Authlib** for the login flow and a
signed-cookie **session** for state. Implemented in `assets/app/auth/oidc.py` and wired by
`assets/app/main.py`.

## Flow

The Backend-for-Frontend (BFF) keeps tokens on the server; the browser only holds a session
cookie. Login uses **Authorization Code + PKCE** against the Veracity B2C tenant, discovered from
the OIDC metadata document.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth` | GET | Anonymous | Sign-in status → `{ "result": <bool> }` |
| `/auth/challenge?returnUrl=` | GET | Anonymous | Redirect to Veracity login (Auth Code + PKCE) |
| `/auth/callback` | GET | Anonymous | Exchange code, store user + tokens in session |
| `/api/me` | GET | Required | Current user (id, displayName, email, firstName, lastName); **401** if not signed in |
| `/signout` | GET | Anonymous | Clear session, redirect to `logout_redirect_uri` |
| `/api/v1/veracity/v3/services` | GET | Required | Proxy: the signed-in user's Veracity services (V3); **401** if not signed in |
| `/api/v1/veracity/v4/me/applications` | GET | Required | Proxy: the signed-in user's applications (V4); **401** if not signed in |

The route names, casing, and the `/api/v1/veracity/...` mount are chosen to match the
**veracity-auth-ui** SPA exactly (its `src/api/auth.ts` / `src/api/veracity.ts` and the Vite
proxy in `vite.config.ts`); the `/api/v{version}` mount mirrors the .NET skill's versioned group.
The `/auth/callback` path is forwarded by the SPA's `/auth` dev-proxy rule, so the generated
frontend talks to this BFF with **no** changes. FastAPI routing is case-sensitive: the sign-out
path must be lowercase `/signout`.

`/api/*` returns **401** (not a login redirect) for unauthenticated callers — the Python analog
of the .NET `__Host-` cookie handler behaviour.

## Configuration values to collect

Ask the user for (non-secret, safe to share):

1. **Client ID** — the GUID of the Veracity app registration. Goes in `.env` as `CLIENT_ID`.

Explain before asking: *"To connect to Veracity Identity you need a Veracity app registration,
which gives a **Client ID** (a GUID, safe to share) and a **Client Secret** (a credential — keep
it secret). Find the Client ID in the [Veracity Developer Portal](https://developer.veracity.com)
under your app's Settings page (labelled 'App / Api ID')."*

The **Client Secret** is a secret the user sets in `.env` themselves (see
`config-and-secrets.md`); never ask for the value in chat. The **Session Secret** is also a
secret, but when applying this skill you should generate a strong local value and write it to
`.env` instead of asking the user to provide one.

## Project structure

For a new OIDC/BFF scaffold, create the project under the resolved Python project slug with a
`-web` suffix:

```text
src/{project-slug}-web/
├── pyproject.toml
├── .env.example
├── .gitignore
├── app/
│   ├── main.py
│   ├── settings.py
│   ├── security_headers.py
│   ├── health.py
│   ├── dev_server.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── oidc.py
│   └── veracity/
│       ├── __init__.py
│       ├── client.py
│       └── routes.py
└── tests/
```

Set `pyproject.toml` `[project].name` to `{project-slug}-web`. Keep the import package as `app`
unless the user explicitly asks to rename it; if renamed, update imports, tests, scripts, and
`[tool.hatch.build.targets.wheel].packages` consistently. For a single-strategy OIDC project,
delete `app/auth/jwt.py` and JWT-only tests, or leave them unused only if the user wants to keep
the full reference test surface.

## How the code works

`assets/app/auth/oidc.py`:
- `init_oauth(settings)` registers the Veracity client with
  `server_metadata_url = {authority}/.well-known/openid-configuration`, so Authlib fetches the
  authorize/token/jwks endpoints automatically. Authority (Production):
  `https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0`.
- `client_kwargs={"scope": settings.login_scopes, "timeout": settings.oidc_http_timeout}` —
  `login_scopes` combines the OIDC scopes (`openid profile email offline_access`) with the
  **Veracity Platform API scope** (`veracity_scope`, the `…/user_impersonation` scope). Requesting
  the API scope *at login* means the authorization-code exchange returns an access token already
  scoped for `api.veracity.com` — the same posture as Microsoft.Identity.Web in the .NET skill — so
  the proxy calls the API directly with **no** on-behalf-of exchange (Azure AD B2C does not reliably
  support OBO). Leave `veracity_scope` empty for a login-only BFF. The app registration must be
  authorized for the Veracity API scope. `timeout` is raised above httpx's 5s default (see Error
  recovery). `offline_access` still yields a refresh token.
- `/auth/challenge` calls `authorize_redirect` (Authlib generates state + PKCE automatically).
  The redirect (callback) URI is `settings.redirect_uri` when set, otherwise it is derived from
  the incoming request (`/auth/callback` on the backend host).
- `/auth/callback` calls `authorize_access_token`, reads `userinfo` claims into the session, and
  stores the user's **API-scoped access token** so the `/api/v1/veracity/...` proxy routes can call
  the Platform API as the signed-in user. On the FastAPI/Flask signed-cookie session the refresh
  token is **not** stored (the ~4 KB cookie limit); Django's server-side session keeps it.

`assets/app/main.py` (OIDC branch) adds Starlette `SessionMiddleware`:
- `session_cookie="__Host-session"` and `https_only=True` when `cookie_secure` is true. The
  `__Host-` prefix requires `Secure`, `Path=/`, and no `Domain`. The scaffold therefore starts
  local development over HTTPS by default via `uv run veracity-dev`; keep `COOKIE_SECURE=true`.

## Local HTTPS development

See `references/config-and-secrets.md` for the shared local HTTPS setup used by both strategies.
For OIDC it is required: the default callback URL is `https://localhost:54438/auth/callback`, and
`same_site="lax"` lets the cookie survive the top-level redirect back from B2C.

## Frontend (veracity-auth-ui) integration

When a React SPA generated by the **veracity-auth-ui** skill runs in front of this BFF, it is
served by Vite over HTTPS at its own origin (e.g. `https://localhost:5173`) and proxies `/auth`,
`/signout`, and `/api` to the BFF. Two things must line up:

1. **Same-origin callback.** B2C must return the browser to the *frontend* origin so the session
   cookie (set on that origin via the proxy) is present. Set `REDIRECT_URI` to the Vite proxy URL:

   ```dotenv
   REDIRECT_URI=https://localhost:5173/auth/callback
   ```

   Register that exact URL as a reply URL on the Veracity app registration. Leave `REDIRECT_URI`
   empty only when the SPA is served from the same origin as the BFF (single origin / prod behind
   one host), in which case the callback is derived from the request. (The .NET skill uses a
   `/signin-oidc` callback path; this Python skill uses `/auth/callback`, which the SPA's `/auth`
   dev-proxy rule also forwards — so no frontend change is needed.)

2. **Matching routes.** The SPA's `src/api` calls `/auth`, `/auth/challenge`, `/signout`,
   `/api/me`, `/api/v1/veracity/v3/services`, and `/api/v1/veracity/v4/me/applications` — all
   provided by this adapter with identical casing/paths, so no frontend edits are needed.

## Downstream API tokens & the Veracity API proxy

The OIDC branch mounts `/api/v1/veracity/v3/services` and `/api/v1/veracity/v4/me/applications`
(`assets/app/veracity/routes.py`, shared logic in `assets/veracity_core/proxy.py`). Each route
reads the user's **API-scoped access token** from the session (acquired at login because
`login_scopes` includes the Veracity `user_impersonation` scope) and calls the Veracity Platform
API *as the signed-in user* directly — no on-behalf-of exchange — attaching the
`Ocp-Apim-Subscription-Key`. This mirrors Microsoft.Identity.Web in the .NET skill, and avoids Azure
AD B2C's unreliable OBO support. A lapsed access token surfaces as **401** so the SPA can silently
re-challenge (the analog of the .NET token-cache recovery). See `references/apiclient.md`.

> **Why not on-behalf-of?** An earlier revision requested only `openid profile email offline_access`
> and tried an MSAL OBO exchange. With no API scope, B2C returns no usable Platform-API access token,
> and B2C does not reliably support OBO — the proxy then failed with *"No Veracity access token in
> session"*. Requesting the API scope at login is the fix. The `veracity_core.obo` client-credentials
> provider remains available for the JWT-Bearer strategy calling the API *as the app itself*.

## Session store & multi-instance deployments

The reference uses a **signed cookie** (simple, ~4 KB size-limited — the FastAPI/Flask adapters store
only the user + API access token, not the refresh token). For multi-instance deployments — or to
persist the refresh token for silent renewal — switch to a server-side session backed by Redis (e.g.
`starsessions` with a Redis store) so all instances share session state. This is the Python analog of
the .NET Data Protection + Redis distributed cache. Django's default server-side sessions already
avoid the cookie-size limit.

## Per-environment values

All environments default to the **Production** B2C tenant (constants baked into
`app/settings.py`). Only when explicitly requested, override for Test/Staging:

| Environment | Instance | Domain | TenantId | LogoutRedirectUri |
|-------------|----------|--------|----------|-------------------|
| **Production** (default) | `https://login.veracity.com` | `dnvglb2cprod.onmicrosoft.com` | `a68572e3-63ce-4bc1-acdc-b64943502e9d` | `https://www.veracity.com/auth/logout` |
| **Test** | `https://logintest.veracity.com` | `dnvglb2ctest.onmicrosoft.com` | `ed815121-cdfa-4097-b524-e2b23cd36eb6` | `https://wwwtest.veracity.com/auth/logout` |
| **Staging** | `https://loginstag.veracity.com` | `dnvglb2cstag.onmicrosoft.com` | `307530a1-6e70-4ef7-8875-daa8f5a664ec` | `https://wwwstag.veracity.com/auth/logout` |

The OIDC metadata URL, authority, and JWKS URI are derived from Instance/Domain/Policy in
`Settings` — change those three and everything else follows. Policy is always `B2C_1A_Identity`.

## Verify

- From `src/{project-slug}-web`, run `uv run pytest`.
- `GET /auth` → `{"result": false}` when not signed in.
- `GET /api/me` → `401` when not signed in (never a redirect).
- `GET /api/v1/veracity/v3/services` and `/api/v1/veracity/v4/me/applications` → `401` when not
  signed in; the user's services / applications once authenticated.
- `GET /auth/challenge` → `302` to
  `https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/b2c_1a_identity/oauth2/v2.0/authorize?response_type=code&...`
  — confirms live B2C discovery and a correctly-built auth request.
- After registering the app and setting real secrets, complete a full login and confirm `/api/me`
  returns the user profile.

## Error recovery

- **`mismatching_state` on callback** — the session cookie didn't round-trip. Ensure
  `SessionMiddleware` is registered, `same_site="lax"`, `COOKIE_SECURE=true`, and the app is being
  served through the configured HTTPS certificate.
- **HTTPS certs missing at startup** — `veracity-dev` fails fast if `HTTPS_CERT_FILE` or
  `HTTPS_KEY_FILE` is missing. Generate the localhost cert/key pair (for example with `mkcert`) and
  keep the paths in `.env` aligned with the generated files.
- **Redirect URI mismatch from B2C** — add the exact callback URL to the app registration's reply
  URLs: `https://<host>/auth/callback` (default `https://localhost:54438/auth/callback`), or, when a
  veracity-auth-ui SPA fronts the BFF, the Vite proxy URL set in `REDIRECT_URI`
  (e.g. `https://localhost:5173/auth/callback`).
- **Metadata fetch fails at challenge** — verify the authority/Instance/Domain are correct and the
  host can reach `login.veracity.com`.
- **`/auth/challenge` returns 500 with `httpcore.ConnectTimeout` / `ConnectError`** — Authlib fetches
  the B2C discovery metadata over HTTPS on the first challenge, and httpx defaults to a **5-second**
  timeout. On a slow network, or behind a **corporate/VPN proxy** (httpx honours `HTTPS_PROXY` /
  `ALL_PROXY` env vars), the CONNECT + TLS handshake can exceed that and the login 500s. The scaffold
  registers the OIDC client with a generous `timeout` (`settings.oidc_http_timeout`, default 30s via
  `client_kwargs`) to absorb this; raise `OIDC_HTTP_TIMEOUT` further if needed. If a proxy is set but
  not required (e.g. a local VPN client that is down), the direct route also works once `HTTPS_PROXY`
  is unset — but keep proxy support for environments where it *is* required.
