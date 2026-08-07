# JWT Bearer — Authentication Integration Reference

Use this file once the authentication strategy has been determined as **JWT Bearer**. By the time you read this, a baseline project already exists (either pre-existing — which may target .NET 8, 9, or 10 — or just created by the `web-backend-net` skill in Phase 2, which produces .NET 10). Your job here is to **integrate JWT Bearer validation into that baseline project**.

JWT Bearer is for stateless APIs consumed by SPAs, mobile apps, or service-to-service calls where the caller already holds a bearer token. The API only validates tokens — there is no client secret, no token acquisition, and no session management on the server side.

> **Project style**: This file is written for **Minimal API** projects. If Phase 2.5 detected `{PROJECT_STYLE} = Controllers`, apply Steps 1, 2, 3, 5, and 6 below unchanged (packages, extension files, appsettings, credentials), but for **Step 4 (Program.cs wiring)** follow `references/controllers-jwt.md` instead — the JWT case adds no controller asset files; it only changes where auth middleware sits relative to `MapControllers` and uses `[Authorize]` on controllers instead of `.RequireAuthorization()` on an endpoint group.

Throughout this file, `{{ProjectName}}` is the **full** project name including the `.Api` suffix (e.g. base name `MyApp` → `{{ProjectName}}` = `MyApp.Api`), and the project lives at `src/{{ProjectName}}/`.

> **Target reference**: `assets/Program.jwt.cs` shows what `Program.cs` should look like **after** this integration. Use it to verify your edits; do not blindly overwrite an existing `Program.cs` — apply the edits below so baseline configuration is preserved.

---

## Step 1: Optional Feature — Swagger OAuth2

Ask the user:

> Should the Swagger UI **Authorize** dialog be configured so developers can obtain a token directly from Swagger and test protected endpoints? (Default: No)

This is the only optional feature for JWT Bearer. JWT projects do not integrate with Veracity V3/V4 APIs by default (the API validates tokens; it doesn't call Veracity APIs on behalf of the user).

---

## Step 2: Add NuGet Packages

Add this auth-specific package to the existing `.csproj` (skip if already present):

- `Microsoft.AspNetCore.Authentication.JwtBearer`

(The baseline versioning, validation, and OpenAPI packages are already present from `web-backend-net`.)

---

## Step 3: Add Auth Source Files

Copy these asset files into the project, replacing `{{ProjectName}}` placeholders:

- `assets/JwtAuthExtensions.cs` → `Extensions/JwtAuthExtensions.cs`
- `assets/SwaggerOAuthExtensions.cs` → `Extensions/SwaggerOAuthExtensions.cs` — **only if** Swagger OAuth2 was opted in during Step 1.

---

## Step 4: Weave Auth Into `Program.cs`

Edit the existing baseline `Program.cs` (do not replace it wholesale). Apply these changes:

1. **Usings** — add at the top:
   ```csharp
   using {{ProjectName}}.Extensions;
   ```

2. **Service registration** — immediately after the CSP configuration line
   (`builder.Services.Configure<CSPOptions>(builder.Configuration.GetSection("CSP"));`), add:
   ```csharp
   builder.Services.AddJwtBearerAuthentication(builder.Configuration);
   ```

3. **Middleware pipeline** — immediately after the existing `app.UseMiddleware<SecurityHeadersMiddleware>();` line, add:
   ```csharp
   app.UseAuthentication();
   app.UseAuthorization();
   ```

4. **Protect the versioned API group** — add `.RequireAuthorization()` to the `apiGroup`:
   ```csharp
   var apiGroup = api.MapGroup("/api/v{version:apiVersion}")
       .HasApiVersion(1.0)
       .RequireAuthorization();
   ```

5. **Swagger OAuth2 (only if opted in)** — replace the baseline Swagger wiring:
   - Replace the baseline `builder.Services.AddSwaggerGen(...)` registration block with:
     ```csharp
     builder.Services.AddSwaggerWithOAuth(builder.Configuration);
     ```
   - Replace the baseline Development Swagger middleware block
     (`app.UseSwagger(); app.UseSwaggerUI(...)` inside `if (app.Environment.IsDevelopment())`) with:
     ```csharp
     app.UseSwaggerWithOAuth();
     ```

Compare the result against `assets/Program.jwt.cs` to confirm the final structure.

> JWT Bearer is stateless — do **not** add `AuthEndpoints.cs`, cookie auth, OIDC, or Veracity V3/V4 endpoints.

---

## Step 5: Merge Configuration

Merge the following into `appsettings.Development.json` (the `Jwt` section belongs in Development only; production values come from environment variables or Azure Key Vault — never committed). Do not overwrite unrelated keys (`Logging`, `CSP`, etc.).

- Merge the `Jwt` section from `assets/jwt.development.json`.
- **If Swagger OAuth2 opted in**: also merge the `Swagger` section from `assets/swagger.development.json`. This is required because `SwaggerOAuthExtensions.cs` calls `configuration.GetRequiredSection("Swagger")`, which throws if missing.

Resulting `appsettings.Development.json` (with Swagger OAuth2):
```json
{
  "Jwt": {
    "Authority": "https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0",
    "Audience": "<api-client-id>"
  },
  "Swagger": {
    "Instance": "https://login.veracity.com",
    "Domain": "dnvglb2cprod.onmicrosoft.com",
    "SignUpSignInPolicyId": "B2C_1A_Identity",
    "ClientId": "<swagger-client-id>",
    "ScopeName": "user_impersonation"
  }
}
```

---

## Step 6: Veracity App Registration & Credentials

### If the user has NOT yet registered their application

Direct them to the Veracity developer documentation:

- **Getting started as a developer**: https://docs.veracity.com/pages/developer-foundations/introduction/getting-started-as-a-developer
- **Veracity Identity Provider (IDP)**: https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/veracity-identity-provider-idp
- **Create an application**: https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-an-application

Ask the user to complete their app registration and return with their credentials.

### Collect credentials

Ask the user to provide:

1. **Audience (Client ID)** — The API's own app registration Client ID (a GUID). This is the value that the Veracity B2C tenant places in the `aud` (audience) claim of access tokens issued for this API.

   > *"To secure your API with Veracity Identity, you need a **Veracity app registration** for the API. This gives your API a **Client ID** (a GUID that Veracity places in the `aud` claim of access tokens so your API can validate them).*
   >
   > *If you haven't registered your API yet, follow the steps above.*
   >
   > *Once your API is registered, you can find the **Client ID** in the [Veracity Developer Portal](https://developer.veracity.com) under your API app registration's **Settings** page (labelled "App / Api ID"). The Client ID is **not** a secret and is safe to share here."*

   Replace the `<your-api-client-id>` placeholder in `appsettings.Development.json`:
   ```json
   "Jwt": {
     "Authority": "https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0",
     "Audience": "<user-provided-client-id>"
   }
   ```

2. **Swagger OAuth2 Authorization** *(only if opted in during Step 1)* — Also collect:
   - **Swagger Client ID** — Client ID of a *separate* B2C app registration created specifically for the Swagger UI. Its reply URL must include `https://<host>/swagger/oauth2-redirect.html`.

   Then guide the user to store the Swagger client secret:
   ```bash
   cd src/{{ProjectName}}
   dotnet user-secrets init
   dotnet user-secrets set "Swagger:ClientSecret" "YOUR_SWAGGER_CLIENT_SECRET_HERE"
   ```

> **Note**: JWT Bearer authentication is stateless — there is no client secret, token acquisition, or session management on the server side. The API only validates tokens that callers already hold.

---

## Error Recovery

### Wrong B2C Tenant / Authority Mismatch

**Symptom**: All requests return 401 with "IDX10204: Unable to validate issuer" or metadata fetch failures at startup.

**Recovery**: Confirm the Authority URL in appsettings is the Veracity Production value `https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0`.

### Audience Mismatch

**Symptom**: Valid tokens return 401 with "IDX10214: Audience validation failed".

**Recovery**: Confirm the `Jwt:Audience` value matches the `aud` claim in the token. Decode the token at [jwt.ms](https://jwt.ms) and compare.

### Clock Skew / Token Expired

**Symptom**: Freshly issued tokens immediately return 401 with lifetime validation errors.

**Recovery**: The extension uses a 1-minute `ClockSkew`. If the server clock is drifting more than a minute, sync it.

### Swagger Authorize Dialog Not Pre-filled

**Symptom**: The Swagger UI **Authorize** dialog opens with empty ClientId / ClientSecret fields.

**Recovery**: Confirm `Swagger:ClientId` is present in the active appsettings file and `Swagger:ClientSecret` is set in user-secrets.

### Swagger OAuth2 Redirect Fails (Invalid Reply URL)

**Symptom**: After logging in via Swagger UI, the browser shows an "Invalid reply URL" error from B2C.

**Recovery**: Add `https://<host>/swagger/oauth2-redirect.html` to the Swagger app registration's allowed reply URLs.
