# MVC Controllers — OpenID Connect (BFF) Integration

Read this file **in addition to** `references/oidc.md` **only when Phase 2.5 detected `{PROJECT_STYLE} = Controllers`** for a pre-existing project. Freshly-scaffolded projects (via `web-backend-net`) are always Minimal API and must **not** use this file.

`references/oidc.md` remains the source of truth for **API version choice (Step 1), NuGet packages (Step 2), appsettings (Step 5), and credential collection (Step 6)** — none of that changes with Controllers. This file overrides only the steps that differ:

- **Step 3** — which endpoint asset files to add (Controllers instead of Minimal-API endpoint files)
- **Step 4** — how to weave auth into `Program.cs` or `Startup.cs` (middleware order around `MapControllers`)
- **Protection** — `[Authorize]` attributes instead of `.RequireAuthorization()` on an endpoint group

Throughout, `{{ProjectName}}` is the full project name including the `.Web` suffix (e.g. `MyApp.Web`), living at `src/{{ProjectName}}/`.

---

## Route contract (why literal `api/v1` routes)

The Veracity V3/V4 controllers use **literal routes** — `[Route("api/v1/veracity/v3")]` / `[Route("api/v1/veracity/v4")]` — and the auth routes are unversioned (`/auth`, `/api/me`, `/auth/challenge`, `/signout`). These paths are a **fixed contract** consumed by the `veracity-auth-ui` frontend:

| Path | Purpose |
|------|---------|
| `GET /auth` | Sign-in status (anonymous) |
| `GET /auth/challenge` | Trigger OIDC sign-in (`?returnUrl=` relative) |
| `GET /api/me` | Current user (`401` if not authenticated) |
| `GET /signout` | Clear session |
| `GET /api/v1/veracity/v3/services` | User's services (V3) |
| `GET /api/v1/veracity/v4/me/applications` | User's applications (V4) |

Because the frontend hard-codes the literal `v1` segment, the controllers do **not** depend on `Asp.Versioning.Mvc`. Do not introduce API-versioning attributes or force the existing project to add that package — keep the literal routes exactly as written in the asset templates.

---

## Step 3 (override): Asset files to add

Copy these **instead of** the Minimal-API endpoint files listed in `oidc.md` Step 3 (do **not** add `AuthEndpoints.cs`, `VeracityV3Endpoints.cs`, or `VeracityV4Endpoints.cs`). Replace the `{{ProjectName}}` placeholder in each:

- `assets/controllers/AuthController.cs` → `Controllers/AuthController.cs`
- `assets/controllers/VeracityV3Controller.cs` → `Controllers/VeracityV3Controller.cs` (only if V3 selected in Step 1)
- `assets/controllers/VeracityV4Controller.cs` → `Controllers/VeracityV4Controller.cs` (only if V4 selected in Step 1)

`assets/VeracityAuthExtensions.cs` → `Extensions/VeracityAuthExtensions.cs` is unchanged from `oidc.md` Step 3 — copy it as described there.

---

## Step 4 (override): Weave auth into the pipeline

### `Program.cs` (minimal hosting)

Apply the same **service registration** from `oidc.md` Step 4 (`using Veracity.Common.Authentication;` and `builder.Services.AddVeracityAuthentication(builder.Configuration, builder.Environment);` after the CSP line). Ensure the project registers controllers — if `builder.Services.AddControllers();` is not already present, add it.

Then wire the **middleware pipeline**. Controllers are dispatched by `MapControllers()`, so authentication/authorization must sit between routing and the controller dispatch:

```csharp
app.UseVeracityTokenCacheRecovery();        // BEFORE security headers
app.UseMiddleware<SecurityHeadersMiddleware>();
app.UseRouting();                            // if not already present
app.UseAuthentication();
app.UseVeracity();
app.UseAuthorization();
// ...
app.MapControllers();                        // already present in a Controllers project
```

**Do not** add `app.MapAuthEndpoints()`, `apiGroup.MapV3Endpoints()`, or `apiGroup.MapV4Endpoints()` — those are Minimal-API calls. The controllers are auto-discovered by `MapControllers()`.

### `Startup.cs` (legacy hosting)

If `{HOSTING_STYLE}` is `Startup`:

- In `ConfigureServices(IServiceCollection services)` — add the same registration call:
  ```csharp
  services.AddVeracityAuthentication(Configuration, Environment);
  ```
  (`Configuration` / `Environment` are the usual `Startup` members; inject `IWebHostEnvironment` via the constructor if `Environment` is not already available.) Keep the existing `services.AddControllers();`.

- In `Configure(IApplicationBuilder app, ...)` — place the auth middleware in the same order, between `UseRouting()` and `UseEndpoints(...)`:
  ```csharp
  app.UseVeracityTokenCacheRecovery();
  // existing security-headers middleware
  app.UseRouting();
  app.UseAuthentication();
  app.UseVeracity();
  app.UseAuthorization();
  app.UseEndpoints(endpoints => endpoints.MapControllers());
  ```

---

## Protecting the API

Protection is via the `[Authorize]` attribute already present on `VeracityV3Controller` / `VeracityV4Controller` (and on the `/api/me` action of `AuthController`). The `/auth`, `/auth/challenge`, and `/signout` actions are marked `[AllowAnonymous]`. If the existing project has additional controllers that should require sign-in, add `[Authorize]` to them as needed — do not add a global fallback policy unless the user asks, since that would also lock the anonymous auth endpoints.

---

## Verification

After integration, confirm:

- `GET /auth` returns 200 (anonymous).
- `GET /api/me` returns 401 when signed out.
- `GET /auth/challenge` returns 302 to the Veracity B2C login page.
- `GET /signout` clears the session.
- V3/V4 routes return 401 when signed out and resolve at the literal paths: `GET /api/v1/veracity/v3/services`, `GET /api/v1/veracity/v4/me/applications`.
- `dotnet build` succeeds and the app starts. Middleware order: `UseAuthentication` **before** `UseAuthorization`, both **after** `UseRouting`, and `UseVeracity` between them.
