---
name: veracity-auth-python
description: "Add Veracity authentication to a Python backend built with FastAPI, Flask, or Django (incl. DRF): OpenID Connect (BFF/cookie sessions, default) or JWT Bearer (stateless token validation), plus an optional Veracity Platform API V3/V4 client with BFF proxy endpoints. Integrates into an existing project (auto-detecting the framework) and scaffolds a FastAPI baseline via web-backend-python if no project exists. USE THIS whenever the user wants Veracity login/auth on a Python app, a Python Veracity BFF, a Python API that validates Veracity JWT bearer tokens, Veracity OpenID Connect / cookie sessions in FastAPI/Flask/Django, B2C setup in Python, or Veracity V3/V4 integration from a Python backend. Do NOT use for: a plain Python baseline with no Veracity (use web-backend-python); a full web app that also needs a frontend UI, or Veracity widgets on a React/SPA (use veracity-auth-ui); non-Python backends (use veracity-auth-net or veracity-auth-node); or non-Veracity providers."
---

# Veracity Auth Python — FastAPI / Flask / Django + Veracity Identity

It integrates a **Python** backend with the **Veracity Azure AD B2C** tenant, using exactly one
strategy per project (OpenID Connect **or** JWT Bearer).

- **New project** → scaffold a **FastAPI** backend (the default, tested reference).
- **Existing project** → integrate into whatever framework is already there — **FastAPI**,
  **Flask**, or **Django / Django REST Framework** — reusing the same framework-agnostic core.

The auth logic (JWT validation, MSAL token acquisition, the httpx API-client auth, config) lives
in a shared, framework-neutral package (`veracity_core`). Each framework provides only a thin
adapter (routing, session, middleware, and the dependency/decorator/authentication-class that
guards routes). The asset code in `assets/` is a **working, tested reference** — the bundled
pytest suite validates every flow (OIDC anonymous status + `/api/me` 401; JWT accept/reject for
valid / missing / expired / wrong-audience / wrong-issuer; API-client header injection) across all
three frameworks.

> **Separation of concerns**: This skill does **not** scaffold the baseline project itself. The
> baseline (health checks, security-headers/CSP middleware, ProblemDetails error handling, the
> versioned `/api/v1` group, `pydantic-settings` config, and the HTTPS-first dev server) is owned
> by the **`web-backend-python`** skill — the Python analog of `web-backend-net`. This skill ensures
> that baseline exists (creating it via `web-backend-python` when missing, for **new FastAPI**
> projects) and then layers Veracity authentication and V3/V4 integration on top. The `assets/`
> here are a complete, self-contained tested reference so the bundled pytest suite can validate
> every flow end-to-end.

## Why These Rules Exist

1. **Secrets never in source or chat** — `CLIENT_SECRET`, `SESSION_SECRET`, and
   `SUBSCRIPTION_KEY` must never be committed or pasted into the conversation. Locally they live
   in `.env` (gitignored — the analog of `dotnet user-secrets`); in deployed environments they
   come from Azure Key Vault / pipeline variables. Generate local development secrets into `.env`
   when scaffolding, but never ask the user to paste a secret value here.
2. **Single strategy per project** — Either OpenID Connect **or** JWT Bearer, never both in a
   real project. (The reference app supports both only so each flow can be validated.)
3. **Per-environment, Production by default** — All environments target the **Production**
   Veracity B2C tenant by default. Only override to Test/Staging when explicitly requested
   (values are in the reference files).
4. **API paths return 401, not a redirect** — For the OIDC BFF, unauthenticated `/api/*`
   requests return `401` so XHR/API callers get a machine-readable error instead of an HTML
   login redirect.
5. **Tight clock skew** — JWT validation uses a 60-second leeway (matching the .NET skill),
   tighter than common defaults.

## Prerequisites — Veracity App Registration

The user needs a **Veracity app registration** in the appropriate B2C tenant, which provides the
**Client ID** (a GUID, not secret) and a **Client Secret**. If they don't have one, direct them to:

- Getting started: https://docs.veracity.com/pages/developer-foundations/introduction/getting-started-as-a-developer
- Veracity Identity Provider (IDP): https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/veracity-identity-provider-idp
- Create an application: https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-an-application

The skill still scaffolds the code if the user hasn't registered yet — it just won't run until
they supply the values.

## Toolchain

FastAPI is the default for new scaffolds; the Flask and Django columns apply when integrating into
an existing project of that framework. The **shared core is identical** across all three.

| Concern | FastAPI (default) | Flask | Django / DRF |
|---------|-------------------|-------|--------------|
| Web layer / routing | FastAPI `APIRouter` (Uvicorn) | Flask `Blueprint` | Django views + `urls.py` |
| OIDC login (BFF) | Authlib `starlette_client` | Authlib `flask_client` | Authlib `django_client` |
| Session store | Starlette `SessionMiddleware` (signed cookie) | Flask `session` (Flask-Session + Redis for multi-instance) | Django sessions (server-side by default) |
| JWT guard | `Depends(require_user)` | `@require_user` decorator | DRF `VeracityJWTAuthentication` (+ plain `@require_user`) |
| Security headers / CSP | Starlette middleware | `after_request` hook | Django middleware |
| Local dev server | `veracity-dev` (Uvicorn HTTPS) | `run_dev` (Flask HTTPS) | `runserver_plus` / `runsslserver` |

Shared across every framework: **PyJWT + `PyJWKClient`** (JWT validation), **MSAL for Python**
(on-behalf-of / client-credentials), **httpx** (Veracity API calls), **pydantic-settings** (config
+ `.env` / Key Vault secrets), **Pydantic v2** (models). Tests use **pytest** (+ `pytest-django`
for the Django adapter).

## Phase 1: MODE & FRAMEWORK

First determine whether the user wants to:

1. **Create a new project** — scaffold from scratch under `src/{project-slug}-web` or
   `src/{project-slug}-api`. **New scaffolds always use FastAPI** (the tested reference); Flask and
   Django support is for integrating into projects that already use them. The generic FastAPI
   baseline is created by the **`web-backend-python`** skill (see Phase 4a); this skill then layers
   Veracity on top.
2. **Integrate into an existing project** — add Veracity auth to an existing Python app.

When integrating, **detect the framework** from project markers (ask only if ambiguous):

| Framework | Detect from |
|-----------|-------------|
| **Django** | `manage.py`, a `settings.py` with `INSTALLED_APPS`, `django` in `pyproject.toml`/`requirements.txt` |
| **Flask** | `Flask(__name__)` / `flask.Flask` usage, `flask` in dependencies |
| **FastAPI** | `FastAPI(...)` / `APIRouter` usage, `fastapi` in dependencies |

Then copy the shared core plus **only** the matching adapter package:

| Framework | Copy | Wire in |
|-----------|------|---------|
| FastAPI | `veracity_core/` + `app/` | app factory (`create_app`) adds middleware + routers |
| Flask | `veracity_core/` + `veracity_flask/` | `register_security_headers(app)`, then `init_veracity_oidc(app)` (BFF) **or** `@require_user` on API views |
| Django | `veracity_core/` + `veracity_django/` | add `veracity_django` to `INSTALLED_APPS`, the security middleware to `MIDDLEWARE`, `include("veracity_django.urls")`; for JWT add `VeracityJWTAuthentication` to DRF `DEFAULT_AUTHENTICATION_CLASSES` |

When integrating into an existing project:
- Locate `pyproject.toml`, `requirements.txt`, or the existing application package.
- Add only dependencies not already present (the framework itself is already there; add
  `authlib`, `msal`, `pyjwt[crypto]`, `httpx`, `pydantic-settings`, and — for Django JWT —
  `djangorestframework` if missing).
- Merge environment settings without overwriting existing local secrets.
- Preserve existing routes, middleware, settings, and tests unless they conflict with the selected
  Veracity auth strategy.
- Follow the framework's reference: `references/frameworks/flask.md` or
  `references/frameworks/django.md` (FastAPI specifics stay in `references/oidc.md` /
  `references/jwt.md`).

## Phase 2: PROJECT NAME RESOLUTION

For a new scaffold, determine the **base project name** automatically using this priority order:

1. If the user explicitly provides a name, use it.
2. Look for existing Python project metadata (`pyproject.toml` `[project].name`) and use it after
   removing known suffixes (`-web`, `-api`, `.web`, `.api`).
3. Use the Git repository name.
4. Use the repo root folder name.
5. Use the current working directory name.

> **Important**: Never derive the project name from an output or scratch directory path such as
> `outputs/`, `temp/`, `tmp/`, `workspace/`, or `.copilot/`. If the working directory is clearly a
> transient location, ask the user or use a sensible default like `veracity-app`.

Normalize the base name for Python:
- **Project slug / distribution name**: lowercase kebab-case, valid for `pyproject.toml`
  `[project].name` (for example `Veracity Reporting` → `veracity-reporting`).
- **Import package**: keep the tested asset package name `app` unless the user explicitly asks to
  rename it. If renamed, update imports, scripts, tests, and
  `[tool.hatch.build.targets.wheel].packages` consistently.

The final scaffold directory and `pyproject.toml` project name depend on the strategy:
- **OpenID Connect**: `src/{project-slug}-web` and `[project].name = "{project-slug}-web"`
- **JWT Bearer**: `src/{project-slug}-api` and `[project].name = "{project-slug}-api"`

## Phase 3: CHOOSE

Pick the authentication strategy before copying files. Priority order:

1. **Caller provided it** — if invoked by another skill that already knows the project type:
   Web App → **OIDC**, Stateless API → **JWT Bearer**.
2. **Derive from the request** — phrases like "web app", "login", "sign-in", "BFF" → **OIDC**;
   "stateless API", "bearer token", "validate tokens", "not a web app" → **JWT Bearer**.
3. **Derive from existing project context** — existing Python project names ending in `-web`
   imply **OIDC**; names ending in `-api` imply **JWT Bearer**.
4. **Ask the user** — *"Veracity OpenID Connect (BFF web app, recommended) or JWT Bearer
   (stateless API)?"* Default to **OIDC** if no preference.

Then read the matching reference and follow it:

| Strategy | Reference |
|----------|-----------|
| OpenID Connect (BFF) | `references/oidc.md` |
| JWT Bearer | `references/jwt.md` |

Configuration, secrets handling, and shared local HTTPS setup for **both** strategies is in
`references/config-and-secrets.md`. Calling the Veracity API (either strategy) is in
`references/apiclient.md`.

The strategy references (`oidc.md`, `jwt.md`) show the **FastAPI** wiring. When integrating into an
existing **Flask** or **Django** project, apply the same strategy but follow the framework adapter
reference for the concrete wiring — the endpoints, session posture, and 401 behaviour are identical:

| Framework | Reference |
|-----------|-----------|
| FastAPI | `references/oidc.md` / `references/jwt.md` |
| Flask | `references/frameworks/flask.md` |
| Django / DRF | `references/frameworks/django.md` |

## Phase 4: SCAFFOLD (new FastAPI project)

> This phase applies to **new** projects (always FastAPI). For an **existing** Flask/Django project,
> skip to the framework reference (`references/frameworks/flask.md` / `django.md`): copy
> `veracity_core/` + the adapter package, wire it into the existing app, and merge `.env`.

### 4a. Ensure the baseline project exists (via `web-backend-python`)

The generic baseline — health checks, security-headers/CSP middleware, ProblemDetails, the
versioned `/api/v1` group, `pydantic-settings` config, and the HTTPS-first dev server — is owned
by the **`web-backend-python`** skill. Do not hand-write it here.

- **No project exists → scaffold it first via the `web-backend-python` skill.** Invoke it, passing:
  - the **full project name including the suffix** chosen in Phase 2/3 (`{project-slug}-web` for
    OIDC, `{project-slug}-api` for JWT),
  - the location `src/{project-name}/`,
  - the desired **HTTPS port** (ask the user; default **54438**).

  After it completes you have a clean, building FastAPI baseline (`app/main.py`, `app/settings.py`,
  `app/security_headers.py`, `app/health.py`, `app/problem_details.py`, `app/api/v1.py`,
  `app/dev_server.py`, `pyproject.toml`, `.env`, tests). Proceed to 4b to layer Veracity on top.
- **A project already exists → skip scaffolding** and integrate Veracity into it (add only what is
  missing; preserve existing endpoints, middleware, settings, and tests).

### 4b. Layer Veracity onto the baseline

1. Copy the Veracity assets into the project (see the **Assets** table): the shared `veracity_core/`
   package plus the Veracity `app/auth/` and `app/veracity/` packages. Keep the `app` import package
   name, or rename it consistently across imports, tests, scripts, and `pyproject.toml`
   (`[tool.hatch.build.targets.wheel] packages`). Keep `veracity_core` as-is.
2. Extend `app/settings.py` to re-export the Veracity settings model (`veracity_core.settings`,
   Production B2C constants baked in) so `Settings` gains the Veracity fields (`client_id`,
   `client_secret`, `jwt_audience`, `subscription_key`, `service_id`, …) on top of the baseline
   fields.
3. Extend the baseline CSP so Veracity works: add `https://*.veracity.com` to `img-src`/`style-src`/
   `script-src`/`connect-src` and `form-action https://login.veracity.com`. (The baseline ships a
   generic `'self'`-only CSP; this is the Veracity extension.)
4. Rewire `app/main.py` (the app factory) to add the chosen strategy on top of the baseline
   pipeline: for **OIDC** add `SessionMiddleware` + the auth router + the Veracity API proxy router;
   for **JWT** add the `require_user`-guarded protected router. Keep the baseline security-headers,
   ProblemDetails, health, and `/api/v1` wiring.
5. Merge Veracity dependencies into `pyproject.toml` (`authlib`, `msal`, `pyjwt[crypto]`, `httpx`,
   `itsdangerous`; keep the FastAPI extra). Update `[project].name` to `{project-slug}-web`
   (OIDC) or `{project-slug}-api` (JWT).
6. Merge Veracity keys into `.env`: fill selected non-secret values, generate a strong
   `SESSION_SECRET` for OIDC projects, and keep secret placeholders only for values the user must
   supply later (for example `CLIENT_SECRET`, `SUBSCRIPTION_KEY`). The baseline already generated the
   local HTTPS cert/key and wired `HTTPS_CERT_FILE` / `HTTPS_KEY_FILE`; keep HTTPS-first local dev.

> **Self-contained reference**: The `assets/` in this skill include working `app/health.py`,
> `app/main.py`, `app/dev_server.py`, and `app/settings.py` so the bundled pytest suite runs
> standalone as a focused harness for the Veracity flows. When scaffolding a **real** project you
> start from the richer `web-backend-python` baseline (which additionally brings ProblemDetails and
> the versioned `/api/v1` group) and overlay these Veracity assets — the resulting **Veracity
> behaviour** (endpoints, 401 posture, token handling) is identical to the bundled reference.

## Phase 5: AUTHENTICATE

Apply the strategy reference. For **FastAPI**, use `oidc.md` / `jwt.md`: for a single-strategy
project you can trim `app/main.py` to only the chosen branch and delete the unused `app/auth/*.py`
module plus tests that import it. For **Flask** use `references/frameworks/flask.md`; for
**Django/DRF** use `references/frameworks/django.md`. The framework-agnostic validation and token
logic in `veracity_core` is unchanged across all three.

## Phase 6: API CLIENT (optional)

If the user needs to call the Veracity Platform API, follow `references/apiclient.md`:
generate a typed client with `openapi-python-client` and plug in the `VeracityAuth` httpx auth
(`app/veracity/client.py`) that attaches the Bearer token (OBO) and `Ocp-Apim-Subscription-Key`.

**Pick exactly one API version — V3 or V4 — and generate only that version's code; delete the
other version's artifacts.** A project integrates **either** V3 **or** V4, never both. When the
user chose one version, remove the other version's helpers, routes, client maker, base-URL
setting, and tests (see the "Keep only your chosen version" checklist in `references/apiclient.md`):

- **V3 selected** → keep `get_my_services`, `validate_policy_v3`, the `v3/*` routes, `make_v3_client`,
  and `api_v3_base_url`; delete `get_my_applications`, `validate_policy_v4`, the `v4/*` routes,
  `make_v4_client`, and `api_v4_base_url`.
- **V4 selected** → keep `get_my_applications`, `validate_policy_v4`, the `v4/*` routes, `make_v4_client`,
  and `api_v4_base_url`; delete `get_my_services`, `validate_policy_v3`, the `v3/*` routes,
  `make_v3_client`, and `api_v3_base_url`.

`SERVICE_ID` is required **only** by the **V4** `policy/validate` endpoint
(`POST /me/policy-verifications/{SERVICE_ID}`). **V3** policy validation is Veracity-wide
(`GET /my/policies/validate()`) and needs no service id. So keep `SERVICE_ID` in `.env` only for a
V4 project that generates `v4/policy/validate`; omit it entirely for V3-only projects.

## Phase 7: VERIFY

- From the resolved project directory, run `uv run pytest` — the bundled suites cover health,
  security headers, JWT accept/reject (valid / missing / expired / wrong audience / wrong issuer),
  OIDC anonymous status, the `/api/me` 401, and API-client header injection.
- From the resolved project directory, run `uv run veracity-dev` with the generated local HTTPS
  certs and open `https://localhost:54438/docs`.
- **OIDC:** `GET /auth` → `{"result": false}`; `GET /api/me` → `401`;
  `GET /auth/challenge` → `302` to `login.veracity.com/.../oauth2/v2.0/authorize` with
  `response_type=code` and the configured scopes (proves live B2C discovery).
- **JWT:** `GET /v1/me` without a token → `401`; with a valid Veracity token → `200`.

## Integration With Other Skills

| Skill | Integration |
|-------|-------------|
| `web-backend-python` | Owns the generic **FastAPI baseline** (health checks, security-headers/CSP middleware, ProblemDetails, the versioned `/api/v1` group, `pydantic-settings` config, HTTPS dev server). For a **new** project this skill invokes `web-backend-python` first (Phase 4a) to create that baseline, then layers Veracity auth on top — the Python analog of how `veracity-auth-net` uses `web-backend-net`. |
| `veracity-auth-ui` / frontend SPAs | The React SPA from **veracity-auth-ui** consumes this BFF unchanged: it calls `/auth`, `/auth/challenge`, `/auth/callback`, `/signout`, `/api/me`, and the Veracity API proxy at `/api/v1/veracity/v3/services` and `/api/v1/veracity/v4/me/applications` — all provided by the OIDC branch with matching casing/paths (the `/auth/callback` path is forwarded by the SPA's `/auth` dev-proxy rule). When the SPA runs behind the Vite dev proxy on its own origin, set `REDIRECT_URI` to the Vite proxy URL (e.g. `https://localhost:5173/auth/callback`) so B2C returns to the origin holding the session cookie. |

## Assets (Tested Reference Code)

The target paths below are for a **new FastAPI scaffold**. For an existing **Flask/Django** project,
copy `assets/veracity_core/` and the matching adapter package (`assets/veracity_flask/` or
`assets/veracity_django/`) into the project and wire them in per the framework reference.

| Asset | Target Path | Description |
|-------|-------------|-------------|
| `assets/pyproject.toml` | `src/{project-slug}-{web|api}/pyproject.toml` | Core deps (authlib, msal, pyjwt[crypto], httpx, pydantic-settings) + per-framework extras (`fastapi` / `flask` / `django`) + dev tools; update `[project].name` |
| `assets/.env.example` | `src/{project-slug}-{web|api}/.env.example` | Local config template (copy to `.env`, gitignored) |
| `assets/.gitignore` | `src/{project-slug}-{web|api}/.gitignore` | Ignores `.env`, venv, caches |
| `assets/veracity_core/` | `src/{project-slug}-{web|api}/veracity_core/` | **Framework-agnostic core**: constants, pydantic-settings, PyJWT validation (+ bearer/AuthError), MSAL OBO/client-credentials, httpx API-client auth, Veracity API proxy helpers (`proxy.py`) |
| `assets/app/settings.py` | `src/{project-slug}-{web|api}/app/settings.py` | Re-exports `veracity_core.settings` + constants (back-compat shim) |
| `assets/app/security_headers.py` | `src/{project-slug}-{web|api}/app/security_headers.py` | CSP/HSTS security-headers middleware |
| `assets/app/health.py` | `src/{project-slug}-{web|api}/app/health.py` | Anonymous health endpoints |
| `assets/app/main.py` | `src/{project-slug}-{web|api}/app/main.py` | App factory; wires the chosen strategy |
| `assets/app/dev_server.py` | `src/{project-slug}-{web|api}/app/dev_server.py` | HTTPS-first local Uvicorn launcher driven by `.env` cert/key settings |
| `assets/app/auth/oidc.py` | `src/{project-slug}-web/app/auth/oidc.py` | FastAPI Authlib BFF: `/auth`, `/auth/challenge`, `/auth/callback`, `/api/me`, `/signout` (SPA-matching paths) |
| `assets/app/auth/jwt.py` | `src/{project-slug}-api/app/auth/jwt.py` | FastAPI `require_user` dependency over `veracity_core.tokens` |
| `assets/app/veracity/routes.py` | `src/{project-slug}-web/app/veracity/routes.py` | FastAPI Veracity API proxy router (`/api/v1/veracity/v3/services` + `v3/policy/validate`, or `v4/me/applications` + `v4/policy/validate` — keep the chosen version) consumed by veracity-auth-ui |
| `assets/veracity_flask/` | `<flask-project>/veracity_flask/` | **Flask adapter**: Authlib BFF blueprint, Veracity API proxy blueprint, `@require_user` decorator, security-headers hook, health blueprint, HTTPS dev runner, app factory |
| `assets/veracity_django/` | `<django-project>/veracity_django/` | **Django adapter**: Authlib BFF views + urls, Veracity API proxy views, DRF `VeracityJWTAuthentication` (+ plain `@require_user`), security middleware, health views |
| `assets/app/veracity/client.py` | `src/{project-slug}-{web|api}/app/veracity/client.py` | httpx auth (Bearer + subscription key) + MSAL OBO provider |
| `assets/tests/*.py` | `src/{project-slug}-{web|api}/tests/*.py` | pytest suites for every flow above |

## References

- `references/oidc.md` — OIDC BFF flow, endpoints, session/cookie security, MSAL OBO, per-environment values (FastAPI wiring)
- `references/jwt.md` — JWT validation, issuer/audience/leeway, optional Swagger OAuth2, alternative `fastapi-azure-auth` (FastAPI wiring)
- `references/frameworks/flask.md` — Flask adapter: blueprint wiring, Flask session (+ Flask-Session/Redis), `@require_user`, HTTPS dev, integration steps
- `references/frameworks/django.md` — Django adapter: Authlib django_client views/urls, DRF `VeracityJWTAuthentication`, session/middleware/`INSTALLED_APPS` wiring
- `references/apiclient.md` — `openapi-python-client` generation + httpx auth layer, spec URLs, subscription key
- `references/config-and-secrets.md` — pydantic-settings, env profiles, shared local HTTPS setup,
  `.env` vs Key Vault, the exact secret keys
