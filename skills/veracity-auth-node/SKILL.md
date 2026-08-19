---
name: veracity-auth-node
description: "Add Veracity authentication to a NodeJS (TypeScript) backend built with Express, Fastify, or NestJS: OpenID Connect (BFF/cookie sessions via @azure/msal-node, default) or JWT Bearer (stateless token validation via jose), plus an optional Veracity Platform API V3/V4 client with BFF proxy endpoints. Integrates into an existing Node project (auto-detecting the framework), and scaffolds an Express baseline via web-backend-node if none exists. USE THIS whenever the user wants Veracity login/auth on a Node app, a Node Veracity BFF, a Node API validating Veracity JWT bearer tokens, Veracity OpenID Connect / cookie sessions, or Veracity V3/V4 integration from a Node backend. Do NOT use for: a plain Node baseline with no Veracity (use web-backend-node); a full web app that also needs a frontend UI or Veracity widgets on a React/SPA (use veracity-auth-ui); non-Node backends (use veracity-auth-net or veracity-auth-python); or non-Veracity providers (Entra ID, Auth0, IdentityServer)."
---

# Veracity Authentication for NodeJS

This skill adds **Veracity Identity (Azure AD B2C)** authentication to a **NodeJS (TypeScript)** backend built with **Express, Fastify, or NestJS**. It supports two authentication strategies:

- **OpenID Connect (default)** — For BFF (Backend-For-Frontend) web apps that manage user sessions with cookies (`@azure/msal-node` + `express-session`, `__Host-` cookie).
- **JWT Bearer** — For stateless APIs consumed by SPAs, mobile apps, or service-to-service calls where the caller already holds a bearer token (`jose` JWKS validation).

It also wires up optional **Veracity Platform API V3/V4** integration (typed client + BFF proxy endpoints, OIDC).

> **Separation of concerns**: This skill does **not** scaffold the baseline project itself. The baseline (Express 5 + TypeScript, zod-validated env config, helmet security headers/CSP, health checks, `/api/v1` versioned router anchor, global error handler) is owned by the **`web-backend-node`** skill. This skill ensures that baseline exists (creating it via `web-backend-node` when missing) and then layers Veracity authentication on top. This mirrors the .NET pair `veracity-auth-net` / `web-backend-net`.

## Non-Negotiable Security Rules

1. **Secrets Never in Source** — `CLIENT_SECRET`, `SESSION_SECRET`, the API `Ocp-Apim-Subscription-Key`, and Redis connection strings must never appear in committed files. Use the gitignored `.env.local` for local development and environment variables / Azure Key Vault for deployed environments.
2. **Secrets Never in Conversation** — Never ask the user to paste secret values into the chat. Instead, **generate a gitignored `.env.local` scaffold** containing every secret and app-registration value the chosen strategy needs. For secrets that come from an external source (e.g. `CLIENT_SECRET`, `REDIS_URL`), write a clearly-marked placeholder (e.g. `CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE`) and have the user fill in the real value themselves. For an **app-internal** secret with no external source — the OIDC session signing key `SESSION_SECRET` — **generate a strong 32-byte random value yourself and write the real value** (`node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"`), never a placeholder and never a hard-coded fallback in source. Do not merely tell the user which lines to add — write the file so they only have to edit placeholder values. Non-secret values (Client ID, audience) are safe to ask for.
3. **Per-Environment Tenant Values** — Each environment uses its own Veracity B2C tenant. By default all environments target **Production**. Only use Test/Staging when explicitly requested (tables in the reference files).
4. **Single Strategy Per Project** — Either OpenID Connect **or** JWT Bearer, never both in the same project.
5. **Cookie Security (OIDC)** — The session cookie uses the `__Host-` prefix (`Secure`, `HttpOnly`, `SameSite`, `Path=/`, no `Domain`), and `/api/*` paths return `401` instead of redirecting to the identity provider.
6. **Validated Outbound Requests (SSRF)** — BFF proxy endpoints must never issue a server-side request to a caller-influenced absolute URL. The Veracity API client builds outbound calls from a **relative** `path` resolved against the configured base URL and validated against an origin allow-list (`resolveVeracityApiUrl` in `veracityApiClient.ts`); reject absolute/protocol-relative/off-origin values before fetching, and keep call sites `encodeURIComponent`-escaping any user-supplied path segment (CWE-918).

## Prerequisites — Veracity App Registration

The user needs a **Veracity app registration** in the appropriate B2C tenant, created in the [Veracity Developer Portal](https://developer.veracity.com). It provides the **Client ID** and (for OIDC) a **Client Secret**. If the user has not registered yet, direct them to:

- **Getting started as a developer**: https://docs.veracity.com/pages/developer-foundations/introduction/getting-started-as-a-developer
- **Veracity Identity Provider (IDP)**: https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/veracity-identity-provider-idp
- **Create an application**: https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-an-application

The skill still integrates everything even if the registration is not ready — leave `CLIENT_ID` (and audience) as a placeholder for the user to fill in.

## Phase 1: Determine Project Name & Strategy

### 1 (pre). Optional caller parameter — `REDIRECT_BASE_URL`

When this skill is invoked **by another skill** (e.g. `veracity-auth-ui`), the caller may pass a `REDIRECT_BASE_URL` (e.g. `https://localhost:5173`) — the HTTPS origin the **browser** uses (the frontend dev server, which proxies `/auth/*` and `/api/*` to this BFF). When provided, set `REDIRECT_URI = {REDIRECT_BASE_URL}/auth/callback` so the OIDC callback lands on the frontend origin and the session cookie is set there. When **not** provided (standalone BFF), default to the BFF's own origin: `https://localhost:<port>/auth/callback`. See `references/oidc.md`.

### 1a. Authentication strategy

Determine the strategy using this priority order:

1. **Caller provided it** — if invoked by another workflow that already knows the project type: Web App (BFF) → **OpenID Connect**; Stateless API → **JWT Bearer**. Do not ask.
2. **Derive from the user's request** — "login", "web app", "sign in", "session", "cookie auth" → **OpenID Connect**. "bearer token API", "stateless", "validate tokens", "service-to-service", "API-only" → **JWT Bearer**.
3. **Ask the user** if it cannot be derived:

   > What authentication strategy would you like to use?
   > - **OpenID Connect (Recommended)** — BFF web app with cookie-based sessions and server-side token management
   > - **JWT Bearer** — Stateless API that validates bearer tokens from callers

   Default to **OpenID Connect**.

One strategy per project. Do **not** prompt about Redis — only configure it if the user explicitly asks (OIDC only; see `references/oidc.md`).

### 1b. Project name

Determine the project name using this priority order:

1. If the user explicitly provides a name, use it.
2. An existing `package.json` `name` field.
3. The Git repository name (`git remote get-url origin`).
4. The repo root folder name.
5. The current working directory name.

Convert to a valid npm package name (lowercase, kebab-case); keep a PascalCase display form for docs. Present the derived name to the user for confirmation.

> **Important**: Never derive the project name from an output or scratch directory path (like `outputs/`, `temp/`, `workspace/`). If the working directory is clearly transient, ask the user or use a sensible default like `veracity-app`.

## Phase 2: Ensure the Baseline Project Exists & Detect the Framework

Detect whether a baseline Node project already exists, and if so which **web framework** it uses — the auth is integrated idiomatically per framework (**Express**, **Fastify**, or **NestJS**):

- Look for a `package.json` and an application entry point (e.g. `src/app.ts` / `src/server.ts` / `src/main.ts`, or `app.js`/`index.js`). Then determine the framework from `package.json` dependencies:
  - `@nestjs/core` present → **NestJS** (also note `@nestjs/platform-fastify` vs the default `@nestjs/platform-express`).
  - `fastify` present (without `@nestjs/core`) → **Fastify**.
  - `express` present (without `@nestjs/core`) → **Express**.
  - If several match, prefer the one that owns the application entry point and **state the assumption** to the user.

**If no project exists → scaffold it first via the `web-backend-node` skill** (which produces an **Express** baseline).

Invoke the **`web-backend-node`** skill, passing:
- the **project name** resolved in Phase 1b,
- the target **location** (current working directory by default),
- the desired **port** (ask the user; default **54438**).

After `web-backend-node` completes, you will have a clean, building **Express** baseline (helmet, zod env config, health checks, `/api/v1` anchor, error handler). Proceed to Phase 3 to integrate authentication into it using the **Express** adapter.

**If a project already exists → skip scaffolding** and proceed directly to Phase 3, integrating auth into the existing project using the adapter for its **detected framework**. Add only what is missing; preserve existing routes, middleware, services, and config.

> New-project scaffolding is **Express-only** (via `web-backend-node`). Fastify and NestJS are supported for **existing** projects — this skill never scaffolds a new Fastify or NestJS app.

> In all cases, the remaining work is the same shape: you are **integrating Veracity authentication into an existing baseline project** using the adapter that matches its framework. The only differences are whether that baseline was just created by `web-backend-node` (Express) or already present (Express/Fastify/NestJS), and which asset set you copy.

### Integrating into a pre-existing project

The baseline conventions this skill relies on may be partially missing in a pre-existing app. Add additively:

- If there is no zod-validated env module, add one (see `web-backend-node`'s `src/config/env.ts` pattern) or extend the project's existing config mechanism with the strategy's env vars. NestJS apps often use `@nestjs/config` (`ConfigService`) — either add the zod `env` module or read the same variables via the project's `ConfigService`.
- Ensure `.gitignore` covers `.env.local` before writing any secrets guidance.
- Ensure `helmet` (or equivalent security headers) and anonymous health endpoints exist; add them via the `web-backend-node` skill's existing-project integration if missing. Fastify uses `@fastify/helmet`; NestJS registers `helmet` in `main.ts`.
- Respect the project's structure and module system. Place auth files consistently with the surrounding code (e.g. `src/auth/`). **The templates use ESM `.js` import specifiers** (matching the Express baseline). If the project compiles to **CommonJS** (the NestJS default), drop the `.js` extension from the relative imports in every copied file.

## Phase 3: Apply Authentication

Read the reference file for the chosen strategy and follow its complete integration workflow:

| Strategy chosen | Reference file |
|-----------------|----------------|
| OpenID Connect | `references/oidc.md` |
| JWT Bearer | `references/jwt.md` |

The reference file contains everything needed: which packages to add, which asset files to copy (it has a **"Choose your framework"** section for Express / Fastify / NestJS), the env-schema fields to add to `src/config/env.ts`, the exact wiring into the app bootstrap (`app.ts` / Fastify instance / `main.ts` + `AppModule`), per-environment tenant values, credential collection, verification, and error recovery.

**Pipeline ordering** when weaving auth in (existing middleware/plugins/modules stay put; insert only what's missing). The principle is identical across frameworks — **security headers first, health endpoints anonymous and above auth, auth next, protected routers after, error handler last**:

- **Express** (`app.ts`):
  1. `helmet` + `express.json()` (baseline)
  2. Health endpoints (baseline — **above** auth, always anonymous)
  3. **Auth**: OIDC → `session(...)` + `registerAuthRoutes(app)`; JWT → nothing global (apply `requireAuth` per-router). For OIDC, wire `secret: env.SESSION_SECRET` **directly — never a `?? "…"` fallback** (CWE-259; see the "Never hard-code a fallback secret" rule in `references/oidc.md`).
  4. Protected feature routers / the `/api/v1` anchor
  5. Global error handler last (baseline)
- **Fastify** (instance registration order): `@fastify/helmet` → health routes → OIDC: `@fastify/cookie` + `@fastify/session` then the `authRoutes` plugin (JWT: none global; apply the `requireAuth` `preHandler` per-route/scope) → protected route plugins → `setErrorHandler` last.
- **NestJS** (`main.ts` + `AppModule`): `app.use(helmet())`; OIDC → `app.set("trust proxy", 1)` and `app.use(session({...}))` before requests are handled; import `AuthModule`/`JwtModule` (and optionally `VeracityModule`) into `AppModule`; apply guards via `@UseGuards(...)`; health endpoints stay unguarded.

> **Important**: Read only the reference file for the chosen strategy. Do not read the other strategy's file.

> **Critical**: Use the asset template files as the source of truth for generated code: the shared `assets/core/*` plus the per-framework adapter set (`assets/express/*`, `assets/fastify/*`, or `assets/nestjs/*`) matching the detected framework, and `assets/{framework}/apiclient/*` for the API client. Do not improvise or rewrite these files from memory — copy from the templates and replace only the documented placeholders (`__PROJECT_NAME__`, `__PROJECT_SLUG__`). The templates contain Veracity-specific patterns (B2C authority construction, `__Host-` cookie rules, `/api/*` 401 behavior, token acquisition) that must be preserved exactly. Copy the `core/*` files once, then the adapter set for the project's framework.

## Phase 4: Veracity API Client (optional, OIDC BFF by default)

Follow `references/apiclient.md`. Generate the Veracity Platform API V3/V4 typed client with `openapi-typescript` + `openapi-fetch`, add the auth-injecting middleware (bearer token from MSAL `acquireTokenSilent` + `Ocp-Apim-Subscription-Key`), and the BFF proxy endpoints under the **same versioned contract as the .NET BFF** — V3: `/api/v1/veracity/v3/services`, `/api/v1/veracity/v3/notifications/count`, `/api/v1/veracity/v3/policy/validate`; V4: `/api/v1/veracity/v4/me/applications`, `/api/v1/veracity/v4/me/tenants`, `/api/v1/veracity/v4/policy/validate`, `/api/v1/veracity/v4/tenants/{tenantId}/applications`. Because these paths match the `veracity-auth-ui` frontend contract, **this Node BFF can serve a `veracity-auth-ui` frontend exactly as the .NET BFF does**.

> The proxy endpoints require a signed-in user's token, so they apply to the **OIDC BFF** project. For a JWT Bearer API that needs to call the Veracity API service-to-service, see the client-credentials note in `references/apiclient.md`.

## Phase 5: Secure & Verify

- [ ] **Generate a gitignored `.env.local` scaffold.** Confirm `.gitignore` covers `.env.local` first, then write a `.env.local` containing a line for every secret and app-registration value the chosen strategy needs so the user only has to fill in the placeholder values (not create the file):
  - OIDC: `CLIENT_ID`, `CLIENT_SECRET` (placeholders for the user), `SESSION_SECRET` (and `REDIS_URL` if Redis was requested).
    - **`SESSION_SECRET` is auto-generated, not a placeholder.** Generate a strong 32-byte random value and write the real value directly: `node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"`. It must satisfy the required `z.string().min(32)` schema field; the app fails fast if it is missing. Never wire it with a hard-coded `?? "…"` fallback in code.
  - JWT: any client-credentials secret the app needs (e.g. `CLIENT_SECRET`) — often none.
  - Veracity API client (Phase 4): `VERACITY_SUBSCRIPTION_KEY`. `VERACITY_SERVICE_ID` is required **only** for the **V4** `policy/validate` endpoint — the V3 `policy/validate` endpoint does not need it, so omit it for V3-only apps.
  - Never put real secret values in `.env` (committed) or `.env.example` — only placeholders in `.env.local`.
- [ ] Feature routers default to requiring authentication; opt out explicitly for anonymous routes (OIDC: mount after the auth middleware; JWT: apply `requireAuth`).
- [ ] Health endpoints remain anonymous (above any auth middleware).
- [ ] `helmet` stays registered before all routes; extend the CSP with `https://*.veracity.com` in `imgSrc`/`connectSrc` when the app loads Veracity CDN assets.
- [ ] Run the strategy reference's VERIFY checklist (`npm run build`, auth endpoints behave, unauthenticated `/api/*` → `401`).

## Phase 6: Document

- [ ] Generate / update `README.md`: architecture, setup, port, env vars, how to set secrets in `.env.local`, and (if generated) how to regenerate the Veracity API client (`npm run veracity:gen`).
- [ ] Generate `AGENTS.md` with project architecture and agent instructions.
- [ ] Verify the full project builds (`npm run build`) and tests pass (`npm test`).

## Recommended Technical Stack

| Concern | Library | Notes |
|---------|---------|-------|
| OIDC confidential client (BFF) | **`@azure/msal-node`** | Direct MSAL port of `Microsoft.Identity.Web`; auth-code + PKCE, token cache, `acquireTokenSilent` for downstream Veracity API tokens |
| Web framework | **Express** / **Fastify** / **NestJS** | Shared framework-agnostic core (`assets/core/*`) + an idiomatic adapter per framework (Express middleware/routes, Fastify plugins/hooks, NestJS guards/modules/controllers) |
| Session / cookie (BFF) | **`express-session`** (Express & NestJS) / **`@fastify/session`** + **`@fastify/cookie`** (Fastify) | `__Host-` cookie; optional `connect-redis` + `ioredis` for multi-instance |
| JWT Bearer validation | **`jose`** | `createRemoteJWKSet` + `jwtVerify`, `clockTolerance: 60` (matches .NET 1-min skew) |
| Veracity API V3/V4 client | **`openapi-typescript`** + **`openapi-fetch`** | Typed client generated from the OpenAPI spec; middleware injects bearer + subscription key |

> **Why `@azure/msal-node` over `openid-client`?** Both work against B2C. MSAL is chosen because it reproduces the .NET token-cache + downstream-token-acquisition model 1:1, which the Veracity API client depends on (`acquireTokenSilent` for the API scope).

## References

- `references/oidc.md` — OIDC BFF strategy: MSAL confidential client, session, auth routes, env vars, optional Redis, error recovery.
- `references/jwt.md` — JWT Bearer strategy: jose JWKS validation, env vars, error recovery.
- `references/apiclient.md` — Veracity API V3/V4 typed client + BFF proxy endpoints.

## Assets (Code Templates)

Copy the **shared core** (once) plus the **adapter set for the detected framework**. All adapter files land in the same target paths (`src/auth/*`, `src/veracity/*`), so a project uses `core/*` + exactly one of `express/` \| `fastify/` \| `nestjs/`.

**Shared core (`assets/core/`, framework-agnostic — always copy):**

| Asset | Target Path | Description |
|-------|-------------|-------------|
| `assets/core/msalClient.ts` | `src/auth/msalClient.ts` | MSAL ConfidentialClientApplication + token acquisition (OIDC & API client) |
| `assets/core/claims.ts` | `src/auth/claims.ts` | `SessionUser` shape + `mapClaims` (OIDC) |
| `assets/core/jwtVerifier.ts` | `src/auth/jwtVerifier.ts` | jose JWKS validation core: `extractBearer`, `verifyBearerToken` (JWT) |
| `assets/core/veracityApiClient.ts` | `src/veracity/veracityApiClient.ts` | openapi-fetch client + `veracityApiFetch`, `parsePolicyRedirect`, `acquireUserApiToken` (API client) |

**Express adapter (`assets/express/`):**

| Asset | Target Path | Description |
|-------|-------------|-------------|
| `assets/express/oidc/authMiddleware.ts` | `src/auth/authMiddleware.ts` | Session guard; `/api/*` → 401, else challenge |
| `assets/express/oidc/authRoutes.ts` | `src/auth/authRoutes.ts` | `/auth`, `/auth/challenge`, `/auth/callback`, `/api/me`, `/signOut` |
| `assets/express/jwt/jwtMiddleware.ts` | `src/auth/jwtMiddleware.ts` | `requireAuth` bearer middleware (uses core verifier) |
| `assets/express/apiclient/veracityApiMiddleware.ts` | `src/veracity/veracityApiMiddleware.ts` | `userApiToken(req)` + re-exports of the core helpers |
| `assets/express/apiclient/apiV3Routes.ts` | `src/veracity/apiV3Routes.ts` | BFF V3 proxy routes under `/api/v1/veracity/v3/...` |
| `assets/express/apiclient/apiV4Routes.ts` | `src/veracity/apiV4Routes.ts` | BFF V4 proxy routes under `/api/v1/veracity/v4/...` |

**Fastify adapter (`assets/fastify/`):**

| Asset | Target Path | Description |
|-------|-------------|-------------|
| `assets/fastify/oidc/authPlugin.ts` | `src/auth/authPlugin.ts` | `requireAuth` `preHandler`; `/api/*` → 401, else challenge; session augmentation |
| `assets/fastify/oidc/authRoutes.ts` | `src/auth/authRoutes.ts` | Auth endpoints as a Fastify plugin |
| `assets/fastify/jwt/jwtPlugin.ts` | `src/auth/jwtPlugin.ts` | `requireAuth` `preHandler` bearer validation (uses core verifier) |
| `assets/fastify/apiclient/veracityApiHelpers.ts` | `src/veracity/veracityApiHelpers.ts` | `userApiToken(request)` + re-exports of the core helpers |
| `assets/fastify/apiclient/apiV3Routes.ts` | `src/veracity/apiV3Routes.ts` | BFF V3 proxy plugin under `/api/v1/veracity/v3/...` |
| `assets/fastify/apiclient/apiV4Routes.ts` | `src/veracity/apiV4Routes.ts` | BFF V4 proxy plugin under `/api/v1/veracity/v4/...` |

**NestJS adapter (`assets/nestjs/`):**

| Asset | Target Path | Description |
|-------|-------------|-------------|
| `assets/nestjs/oidc/session.types.ts` | `src/auth/session.types.ts` | express-session `SessionData` augmentation |
| `assets/nestjs/oidc/msal.service.ts` | `src/auth/msal.service.ts` | Injectable `MsalService` wrapping the core MSAL client |
| `assets/nestjs/oidc/session-auth.guard.ts` | `src/auth/session-auth.guard.ts` | `SessionAuthGuard` (`CanActivate`) → 401 when unauthenticated |
| `assets/nestjs/oidc/auth.controller.ts` | `src/auth/auth.controller.ts` | `/auth`, `/auth/challenge`, `/auth/callback`, `/api/me`, `/signOut` |
| `assets/nestjs/oidc/auth.module.ts` | `src/auth/auth.module.ts` | `AuthModule` wiring service + guard + controller |
| `assets/nestjs/jwt/jwt-auth.guard.ts` | `src/auth/jwt-auth.guard.ts` | `JwtAuthGuard` (`CanActivate`) bearer validation (uses core verifier) |
| `assets/nestjs/jwt/jwt.module.ts` | `src/auth/jwt.module.ts` | `JwtModule` exporting the guard |
| `assets/nestjs/apiclient/veracity-api.service.ts` | `src/veracity/veracity-api.service.ts` | Injectable `VeracityApiService` (`userApiToken` + core helpers) |
| `assets/nestjs/apiclient/veracity-v3.controller.ts` | `src/veracity/veracity-v3.controller.ts` | V3 proxy controller under `/api/v1/veracity/v3/...` |
| `assets/nestjs/apiclient/veracity-v4.controller.ts` | `src/veracity/veracity-v4.controller.ts` | V4 proxy controller under `/api/v1/veracity/v4/...` |
| `assets/nestjs/apiclient/veracity.module.ts` | `src/veracity/veracity.module.ts` | `VeracityModule` wiring the service + controllers |

> Asset files use the placeholder `__PROJECT_NAME__` (display) and `__PROJECT_SLUG__` (npm/package name); replace both when copying, mirroring the `ProjectName` pattern in the .NET assets.

> **Module system note**: templates use ESM `.js` import specifiers (matching the `web-backend-node` Express baseline). For a **CommonJS** project (the NestJS default — `"module": "commonjs"`), drop the `.js` extension from the relative imports in every copied file.
