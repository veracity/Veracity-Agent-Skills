# AN Agent Skills

A collection of GitHub Copilot skills for scaffolding and configuring **Veracity** web applications across **.NET, NodeJS, and Python** backends plus a **React** frontend. Each skill is a reusable instruction set that Copilot follows to automate a specific part of your project setup — from creating an API backend to wiring up Veracity login in the browser.

These skills live under `.github/skills/` and are loaded automatically by GitHub Copilot when it detects a matching user intent. You do not need to reference them by name — just describe what you want to do and Copilot will apply the right skill.

---

## Skills at a glance

| Skill | What it does |
|-------|-------------|
| [`web-backend-net`](#web-backend-net) | Scaffolds a new .NET 10 Minimal API baseline (API versioning, OpenAPI, FluentValidation, health checks, CSP/security headers) — **no authentication** |
| [`web-backend-node`](#web-backend-node) | Scaffolds a new NodeJS (Express 5 + TypeScript) baseline (zod env config, helmet/CSP, health checks, `/api/v1` anchor, error handler) — **no authentication** |
| [`web-backend-python`](#web-backend-python) | Scaffolds a new Python FastAPI baseline (OpenAPI `/docs`, Pydantic v2, `/api/v1` router, health checks, CSP/security headers, ProblemDetails, HTTPS dev server) — **no authentication** |
| [`web-base-ui`](#web-base-ui) | Scaffolds a new React + Vite + TypeScript frontend baseline (welcome page, generated `package.json`, selectable design system) — **no authentication** |
| [`veracity-auth-net`](#veracity-auth-net) | Adds Veracity authentication (OIDC or JWT) + V3/V4 API to a .NET 10 app; scaffolds the baseline via `web-backend-net` first when none exists |
| [`veracity-auth-node`](#veracity-auth-node) | Adds Veracity authentication (OIDC or JWT) + V3/V4 API client to a Node app (Express, Fastify, or NestJS); scaffolds an Express baseline via `web-backend-node` first when none exists |
| [`veracity-auth-python`](#veracity-auth-python) | Adds Veracity authentication (OIDC or JWT) + optional V3/V4 API client to a FastAPI/Flask/Django app; scaffolds the FastAPI baseline via `web-backend-python` first when none exists |
| [`veracity-auth-ui`](#veracity-auth-ui) | Adds Veracity login (sign in/out, profile, V3/V4 data) to a frontend; scaffolds the frontend via `web-base-ui` first when none exists |

---

## How the skills fit together

Each backend language has a **baseline** skill (no auth) and a **Veracity auth** skill that layers identity on top of that baseline. The frontend follows the same pattern with `web-base-ui` and `veracity-auth-ui`.

```
veracity-auth-ui          — add Veracity login to a frontend (full-stack from scratch)
        ↓ (scaffolds the frontend baseline when none exists)
      web-base-ui          — scaffold the React + Vite + TypeScript welcome-page baseline (no auth)
        ↓ (creates a Veracity BFF by default when none exists)
   veracity-auth-{net|node|python}   — add Veracity authentication (OIDC) to the BFF
        ↓ (scaffolds the baseline project when none exists)
      web-backend-{net|node|python}  — scaffold the backend baseline (no auth)
```

- **`veracity-auth-ui`** focuses on authentication. It **reuses** an existing frontend scaffold if the workspace has one, otherwise it creates a welcome-page baseline via `web-base-ui`, then layers Veracity login on top. It **always** produces a Veracity-integrated backend too: it reuses an existing BFF if present, otherwise it creates a new BFF — **.NET by default** (via `veracity-auth-net`), or **Node** / **Python** (via `veracity-auth-node` / `veracity-auth-python`) when the user asks for those stacks. It only skips creating a backend when the user explicitly already has a Veracity backend (in the workspace or at a URL they provide).
- **`veracity-auth-net` / `veracity-auth-node` / `veracity-auth-python`** can each be applied on their own to integrate Veracity auth into an **existing** app (OIDC or JWT). When no project exists, they first call the matching baseline skill to scaffold it, then layer authentication on top.
- **`web-backend-net` / `web-backend-node` / `web-backend-python`** and **`web-base-ui`** can each be used **standalone** to scaffold a plain, unauthenticated baseline when you don't need Veracity identity.

> **Same BFF contract across languages:** the .NET, Node, and Python BFFs all expose the same `/auth`, `/auth/challenge`, `/api/me`, `/signout` and `/api/v1/veracity/v3|v4/...` endpoints, so a `veracity-auth-ui` frontend serves any of them unchanged.

---

## Skill Guides

### web-backend-net

**Trigger phrases:** "scaffold a new .NET 10 minimal API", "bootstrap a backend service", "create a web API skeleton", "new .NET web project with sensible defaults", "baseline .NET API with health checks and versioning"

Scaffolds a brand-new **.NET 10 Minimal API** project with a production-sensible baseline — **but no authentication**. It is the foundation `veracity-auth-net` builds on.

| Capability | Detail |
|------------|--------|
| API versioning | URL segment (`/api/v1/...`) + `X-Api-Version` header, default v1.0 |
| OpenAPI / Swagger | Swagger UI in Development |
| Validation | FluentValidation with assembly scanning |
| Health checks | `/health`, `/health/ready`, `/health/live` (anonymous) |
| Security headers | `SecurityHeadersMiddleware` + CSP bound from the `CSP` config section |
| Error handling | Global `ProblemDetails` exception handler |
| Config & launch | `appsettings.json` (+ CSP), `appsettings.Development.json`, HTTPS `launchSettings.json` |

It does **not** add authentication, authorization, cookies, OIDC, JWT, or Veracity packages. The generated versioned API group is **not** protected — protection is added later by an auth skill.

**Example prompts:**
```
Scaffold a new .NET 10 minimal API called Contoso.Reporting.
Create a baseline .NET web API skeleton with health checks and API versioning.
```

---

### web-backend-node

**Trigger phrases:** "scaffold a new Node/Express backend", "bootstrap a Node API service", "create an Express + TypeScript skeleton", "new Node web project with sensible defaults", "baseline Node API with health checks"

Scaffolds a brand-new **Express 5 + TypeScript** project with a production-sensible baseline — **but no authentication**. It is the NodeJS sibling of `web-backend-net` and the foundation `veracity-auth-node` builds on.

| Capability | Detail |
|------------|--------|
| Versioned API anchor | `src/routes/apiV1.ts` router mounted at `/api/v1` |
| Config / secrets | `dotenv` layering (`.env` → `.env.<NODE_ENV>` → `.env.local`) validated with `zod` |
| Health checks | `/health`, `/health/ready`, `/health/live` (anonymous) |
| Security headers | `helmet` with generic `'self'`-only CSP |
| Error handling | Global error handler with a ProblemDetails-style body |
| Tooling | `tsx` dev, `tsc` build, ESLint + Prettier, vitest + supertest, optional HTTPS via mkcert |

It does **not** add authentication, sessions, OIDC, JWT, or Veracity packages. The `/api/v1` router is **not** protected — protection is added later by an auth skill.

**Example prompts:**
```
Scaffold a new Express + TypeScript backend called contoso-reporting.
Bootstrap a baseline Node API skeleton with health checks.
```

---

### web-backend-python

**Trigger phrases:** "scaffold a new FastAPI project", "bootstrap a Python backend service", "create a FastAPI skeleton", "new Python web project with sensible defaults", "baseline Python API with health checks"

Scaffolds a brand-new **FastAPI (Python)** project with a production-sensible baseline — **but no authentication**. It is the Python sibling of `web-backend-net` and the foundation `veracity-auth-python` builds on.

| Capability | Detail |
|------------|--------|
| OpenAPI / Swagger | Built-in `/docs` (Swagger UI) |
| Validation | Pydantic v2 models |
| Versioned API anchor | A `/api/v1` router group |
| Health checks | `/health`, `/health/ready`, `/health/live` (anonymous) |
| Security headers | Security-headers middleware + a Content-Security-Policy |
| Error handling | Global RFC 9457 `ProblemDetails` error handler |
| Config & dev server | `pydantic-settings` configuration, HTTPS-first local dev server |

It does **not** add authentication, sessions, OIDC, JWT, or Veracity packages. The `/api/v1` group is **not** protected — protection is added later by `veracity-auth-python`.

**Example prompts:**
```
Scaffold a new FastAPI project called contoso-reporting.
Bootstrap a baseline Python API skeleton with health checks and OpenAPI docs.
```

---

### web-base-ui

**Trigger phrases:** "scaffold a new React + Vite frontend", "bootstrap a React app", "create a web UI skeleton", "new frontend project with sensible defaults", "welcome-page SPA baseline"

Scaffolds a brand-new **frontend SPA** with a production-sensible baseline — a **React + Vite + TypeScript** welcome-page app (or a user-specified stack) — **but no authentication and no backend integration**. It is the foundation `veracity-auth-ui` builds on.

| Capability | Detail |
|------------|--------|
| App | React + Vite + TypeScript SPA (default), or a user-specified stack |
| Welcome page | A single welcome screen showing the project name |
| Dependencies | `package.json` **generated** at scaffold time with versions resolved from the npm registry as caret ranges |
| TypeScript | `tsconfig.json` (strict, `react-jsx`) |
| Dev server | Vite dev server over HTTPS (self-signed cert via `@vitejs/plugin-basic-ssl`), no backend proxy |
| Design system | Selectable: ShadCN by default; detected if the project already configures one (VUI, MUI, Chakra, Ant); or a user-named system / Google Stitch `design.md` |
| Build gate | `<pm> install` + `<pm> run build` must succeed |

It does **not** add authentication, cookies, OIDC/JWT, backend proxies, or Veracity packages. Those are layered on later by `veracity-auth-ui`. The bundled, MIT-licensed **ShadCN** design system lives here (`vendor/shadcn/`) — no network fetch required.

**Example prompts:**
```
Scaffold a new React + Vite frontend called MyPortal.
Create a welcome-page web app with the default design system.
```

---

### veracity-auth-net

**Trigger phrases:** "add Veracity authentication", "create a Veracity-secured web project", "set up a Veracity BFF", "create a stateless API with JWT for Veracity", "integrate Veracity V3/V4 API", "wire up Veracity OpenID Connect"

Adds **Veracity authentication** to a .NET 10 application. This skill focuses on authentication: when no scaffolded baseline project exists it first calls **`web-backend-net`** to scaffold one, then layers Veracity auth on top; when a project already exists it integrates auth into it. Supports both authentication strategies:

| Strategy | When to use |
|----------|------------|
| **OpenID Connect (BFF)** *(default)* | Web app where a React frontend communicates with a .NET backend — sessions and cookies managed server-side |
| **JWT Bearer** | Stateless API consumed directly by SPAs, mobile apps, or other services that already hold a bearer token |

**What gets added on top of the baseline:**

| Output | OIDC (`.Web`) | JWT (`.Api`) |
|--------|--------------|-------------|
| `VeracityAuthExtensions.cs` / `JwtAuthExtensions.cs` | ✅ | ✅ |
| Auth woven into `Program.cs` (services + middleware + protected API group) | ✅ | ✅ |
| Auth endpoints (`/auth`, `/api/me`, `/signOut`) | ✅ | — |
| Veracity V3 or V4 API endpoints | ✅ (optional) | — |
| Swagger OAuth2 Authorize dialog | — | optional |
| Veracity / Jwt appsettings sections merged | ✅ | ✅ |

**Project naming convention:** OIDC → `src/{BaseName}.Web/`; JWT → `src/{BaseName}.Api/`.

**When integrating into an existing project:** the baseline is **not** re-scaffolded — only missing auth packages are added, configuration is merged without overwriting, and existing endpoints and middleware are preserved.

**Example prompts:**
```
Add Veracity authentication to my existing .NET 10 project.
Create a new Veracity web project called "MyApp" with V4 APIs.
Scaffold a stateless JWT API called "DataService" with Swagger OAuth2.
```

---

### veracity-auth-node

**Trigger phrases:** "add Veracity auth in Node", "Express/Fastify/NestJS login with Veracity", "Node Veracity BFF", "validate Veracity JWT in Node", "set up B2C in NodeJS", "call the Veracity API from Express"

The NodeJS sibling of `veracity-auth-net`. Adds **Veracity authentication** to a Node (TypeScript) backend built with **Express, Fastify, or NestJS** (the framework is auto-detected for existing projects): when no project exists it first calls **`web-backend-node`** to scaffold an Express baseline, then layers Veracity auth on top; when a project already exists it integrates auth into it additively using the adapter for its framework.

| Strategy | When to use |
|----------|------------|
| **OpenID Connect (BFF)** *(default)* | Web app with cookie sessions — `@azure/msal-node` confidential client, session with `__Host-` cookie (`express-session` or `@fastify/session`), `/auth`, `/auth/challenge`, `/api/me`, `/signOut` |
| **JWT Bearer** | Stateless API validating bearer tokens with `jose` (JWKS, 60s clock tolerance) |

Optionally generates the **Veracity Platform API V3/V4 typed client** (`openapi-typescript` + `openapi-fetch`) with BFF proxy endpoints under the same `/api/v1/veracity/v3|v4/...` contract as the .NET BFF — so it can serve a `veracity-auth-ui` frontend unchanged. Secrets (`CLIENT_SECRET`, `SESSION_SECRET`, subscription key) are guided into the gitignored `.env.local`, never into source or chat.

**Example prompts:**
```
Add Veracity login to my Express app.
Create a Node API that validates Veracity JWT bearer tokens.
Add Veracity OIDC plus the V4 applications API to my Node backend.
```

---

### veracity-auth-python

**Trigger phrases:** "add Veracity login in Python", "FastAPI Veracity BFF", "validate Veracity JWT in FastAPI", "add Veracity auth to Flask/Django", "call the Veracity API from Python"

The Python sibling of `veracity-auth-net`. Adds **Veracity authentication** to a Python backend using OpenID Connect (BFF) or JWT Bearer. For a **new** project it scaffolds a **FastAPI** backend (via **`web-backend-python`**, the tested reference); for an **existing** project it integrates into whatever framework is already there — **FastAPI, Flask, or Django / Django REST Framework** — reusing the same framework-neutral `veracity_core` package.

| Strategy | When to use |
|----------|------------|
| **OpenID Connect (BFF)** *(default)* | Web app with server-side sessions and cookies (Authlib), exposing `/auth`, `/api/me`, `/signout` |
| **JWT Bearer** | Stateless API validating Veracity bearer tokens (JWKS, audience/issuer checks) |

Adds auth routes, settings, security headers, health checks, a bundled pytest suite validating every flow (OIDC anonymous status + `/api/me` 401; JWT accept/reject; API-client header injection) across all three frameworks, and an optional **Veracity V3/V4 API client** with BFF proxy endpoints. Secrets go into a gitignored `.env`, never into source.

**Example prompts:**
```
Add Veracity login to my FastAPI app.
Create a Python API that validates Veracity JWT bearer tokens.
Add Veracity OIDC plus the V4 applications API to my Flask backend.
```

---

### veracity-auth-ui

**Trigger phrases:** "full-stack Veracity login app", "React app plus a login backend", "web with Veracity login from scratch", "add Veracity sign in to my app", "end-to-end Veracity login web app"

Adds **Veracity login** to a web frontend — Sign In / Sign Out, an authenticated user profile, and the user's Veracity services/applications (V3/V4) — wired to a **Veracity Identity BFF** that exposes `/auth` and `/auth/challenge`. This skill focuses on authentication: when no scaffolded frontend exists it first calls **`web-base-ui`** to scaffold a welcome-page baseline, then layers Veracity login on top; when a frontend already exists it integrates auth into it. The frontend stays minimal — no VUI, React Query, or Zustand by default.

**Output location:** the frontend is placed as a **sibling of the BFF project**, named per the backend stack — `{Base}.Client` for a .NET BFF, `{base}-client` (kebab-case) for a Node or Python BFF. If a new .NET BFF is created it goes to `src/<ProjectName>.Web/` and the frontend to `src/<ProjectName>.Client/`; if an existing API project lives at the repo root (e.g. `MyApi/`), the frontend is created next to it (`MyApi.Client/`).

**How it resolves the frontend (default: scaffold one):**

| Path | When |
|------|------|
| **Reuse existing frontend** | A frontend scaffold already exists (`package.json` + app entry); auth is integrated without re-scaffolding |
| **Scaffold via `web-base-ui`** *(default)* | No frontend exists — delegates to `web-base-ui` to create the welcome-page baseline, then applies auth |

**How it resolves the backend (default: create one):**

| Path | When |
|------|------|
| **Reuse existing BFF** | A workspace project (any stack — .NET, Node, or Python) already exposes `/auth` and `/auth/challenge` |
| **Use a provided URL** | The user explicitly already has a backend serving the auth endpoints |
| **Create a new BFF** *(default)* | No backend exists — delegates to `veracity-auth-net` (OIDC, **.NET default**), or `veracity-auth-node` / `veracity-auth-python` when a Node or Python backend is requested |

**Required BFF endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /auth` | Returns `{ "result": boolean }` — is the user signed in (anonymous-safe) |
| `GET /auth/challenge` | Triggers OIDC sign-in; accepts `?returnUrl=` |
| `GET /api/me` | Returns the current user; `401` if not authenticated |
| `GET /signout` | Signs the user out |

**What you get:**
- A frontend that checks `/auth` on load, shows a **Sign in** button (redirects to `/auth/challenge`), and shows the user + **Sign out** when authenticated
- A login UI built with **the frontend's design system** — the one `web-base-ui` set up (ShadCN default, or a detected system: VUI, MUI, Chakra, etc.)
- Default tech stack **React + Vite + TypeScript**; vanilla JS/HTML or an alternative bundler is supported when you ask for it, keeping the same auth contract
- A Vite dev server over **HTTPS** (`@vitejs/plugin-basic-ssl`) so the BFF's secure auth cookie flows through the same-origin proxy
- A Vite proxy **merged** into the scaffold's config, targeting the resolved backend URL (`/api`, `/auth/challenge`, `/auth`, `/signin-oidc`, `/signout`)
- A scoped 401→challenge recovery on `/api/me` (no global fetch interceptor)
- If the BFF exposes Veracity API endpoints, the frontend automatically calls and displays them: V3 services from `/api/v1/veracity/v3/services` and/or V4 applications from `/api/v1/veracity/v4/me/applications`
- `README.md` documenting the architecture and local development

**Example prompt:**
```
Build a full-stack Veracity login web app called "MyApp" from scratch.
```

---

## Using the skills

The skills are loaded automatically by GitHub Copilot when it detects a matching user intent — just describe what you want to build. To invoke one explicitly, name it:

```
Use the veracity-auth-net skill to add authentication to my project.
```

---

## Repository Layout

```
.github/skills/
  README.md                       # This catalog
  web-backend-net/                # Scaffold a plain .NET 10 Minimal API baseline (no auth)
  web-backend-node/               # Scaffold a plain Express 5 + TypeScript baseline (no auth)
  web-backend-python/             # Scaffold a plain FastAPI baseline (no auth)
  web-base-ui/                    # Scaffold a plain React + Vite + TS frontend baseline (no auth); bundles ShadCN
  veracity-auth-net/              # Add Veracity auth (OIDC or JWT) + V3/V4; scaffolds baseline via web-backend-net when none exists
  veracity-auth-node/             # Add Veracity auth + V3/V4 client to Express/Fastify/NestJS; scaffolds Express baseline via web-backend-node when none exists
  veracity-auth-python/           # Add Veracity auth + V3/V4 client to FastAPI/Flask/Django; scaffolds FastAPI baseline via web-backend-python when none exists
  veracity-auth-ui/               # Add Veracity login to a frontend; scaffolds the frontend via web-base-ui when none exists
```
