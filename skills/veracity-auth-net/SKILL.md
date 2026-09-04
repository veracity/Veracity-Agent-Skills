---
name: veracity-auth-net
description: "Add Veracity authentication to a .NET 8 or later backend: OpenID Connect (BFF/cookie sessions, default) or JWT Bearer (stateless token validation), plus optional Veracity V3/V4 API calls for the signed-in user. Integrates using the existing project's style — Minimal API or MVC Controllers — and scaffolds a .NET 10 Minimal API baseline via web-backend-net if no project exists. USE THIS whenever the user wants Veracity login/auth on a .NET app, a Veracity BFF, a .NET API that validates Veracity JWT bearer tokens, Veracity OpenID Connect / cookie sessions, or Veracity V3/V4 integration from a .NET backend. Do NOT use for: a plain .NET baseline with no Veracity (use web-backend-net); a complete/full web app or 'web app with Veracity login' that also needs a frontend UI (use veracity-auth-ui, which calls this skill for the BFF); Veracity login/profile widgets on a frontend or React/SPA (use veracity-auth-ui); non-.NET backends; or non-Veracity providers (Entra ID, Auth0, IdentityServer)."
license: Apache-2.0
---

# Veracity Authentication for .NET

This skill adds **Veracity authentication** to a **.NET 8 or later** backend project. Freshly-scaffolded projects (via `web-backend-net`) are **.NET 10**; existing projects may be .NET 8, 9, or 10 — all are supported. It supports two authentication strategies:

- **OpenID Connect (default)** — For BFF (Backend-For-Frontend) web apps that manage user sessions with cookies.
- **JWT Bearer** — For stateless APIs consumed by SPAs, mobile apps, or service-to-service calls where the caller already holds a bearer token.

It also wires up optional **Veracity V3/V4 API** integration (OIDC) and **Swagger OAuth2** (JWT).

> **Separation of concerns**: This skill does **not** scaffold the baseline project itself. The baseline (API versioning, OpenAPI/Swagger, FluentValidation, health checks, CSP/security-headers middleware, global error handler, appsettings, launch settings) is owned by the **`web-backend-net`** skill. This skill ensures that baseline exists (creating it via `web-backend-net` when missing) and then layers Veracity authentication on top.

## Phase 1: Determine Project Name & Strategy

Resolve these two things first, because they determine the scaffold's project name and suffix.

### 1 (pre). Optional caller parameter — `REDIRECT_BASE_URL`

When this skill is invoked **by another skill** (e.g. `veracity-auth-ui`), the caller may pass a `REDIRECT_BASE_URL` (e.g. `https://localhost:5173`). This is the HTTPS origin that the **browser** will use — the frontend dev server, not the BFF directly. When provided, it overrides the BFF's own HTTPS base URL when writing `RedirectUrl` in `appsettings.Development.json` (see Step 5 in `references/oidc.md`).

- **Provided by caller** → use `{REDIRECT_BASE_URL}/signin-oidc` as the `RedirectUrl`.
- **Not provided (standalone use)** → default to the BFF's own HTTPS URL: `https://localhost:{BFF_PORT}/signin-oidc`.

Store this value as `{REDIRECT_BASE_URL}` for use in Phase 3.

### 1a. Authentication strategy

Determine the strategy using this priority order:

1. **Derive from the user's request** — "JWT", "bearer token", "stateless API", "API-only" → **JWT Bearer**. "BFF", "web app", "login page", "cookie auth" → **OpenID Connect**.
2. **Derive from project context** — if an existing `.csproj` is found: name ends in `.Web` → **OpenID Connect**; name ends in `.Api` → **JWT Bearer**.
3. **Ask the user** if it cannot be derived:

   > What authentication strategy would you like to use?
   > - **OpenID Connect (Recommended)** — BFF web app with cookie-based sessions and server-side token management
   > - **JWT Bearer** — Stateless API that validates bearer tokens from callers

   Default to **OpenID Connect**.

### 1b. Project name

Determine the base project name using this priority order:

1. If the user explicitly provides a name, use it.
2. Look for a `.sln` file — use its base name (e.g., `Veracity.Common.Auth.sln` → `Veracity.Common.Auth`).
3. Look for a `.csproj` under `src/` — remove known suffixes (`.Web`, `.Api`, `.Client`, `.Service`).
4. Use the Git repository name.
5. Use the repo root folder name.
6. Use the current working directory name, converted to PascalCase.

> **Important**: Never derive the project name from an output or scratch directory path (like `outputs/`, `temp/`, `workspace/`). If the working directory is clearly transient, ask the user or use `Veracity.App`.

The final project name suffix depends on the strategy:
- **OpenID Connect**: `{BaseName}.Web` → `src/{BaseName}.Web/`
- **JWT Bearer**: `{BaseName}.Api` → `src/{BaseName}.Api/`

## Phase 2: Ensure the Baseline Project Exists

Detect whether a baseline project already exists (it may target .NET 8, 9, or 10):

- Look for a `.csproj` (typically under `src/`) with a `Program.cs` that already configures the baseline (API versioning, health checks, `SecurityHeadersMiddleware`).

**If no project exists → scaffold it first via the `web-backend-net` skill.**

Invoke the **`web-backend-net`** skill, passing:
- the **full project name including the suffix** chosen in Phase 1b (e.g. `{BaseName}.Web` for OIDC, `{BaseName}.Api` for JWT),
- the location `src/{ProjectName}/`,
- the desired **HTTPS port** (ask the user; default **54438**).

After `web-backend-net` completes, you will have a clean, building baseline project. Proceed to Phase 3 to integrate authentication into it.

**If a project already exists → skip scaffolding** and proceed directly to Phase 3, integrating auth into the existing project. Add only what is missing; preserve existing endpoints, middleware, services, and config.

> In both cases, the remaining work is identical: you are **integrating Veracity authentication into an existing baseline project**. The only difference is whether that baseline was just created by `web-backend-net` or already present.

## Phase 2.5: Determine the Project's API Style

The generated auth code must match how the project already exposes HTTP endpoints — **Minimal API** or **MVC Controllers**. Resolve `{PROJECT_STYLE}` before applying auth.

- **Freshly scaffolded (via `web-backend-net` in Phase 2) → always `MinimalApi`.** Skip detection; `web-backend-net` only produces Minimal API projects.
- **Pre-existing project → detect the style** by inspecting the project:

  | Signal | Indicates |
  |--------|-----------|
  | A `Controllers/` folder with `*Controller.cs` classes deriving `ControllerBase`/`Controller`; `[ApiController]` / `[Route]` attributes; `AddControllers()` / `AddControllersWithViews()` / `MapControllers()` in `Program.cs`; or a legacy `Startup.cs` (`ConfigureServices` / `Configure`) | **`Controllers`** |
  | Top-level `app.MapGet` / `MapPost` / `MapGroup` endpoint registrations and no controllers | **`MinimalApi`** |

  Also record `{HOSTING_STYLE}` = `Program` (top-level `Program.cs` minimal hosting) or `Startup` (legacy `Startup.cs`).

- **Decision rule:** if only one style is present, use it **without asking**. Only if the project is **genuinely mixed or ambiguous** (both controllers and hand-mapped endpoints, or neither is clearly dominant), ask the user which style the Veracity auth code should follow (MVC Controllers or Minimal API).

Carry `{PROJECT_STYLE}` and `{HOSTING_STYLE}` into Phase 3.

## Phase 3: Apply Authentication

Read the reference file for the chosen strategy and follow its complete integration workflow:

| Strategy chosen | Reference file |
|-----------------|----------------|
| OpenID Connect | `references/oidc.md` |
| JWT Bearer | `references/jwt.md` |

**If `{PROJECT_STYLE}` is `Controllers`, also read the matching controllers reference file** and follow it for the style-specific parts (which endpoint files to add, `Program.cs`/`Startup.cs` wiring, and `[Authorize]`-based protection):

| Strategy | Controllers reference |
|----------|-----------------------|
| OpenID Connect | `references/controllers-oidc.md` |
| JWT Bearer | `references/controllers-jwt.md` |

The strategy file still governs packages, service-registration/extension files, appsettings, and credentials — the controllers file only overrides the endpoint-shape and pipeline-wiring steps. When `{PROJECT_STYLE}` is `MinimalApi`, follow the strategy file as-is (it is written for Minimal API).

The reference file contains everything needed: which packages to add, which asset files to add, the exact edits to weave auth into `Program.cs`, the appsettings sections to merge, optional Veracity V3/V4 (OIDC) or Swagger OAuth2 (JWT) features, and credential collection.

> **Important**: Read only the reference file for the chosen strategy (plus the matching controllers file when `{PROJECT_STYLE}` is `Controllers` — see the table above). Do not read the other strategy's file.

> **Critical**: Use the asset template files (`assets/*.cs`, `assets/*.json`) as the source of truth for generated code. Do not improvise or rewrite these files from memory — copy from the templates and replace only the documented placeholders (`{{ProjectName}}`, `{{EndpointMapping}}`, `{PORT}`, etc.). The templates contain Veracity-specific patterns (B2C tenant configuration, token cache recovery, MSAL packaging, data protection setup) that must be preserved exactly.

## Additional References

These files provide supplementary guidance — read them only when the user needs the specific topic:

- `references/controllers-oidc.md` — MVC Controllers integration for OpenID Connect (read when `{PROJECT_STYLE}` is `Controllers` + OIDC; see Phase 3)
- `references/controllers-jwt.md` — MVC Controllers integration for JWT Bearer (read when `{PROJECT_STYLE}` is `Controllers` + JWT; see Phase 3)
- `references/production-setup.md` — Redis, Azure Key Vault, and production credential configuration (OIDC)

For the pattern to add new versioned API endpoints after auth is in place, use the **`web-backend-net`** skill's `references/new-endpoints.md` guidance.
