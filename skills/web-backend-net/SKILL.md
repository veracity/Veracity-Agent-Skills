---
name: web-backend-net
description: "Scaffold a new .NET 10 Minimal API web project with the standard baseline capabilities every backend service needs: API versioning (URL segment + header), OpenAPI/Swagger, FluentValidation, health checks (live/ready), a Content-Security-Policy and security-headers middleware, a global ProblemDetails error handler, per-environment appsettings, and HTTPS launch settings. USE THIS SKILL whenever the user wants to create a new .NET 10 minimal API project, bootstrap a backend service, scaffold a web API skeleton, set up a new .NET web project with sensible defaults, or needs a clean baseline project to build on. This skill does NOT add authentication — it produces an unauthenticated baseline."
---

# .NET Web Backend Scaffolding

This skill creates a new **.NET 10 Minimal API** project with a production-sensible baseline — but **no authentication**. It is the foundation other skills build on.

## What this skill produces

| Capability | Detail |
|------------|--------|
| API versioning | `Asp.Versioning` with URL-segment (`/api/v1/...`) and `X-Api-Version` header readers, default v1.0 |
| OpenAPI / Swagger | `Swashbuckle.AspNetCore`, Swagger UI in Development |
| Validation | `FluentValidation` with assembly scanning |
| Health checks | `/health`, `/health/ready`, `/health/live` (all anonymous) |
| Security | `SecurityHeadersMiddleware` + CSP bound from the `CSP` config section |
| Error handling | Global `ProblemDetails` exception handler |
| Config | `appsettings.json` (+ CSP — generic `'self'`-only defaults), `appsettings.Development.json` |
| Launch | HTTPS `launchSettings.json` on a fixed port |

It does **not** add authentication, authorization, cookies, OIDC, JWT, or any Veracity-specific packages or endpoints. The generated versioned API group is **not** protected — protection is added later by an auth skill.

> **CSP defaults are intentionally generic.** The scaffolded `appsettings.json` ships with `'self'`-only CSP sources so the baseline has no external dependencies. Auth skills (e.g. `veracity-auth-net`) extend the CSP when they add their own CDN and login endpoints.

## Phase 1: Mode Detection

Determine whether the user wants to:

1. **Create a new project** — scaffold from scratch (the default).
2. **Integrate into an existing project** — add only the missing baseline capabilities to an existing .NET 10 app (skip project creation, adapt to existing structure).

When integrating into an existing project:
- Locate the `.csproj` file and understand the current project structure.
- Add only the packages not already present.
- Merge configuration into existing appsettings without overwriting existing settings.
- Preserve existing endpoints, middleware, and services unless they conflict.

> **Invoked by another skill?** When this skill is called by `veracity-auth-net` (or another orchestrating skill), the caller passes the resolved **full project name** (including any suffix such as `.Web` or `.Api`), the target **location** (e.g. `src/`), and the **HTTPS port**. Use those values directly and skip the resolution/questions below.

## Phase 2: Project Name Resolution

Determine the project name automatically using this priority order:

1. If the user (or calling skill) explicitly provides a name, use it.
2. Look for a `.sln` file — use its name (e.g., `Contoso.Reporting.sln` → base name `Contoso.Reporting`).
3. Look for a `.csproj` under `src/` — extract the base name by removing known suffixes (`.Web`, `.Api`, `.Client`, `.Service`).
4. Use the Git repository name.
5. Use the repo root folder name.
6. Use the current working directory name, converted to PascalCase.

> **Important**: Never derive the project name from an output or scratch directory path (like `outputs/`, `temp/`, `workspace/`). If the working directory is clearly a transient location, fall back to asking the user or use a sensible default like `Demo`.

If the caller did not specify a suffix, default the project name to `{BaseName}.Web` and place it at `src/{ProjectName}/`.

If no `.sln` file exists at the repository root, create one (e.g. `{BaseName}.sln`) and add the new project to it. This keeps the repo IDE-friendly and makes it easier for auth skills or additional projects to integrate later.

## Phase 3: HTTPS Port

Ask the user what HTTPS port to use for local development in `Properties/launchSettings.json`. If the user (or calling skill) does not provide one, use **54438**.

> What HTTPS port would you like to use for local development? (Default: 54438)

Remember this value — substitute it for `{PORT}` in `launchSettings.json` during file generation.

## Phase 4: Project Structure

```
src/{ProjectName}/
├── Program.cs
├── {ProjectName}.csproj
├── Middleware/
│   ├── CSPOptions.cs
│   └── SecurityHeadersMiddleware.cs
├── Properties/
│   └── launchSettings.json
├── appsettings.json
└── appsettings.Development.json
```

## Phase 5: Generate Files

Use the template files from `assets/` as the source of truth. Replace all `{{ProjectName}}` placeholders with the derived project name (the full name including any suffix).

> **Critical**: Copy from the asset templates — do not improvise or rewrite these files from memory. Replace only the documented placeholders (`{{ProjectName}}`, `{PORT}`).

### Project File (.csproj)

Generate the `.csproj` with:
- `<TargetFramework>net10.0</TargetFramework>`, Nullable and ImplicitUsings enabled.
- A freshly generated GUID for `<UserSecretsId>`.
- Versioning: `Asp.Versioning.Http`, `Asp.Versioning.Mvc.ApiExplorer`.
- Validation: `FluentValidation`, `FluentValidation.DependencyInjectionExtensions`.
- OpenAPI: `Swashbuckle.AspNetCore`, `Swashbuckle.AspNetCore.Annotations`.

Use `dotnet add package` (no explicit version) so NuGet selects current versions.

### Other Files

Copy directly from `assets/`, replacing `{{ProjectName}}` and `{PORT}` where present:
- `Program.cs` → `Program.cs`
- `CSPOptions.cs` → `Middleware/CSPOptions.cs`
- `SecurityHeadersMiddleware.cs` → `Middleware/SecurityHeadersMiddleware.cs`
- `launchSettings.json` → `Properties/launchSettings.json` — replace `{PORT}` with the chosen port (default 54438). **Do not use the default `dotnet new web` launchSettings** — it generates a random port.
- `appsettings.json` → `appsettings.json`
- `appsettings.Development.json` → `appsettings.Development.json`

## Phase 6: Verify

Build the project to confirm the baseline compiles:

```bash
cd src/{ProjectName}
dotnet build
```

The app should start, expose `/swagger` in Development, and answer `/health`, `/health/ready`, and `/health/live`.

## Adding endpoints

For the pattern to add new versioned endpoints after scaffolding, read `references/new-endpoints.md`.

## Existing Project Integration

When adding the baseline to an existing .NET 10 project, adapt the steps above. The guiding principle is **additive, not destructive**: the user has working code, so add only what's missing and leave everything else — endpoints, services, config, launch profiles — exactly as it is.

1. Add only the NuGet packages not already present in the `.csproj`.
2. If the `.csproj` lacks a `<UserSecretsId>`, generate one (a fresh GUID) — user-secrets are useful during local development for the CSP and any future config the baseline introduces.
2. Add `CSPOptions.cs` and `SecurityHeadersMiddleware.cs` to a `Middleware/` folder (using the existing project's root namespace, not `{{ProjectName}}`).
3. Add API versioning, Swagger, FluentValidation, health checks, the CSP binding, and the global error handler to `Program.cs` only where not already configured. Skip any that the project already sets up.
4. Merge the `CSP` configuration section into existing appsettings without overwriting existing keys.

### Middleware & pipeline ordering

Ordering matters in the request pipeline, so when you insert the baseline middleware into an existing `Program.cs`, follow the same relative order the new-project `assets/Program.cs` uses — inserting only the pieces that aren't already there and leaving any existing middleware in place:

1. `app.UseExceptionHandler(...)` — the global `ProblemDetails` handler goes first so it can catch failures from everything after it.
2. Swagger (`UseSwagger` / `UseSwaggerUI`) in Development.
3. `app.UseHttpsRedirection();`
4. `app.UseMiddleware<SecurityHeadersMiddleware>();` — before endpoints so headers apply to every response.
5. The `/health`, `/health/ready`, `/health/live` endpoint mappings.

If the project already has, say, its own exception handler or `UseHttpsRedirection`, don't duplicate it — just slot the missing pieces into the right position relative to what's there.

### Existing endpoints and the versioned group

Add the versioned group scaffold (`app.NewVersionedApi()` → `apiGroup = ...MapGroup("/api/v{version:apiVersion}").HasApiVersion(1.0)`) so future endpoints have a versioned anchor (see [`references/new-endpoints.md`](references/new-endpoints.md)). **Leave the user's existing endpoints exactly where they are** — do not move, re-route, or rewrite them into the versioned group. It's fine for `apiGroup` to start out with no endpoints attached; it's the seam new work hangs off, and moving existing routes would change their URLs and break callers.

### Launch settings

Do **not** overwrite an existing `Properties/launchSettings.json` — it already carries the project's ports and profiles. Only create one from the template (Phase 3 port handling) if the project doesn't have one.
