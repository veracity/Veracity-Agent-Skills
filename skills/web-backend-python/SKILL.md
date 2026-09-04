---
name: web-backend-python
description: "Scaffold a new FastAPI (Python) web/API project with the standard baseline capabilities every backend service needs: OpenAPI/Swagger (built-in /docs), Pydantic v2 validation, a versioned /api/v1 router group, health checks (live/ready), a Content-Security-Policy and security-headers middleware, a global RFC 9457 ProblemDetails error handler, pydantic-settings configuration, and an HTTPS-first local dev server. USE THIS SKILL whenever the user wants to create a new FastAPI project, bootstrap a Python backend service, scaffold a web API skeleton, set up a new Python web project with sensible defaults, or needs a clean baseline project to build on. This skill does NOT add authentication — it produces an unauthenticated baseline. For Veracity login/JWT/API integration on top of a Python backend, use the veracity-auth-python skill (which calls this skill to scaffold first when no project exists)."
license: Apache-2.0
---

# Python Web Backend Scaffolding

This skill creates a new **FastAPI** project with a production-sensible baseline — but
**no authentication**. It is the foundation other skills build on (the Python analog of the
`web-backend-net` skill).

## What this skill produces

| Capability | Detail |
|------------|--------|
| OpenAPI / Swagger | FastAPI built-in — interactive docs at `/docs`, schema at `/openapi.json` |
| Validation | Pydantic v2 request/response models (built-in) |
| API versioning | A versioned `APIRouter(prefix="/api/v1")` group — the seam new endpoints hang off |
| Health checks | `/health`, `/health/ready`, `/health/live` (all anonymous) |
| Security | `SecurityHeadersMiddleware` + CSP from the `content_security_policy` setting |
| Error handling | Global RFC 9457 `ProblemDetails` (`application/problem+json`) handler |
| Config | `pydantic-settings` `Settings` (+ generic `'self'`-only CSP defaults), `.env` / `.env.example` |
| Launch | HTTPS-first `dev_server.py` (`web-dev` script) on a fixed port |

It does **not** add authentication, authorization, cookies/sessions, OIDC, JWT, or any
provider-specific packages or endpoints. The generated versioned `/api/v1` group is **not**
protected — protection is added later by an auth skill.

> **CSP defaults are intentionally generic.** The scaffolded settings ship with `'self'`-only
> CSP sources so the baseline has no external dependencies. Auth skills (e.g.
> `veracity-auth-python`) extend the CSP when they add their own CDN and login endpoints.

## Toolchain

FastAPI (Uvicorn) + Pydantic v2 + pydantic-settings. Dependency/venv management uses `uv`
when available (falling back to `pip`). Tests use `pytest`.

## Phase 1: Mode Detection

Determine whether the user wants to:

1. **Create a new project** — scaffold from scratch (the default).
2. **Integrate into an existing project** — add only the missing baseline capabilities to an
   existing FastAPI app (skip project creation, adapt to existing structure).

When integrating into an existing project:
- Locate `pyproject.toml` (or `requirements.txt`) and the existing application package.
- Add only the dependencies not already present.
- Merge configuration into existing `.env` / settings without overwriting existing values.
- Preserve existing endpoints, middleware, and services unless they conflict.

> **Invoked by another skill?** When this skill is called by `veracity-auth-python` (or another
> orchestrating skill), the caller passes the resolved **full project name** (including any
> suffix such as `-web` or `-api`), the target **location** (e.g. `src/`), and the **HTTPS port**.
> Use those values directly and skip the resolution/questions below.

## Phase 2: Project Name Resolution

Determine the **base project name** automatically using this priority order:

1. If the user (or calling skill) explicitly provides a name, use it.
2. Look for existing Python project metadata (`pyproject.toml` `[project].name`) and use it
   after removing known suffixes (`-web`, `-api`).
3. Use the Git repository name.
4. Use the repo root folder name.
5. Use the current working directory name.

> **Important**: Never derive the project name from an output or scratch directory path such as
> `outputs/`, `temp/`, `tmp/`, `workspace/`, or `.copilot/`. If the working directory is clearly
> a transient location, fall back to asking the user or use a sensible default like `web-app`.

Normalize the base name for Python:
- **Project slug / distribution name**: lowercase kebab-case, valid for `pyproject.toml`
  `[project].name` (for example `Contoso Reporting` → `contoso-reporting`).
- **Import package**: keep the tested asset package name `app` unless the user explicitly asks
  to rename it. If renamed, update imports, scripts, tests, and
  `[tool.hatch.build.targets.wheel].packages` consistently.

**Default suffix**: a plain baseline is API-shaped, so default to `{project-slug}-api` and place
it at `src/{project-slug}-api/`. If the caller (or user) specifies a different suffix (e.g.
`-web`), honor it. When invoked by an auth skill, **use the exact full name the caller passes**.

## Phase 3: HTTPS Port

Ask the user what HTTPS port to use for local development. If the user (or calling skill) does
not provide one, use **54438**.

> What HTTPS port would you like to use for local development? (Default: 54438)

Remember this value — write it as `APP_PORT` in `.env` (copied from `.env.example`).

## Phase 4: Project Structure

```
src/{project-slug}-api/
├── pyproject.toml
├── .env.example
├── .gitignore
└── app/
    ├── __init__.py
    ├── main.py             # create_app: security headers + ProblemDetails + health + /api/v1
    ├── settings.py         # pydantic-settings baseline (+ generic CSP)
    ├── security_headers.py
    ├── health.py
    ├── problem_details.py
    ├── dev_server.py
    └── api/
        ├── __init__.py
        └── v1.py           # versioned /api/v1 router seam
└── tests/
    ├── __init__.py
    ├── test_health.py
    ├── test_api_v1.py
    └── test_dev_server.py
```

## Phase 5: Generate Files

Use the template files from `assets/` as the source of truth.

> **Critical**: Copy from the asset templates — do not improvise or rewrite these files from
> memory. Keep the `app` import package name (or rename it consistently everywhere). Update
> `[project].name` in `pyproject.toml` to the resolved project slug.

1. Create the resolved project directory `src/{project-slug}-api/`.
2. Copy `assets/app/`, `assets/tests/`, `assets/pyproject.toml`, `assets/.env.example`, and
   `assets/.gitignore` into it.
3. Set `pyproject.toml` `[project].name = "{project-slug}-api"` (keep `[project.scripts].web-dev`
   unless the import package is intentionally renamed).
4. Copy `.env.example` to `.env` and set `APP_PORT` to the chosen port (default 54438). Generate
   local HTTPS cert and key files in the project (prefer a trusted localhost cert via `mkcert`
   when available; otherwise a self-signed localhost pair) and point `HTTPS_CERT_FILE` /
   `HTTPS_KEY_FILE` at them.
5. From the project directory, install dependencies:
   `uv venv && uv pip install -e ".[dev]"` (or `pip install -e ".[dev]"`).

## Phase 6: Verify

From the resolved project directory:

```bash
uv run pytest          # health, security headers, versioned endpoint, ProblemDetails, dev server
uv run web-dev         # then open https://localhost:54438/docs
```

The app should start, expose `/docs` (OpenAPI), answer `/health`, `/health/ready`,
`/health/live`, and serve the sample `/api/v1/ping`.

## Adding endpoints

For the pattern to add new versioned endpoints after scaffolding, read
`references/new-endpoints.md`.

## Existing Project Integration

When adding the baseline to an existing FastAPI project, adapt the steps above. The guiding
principle is **additive, not destructive**: the user has working code, so add only what's
missing and leave everything else — endpoints, services, config — exactly as it is.

1. Add only the dependencies not already present in `pyproject.toml` / `requirements.txt`.
2. Add `app/security_headers.py` and `app/problem_details.py` (using the existing project's
   package layout).
3. In the existing app factory / `main.py`, add the security-headers middleware, the
   ProblemDetails handlers, the health router, and a versioned `/api/v1` router — only where not
   already configured. Skip any the project already sets up.
4. Merge the CSP / settings into the existing configuration without overwriting existing keys.

### Middleware & pipeline ordering

Follow the same relative order the new-project `assets/app/main.py` uses — inserting only the
pieces that aren't already there and leaving existing middleware in place:

1. `SecurityHeadersMiddleware` — added first so headers apply to every response.
2. ProblemDetails exception handlers.
3. Health endpoints.
4. The versioned `/api/v1` router group.

### Existing endpoints and the versioned group

Add the versioned `/api/v1` router so future endpoints have a versioned anchor (see
[`references/new-endpoints.md`](references/new-endpoints.md)). **Leave the user's existing
endpoints exactly where they are** — do not move, re-route, or rewrite them into the versioned
group. It's fine for the group to start with only the sample endpoint; it's the seam new work
hangs off, and moving existing routes would change their URLs and break callers.

### Local dev / .env

Do **not** overwrite an existing `.env` — it already carries the project's ports and settings.
Only create one from `.env.example` if the project doesn't have one.
