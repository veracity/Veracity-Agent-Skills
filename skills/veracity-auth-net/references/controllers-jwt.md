# MVC Controllers — JWT ****** Integration

Read this file **in addition to** `references/jwt.md` **only when Phase 2.5 detected `{PROJECT_STYLE} = Controllers`** for a pre-existing project. Freshly-scaffolded projects (via `web-backend-net`) are always Minimal API and must **not** use this file.

`references/jwt.md` remains the source of truth for **Swagger OAuth2 opt-in (Step 1), NuGet packages (Step 2), `JwtAuthExtensions.cs` (Step 3), appsettings (Step 5), and credential collection (Step 6)** — none of that changes with Controllers. This file overrides only the steps that differ:

- **Step 4** — how to weave auth into `Program.cs` or `Startup.cs` (middleware order around `MapControllers`)
- **Protection** — `[Authorize]` attributes on controllers instead of `.RequireAuthorization()` on an endpoint group

JWT ****** stateless — there are **no controller asset files to add** for this strategy (no `AuthController.cs` or Veracity API controllers). Controllers project JWT integration is wiring-only.

Throughout, `{{ProjectName}}` is the full project name including the `.Api` suffix (e.g. `MyApp.Api`), living at `src/{{ProjectName}}/`.

---

## Step 4 (override): Weave auth into the pipeline

### `Program.cs` (minimal hosting)

Apply the `jwt.md` Step 4 service registration (`builder.Services.AddJwtBearerAuthentication(builder.Configuration);` after the CSP line). Ensure `builder.Services.AddControllers();` is present, then place the auth middleware between routing and the controller dispatch:

```csharp
app.UseMiddleware<SecurityHeadersMiddleware>();
app.UseRouting();                            // if not already present
app.UseAuthentication();
app.UseAuthorization();
// ...
app.MapControllers();
```

If Swagger OAuth2 was opted in (Step 1 of `jwt.md`), apply the `AddSwaggerWithOAuth` / `UseSwaggerWithOAuth` replacements exactly as described in `jwt.md` Step 4 — those are style-independent.

**Do not** add `apiGroup.RequireAuthorization()` or any `MapGroup` wiring — there is no versioned API group in a Controllers project.

### `Startup.cs` (legacy hosting)

If `{HOSTING_STYLE}` is `Startup`:

- In `ConfigureServices(IServiceCollection services)`:
  ```csharp
  services.AddJwtBearerAuthentication(Configuration);
  // keep existing: services.AddControllers();
  ```

- In `Configure(IApplicationBuilder app, ...)`:
  ```csharp
  // existing security-headers middleware
  app.UseRouting();
  app.UseAuthentication();
  app.UseAuthorization();
  app.UseEndpoints(endpoints => endpoints.MapControllers());
  ```

---

## Protecting the API

There is no versioned `apiGroup` to call `.RequireAuthorization()` on. Add `[Authorize]` to the API controllers that must require a valid bearer token. Mark any intentionally public endpoints `[AllowAnonymous]`. Health-check endpoints mapped via `MapHealthChecks` remain anonymous as in the baseline.

If the user wants every controller protected by default, a global fallback authorization policy can be registered:

```csharp
builder.Services.AddAuthorizationBuilder()
    .SetFallbackPolicy(new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build());
```

---

## Verification

After integration, confirm:

- Authenticated requests with a valid Veracity bearer token in the `Authorization` header return the expected data.
- Unauthenticated requests to protected controller actions return `401`.
- `dotnet build` succeeds and the app starts. Middleware order: `UseAuthentication` **before** `UseAuthorization`, both **after** `UseRouting`.
