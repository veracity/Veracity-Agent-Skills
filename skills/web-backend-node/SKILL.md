---
name: web-backend-node
description: "Scaffold a new NodeJS (Express 5 + TypeScript) web backend with the standard baseline capabilities every backend service needs: zod-validated env config with .env layering, helmet security headers with a Content-Security-Policy, health checks (live/ready), a versioned API router anchor (/api/v1), a global error handler, optional HTTPS for local dev, ESLint/Prettier, and vitest + supertest. USE THIS SKILL whenever the user wants to create a new NodeJS or Express backend, bootstrap a Node API service, scaffold a Node/Express + TypeScript web project skeleton, or needs a clean Node baseline project to build on. This skill does NOT add authentication — it produces an unauthenticated baseline. For Veracity login/JWT on a Node backend, use veracity-auth-node (which calls this skill first when no project exists)."
---

# NodeJS Web Backend Scaffolding

This skill creates a new **Express 5 + TypeScript** project with a production-sensible baseline — but **no authentication**. It is the NodeJS sibling of `web-backend-net` and the foundation other skills build on (`veracity-auth-node` calls it before layering Veracity authentication on top).

## What this skill produces

| Capability | Detail | .NET equivalent (`web-backend-net`) |
|------------|--------|-------------------------------------|
| Web framework | Express 5 + TypeScript (ESM, Node ≥ 20) | ASP.NET Minimal API |
| Versioned API anchor | `src/routes/apiV1.ts` router mounted at `/api/v1` | `Asp.Versioning` versioned `apiGroup` |
| Config / secrets | `dotenv` layering (`.env` → `.env.<NODE_ENV>` → `.env.local`) validated with `zod`, fail-fast | appsettings + `dotnet user-secrets` |
| Health checks | `/health`, `/health/ready`, `/health/live` (all anonymous) | Health checks |
| Security | `helmet` with an explicit locked-down CSP (`useDefaults:false`) matching the .NET policy | `SecurityHeadersMiddleware` + CSP section |
| Error handling | Global error handler returning a ProblemDetails-style JSON body | Global `ProblemDetails` exception handler |
| Request validation | `zod` (also validates env) | FluentValidation |
| HTTPS local dev | Optional via `TLS_CERT_FILE` / `TLS_KEY_FILE` (mkcert) | HTTPS `launchSettings.json` |
| Tests / tooling | `vitest` + `supertest`; `tsx` dev, `tsc` build, ESLint + Prettier | — |

It does **not** add authentication, authorization, cookies, OIDC, JWT, sessions, or any Veracity-specific packages or endpoints. The `/api/v1` router is **not** protected — protection is added later by an auth skill.

> **CSP is explicit and locked down.** The scaffolded `app.ts` sets `helmet`'s CSP with `useDefaults: false` and an explicit directive set (`base-uri 'none'`, `default-src 'self'`, `script-src 'self'`, `style-src 'self'`, `frame-src 'none'`, `worker-src 'self' blob:`, etc.), so the baseline has no external dependencies. Auth skills (e.g. `veracity-auth-node`) extend the directives when they add their own CDN and login endpoints.

## Phase 1: Mode Detection

Determine whether the user wants to:

1. **Create a new project** — scaffold from scratch (the default).
2. **Integrate into an existing project** — add only the missing baseline capabilities to an existing Node app (skip project creation, adapt to existing structure).

When integrating into an existing project:
- Locate `package.json` and understand the current project structure (entry point, framework, TS vs JS).
- Add only the dependencies not already present.
- Merge env/config conventions without overwriting existing settings.
- Preserve existing routes, middleware, and services unless they conflict.

> **Invoked by another skill?** When this skill is called by `veracity-auth-node` (or another orchestrating skill), the caller passes the resolved **project name**, the target **location**, and the **port**. Use those values directly and skip the resolution/questions below.

## Phase 2: Project Name Resolution

Determine the project name automatically using this priority order:

1. If the user (or calling skill) explicitly provides a name, use it.
2. An existing `package.json` `name` field.
3. The Git repository name (`git remote get-url origin`).
4. The repo root folder name.
5. The current working directory name.

Convert to a valid npm package name (lowercase, kebab-case) → `__PROJECT_SLUG__`; keep a PascalCase display form → `__PROJECT_NAME__`. Present the derived name to the user for confirmation (skip when a calling skill provided it).

> **Important**: Never derive the project name from an output or scratch directory path (like `outputs/`, `temp/`, `workspace/`). If the working directory is clearly a transient location, fall back to asking the user or use a sensible default like `demo-api`.

Place the project at the repo root when it is empty, or under a folder named after the project when the repo already contains other content (mirroring the `src/{ProjectName}/` convention used by the .NET skills when siblings exist).

## Phase 3: Port

Ask the user what port to use for local development. If the user (or calling skill) does not provide one, use **54438** (parity with the .NET baseline).

The port is configured via `PORT` in `.env` — substitute it when generating `.env.example`/`.env` if it differs from the default.

## Phase 4: Project Structure

```
{project}/
├── package.json
├── tsconfig.json
├── .env.example
├── .gitignore
└── src/
    ├── server.ts          # bootstrap + listen (HTTP, or HTTPS when TLS_* set)
    ├── app.ts             # helmet, json, health, /api/v1 mount, error handler
    ├── config/
    │   └── env.ts         # zod-validated environment loader
    └── routes/
        └── apiV1.ts       # versioned API router anchor (empty seam)
```

## Phase 5: Generate Files

Use the template files from `assets/` as the source of truth. Replace `__PROJECT_SLUG__` (npm name) and `__PROJECT_NAME__` (display name) placeholders when copying.

> **Critical**: Copy from the asset templates — do not improvise or rewrite these files from memory. Replace only the documented placeholders.

| Asset | Target |
|-------|--------|
| `assets/package.json` | `package.json` |
| `assets/tsconfig.json` | `tsconfig.json` |
| `assets/server.ts` | `src/server.ts` |
| `assets/app.ts` | `src/app.ts` |
| `assets/env.ts` | `src/config/env.ts` |
| `assets/apiV1.ts` | `src/routes/apiV1.ts` |
| `assets/.env.example` | `.env.example` |

Also:

- Ensure a `.gitignore` exists (create if missing) containing at least:

  ```gitignore
  node_modules/
  dist/
  *.log
  .env.local
  .env.*.local
  ```

- Optionally generate a minimal `eslint.config.js` and `.prettierrc` (the `package.json` template already carries the scripts and devDependencies).
- Tell the user to copy `.env.example` → `.env.local` for any local overrides; secrets go **only** in `.env.local` (gitignored) locally, and environment variables / Azure Key Vault when deployed. Never ask the user to paste secret values into the chat.

## Phase 6: Verify

```bash
npm install
npm run build
```

The build must compile with no TypeScript errors. Start the app (`npm run dev`) and confirm:

- `GET /health`, `/health/ready`, `/health/live` return `200` without authentication.
- Security headers are present (`curl -I http://localhost:<port>/health`).

## HTTPS for Local Dev (optional)

`server.ts` serves HTTPS when `TLS_CERT_FILE` / `TLS_KEY_FILE` are set, otherwise plain HTTP. To use HTTPS locally, the developer generates a trusted localhost cert themselves — for example with a tool such as [`mkcert`](https://github.com/FiloSottile/mkcert) (trusting the cert is a one-time manual machine setup you run outside this skill) — and points the env vars at the resulting files. Plain HTTP is fine when the app sits behind an HTTPS dev proxy (e.g. a Vite frontend).

## Rate Limiting (optional — only when explicitly requested)

Do **not** add rate limiting by default. When the user asks for it, add `express-rate-limit` and apply named limiters per-route:

```ts
import rateLimit from "express-rate-limit";

const publicLimiter = rateLimit({ windowMs: 60_000, limit: 100 });
app.use("/api/public", publicLimiter);
```

## Adding endpoints

For the pattern to add new versioned routes after scaffolding, read `references/new-endpoints.md`.

## Existing Project Integration

When adding the baseline to an existing Node project, adapt the steps above. The guiding principle is **additive, not destructive**: the user has working code, so add only what's missing and leave everything else — routes, services, config, scripts — exactly as it is.

1. Add only the npm dependencies not already present in `package.json`.
2. Add the zod-validated env loader (`src/config/env.ts`) only if the project has no equivalent config module; otherwise extend the existing one.
3. Register `helmet` only if no security-header middleware exists.
4. Add the health endpoints and the `/api/v1` router anchor only where not already present.
5. Merge `.gitignore` entries (especially `.env.local`) without removing existing ones.

### Middleware & pipeline ordering

Ordering matters in Express, so when inserting baseline middleware into an existing `app.ts`, follow the same relative order the new-project template uses — inserting only the missing pieces and leaving existing middleware in place:

1. `helmet` — first, so headers apply to every response.
2. `express.json()` body parsing.
3. The `/health`, `/health/ready`, `/health/live` endpoints — before any auth middleware, so they are never protected.
4. (Auth middleware slot — added later by an auth skill.)
5. The `/api/v1` versioned router and feature routes.
6. The global error handler — registered **last**.

### Existing endpoints and the versioned router

Add the `/api/v1` router anchor so future endpoints have a versioned seam. **Leave the user's existing routes exactly where they are** — do not move or re-route them into the versioned router; changing their URLs would break callers. It's fine for `apiV1` to start out empty.
