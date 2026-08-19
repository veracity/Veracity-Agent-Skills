# OpenID Connect (BFF) — Authentication Integration Reference

Use this file once the authentication strategy has been determined as **OpenID Connect**. By the time you read this, a baseline project already exists (either pre-existing — which may target .NET 8, 9, or 10 — or just created by the `web-backend-net` skill in Phase 2, which produces .NET 10). Your job here is to **integrate Veracity OpenID Connect authentication into that baseline project**.

OpenID Connect is for BFF (Backend-For-Frontend) web apps that manage user sessions with cookies. The server handles token acquisition and refresh — the browser only sees a session cookie.

> **Project style**: This file is written for **Minimal API** projects. If Phase 2.5 detected `{PROJECT_STYLE} = Controllers`, apply Steps 1, 2, 5, and 6 below unchanged (API version choice, packages, appsettings, credentials), but for **Step 3 (auth source files)** and **Step 4 (Program.cs wiring)** follow `references/controllers-oidc.md` instead — it specifies the controller asset files (`AuthController.cs`, `VeracityV3/V4Controller.cs`) and the `Program.cs`/`Startup.cs` middleware wiring for controllers.

Throughout this file, `{{ProjectName}}` is the **full** project name including the `.Web` suffix (e.g. base name `MyApp` → `{{ProjectName}}` = `MyApp.Web`), and the project lives at `src/{{ProjectName}}/`.

> **Target reference**: `assets/Program.cs` shows what `Program.cs` should look like **after** this integration is complete. Use it to verify your edits. Do not blindly overwrite an existing `Program.cs` with it — apply the edits below so baseline configuration is preserved.

---

## Step 1: Ask About Veracity API Version

Ask the user:

> Would you like to integrate with Veracity API **V3** or **V4**? (Default: V4)

Reference docs to help the user decide (share these if they are unsure):
- **V4** — [VTM API overview](https://docs.veracity.com/pages/developer-foundations/access-management/veracity-tenant-management-vtm/vtm-api/vtm-api-overview) and [API Explorer](https://docs.veracity.com/apis/platform/ApiV4Prod)
- **V3** — [MyServices V3 API Explorer](https://docs.veracity.com/apis/platform/veracity-myservices-v3)

The choice controls which package, registration, endpoints file, and appsettings key you add below. (The user may also choose **neither** — a BFF with login only, no Veracity API calls.)

---

## Step 2: Add NuGet Packages

Add these auth-specific packages to the existing `.csproj` (skip any already present):

- `Veracity.Common.OAuth.AspNetCore`
- `Azure.Identity`
- `Azure.Extensions.AspNetCore.DataProtection.Keys`
- `StackExchange.Redis`
- `Microsoft.AspNetCore.DataProtection.StackExchangeRedis`
- `Microsoft.Extensions.Caching.StackExchangeRedis`
- `Microsoft.Identity.Client` — **required as a direct reference only on .NET 10.** The Veracity OAuth packages ship native assets up to `net9.0`; on .NET 8 and .NET 9 the correct MSAL assembly is resolved from the native target and no direct reference is needed. On `net10.0` the packages fall back to the `net9.0` target, and the transitive MSAL assembly is not reliably copied to the output, causing a runtime `System.IO.FileNotFoundException: Could not load file or assembly 'Microsoft.Identity.Client'` during sign-in (in `OnAuthorizationCodeReceived`). **If the project targets `net10.0`**: add `dotnet add package Microsoft.Identity.Client` (no version pin) so NuGet selects a current version — it must be **at least** `4.66.2` and **not lower** than the version already pulled in transitively (e.g. `Azure.Identity`/`Azure.Core` may require `>= 4.83.1`), otherwise the build fails with `NU1605`. Skip this package on .NET 8/9.
- The Veracity API package matching the user's version choice: **V3** → `Veracity.Services.Api`; **V4** → `Veracity.Core.Api.V4`; **both** → both packages.

(The baseline versioning, validation, and OpenAPI packages are already present from `web-backend-net`.)

---

## Step 3: Add Auth Source Files

Copy these asset files into the project, replacing `{{ProjectName}}` placeholders:

- `assets/VeracityAuthExtensions.cs` → `Extensions/VeracityAuthExtensions.cs`. Replace:
  - `{{VeracityApiUsings}}` — add `using Veracity.Core.Api.V4;` for V4, or nothing extra for V3-only.
  - `{{VeracityApiRegistration}}` — add the appropriate registration call(s):
    - V4: `services.AddVeracityGraphApi<DotNetLogger>();`
    - V3: `services.AddVeracityServices(configuration.GetValue<string>("Veracity:MyServicesApi"));`
    - Both: include both lines.
- `assets/AuthEndpoints.cs` → `Endpoints/AuthEndpoints.cs`
- `assets/SafeRedirect.cs` → `Extensions/SafeRedirect.cs` (open-redirect guard used by the `/auth/challenge` `returnUrl` and the token-cache-recovery challenge)
- `assets/VeracityV3Endpoints.cs` → `Endpoints/VeracityV3Endpoints.cs` (only if V3 selected)
- `assets/VeracityV4Endpoints.cs` → `Endpoints/VeracityV4Endpoints.cs` (only if V4 selected)

> **Open-redirect guard (`SafeRedirect`, CWE-601)** — the `returnUrl` accepted by `/auth/challenge` is caller-supplied and must never become the `AuthenticationProperties.RedirectUri` without validation. `Uri.IsWellFormedUriString(returnUrl, UriKind.Relative)` is **not** sufficient: a protocol-relative value like `//evil.com` is a well-formed relative URI yet the browser follows it off-site. `SafeRedirect.SanitizeReturnUrl` mirrors ASP.NET Core's `Url.IsLocalUrl` and collapses any absolute, protocol-relative, or backslash-obfuscated value to `/`. The fixed `Veracity:LogoutRedirectUri` is not user input and is used as-is.

---

## Step 4: Weave Auth Into `Program.cs`

Edit the existing baseline `Program.cs` (do not replace it wholesale). Apply these changes:

1. **Usings** — add at the top:
   ```csharp
   using Veracity.Common.Authentication;
   ```

2. **Service registration** — immediately after the CSP configuration line
   (`builder.Services.Configure<CSPOptions>(builder.Configuration.GetSection("CSP"));`), add:
   ```csharp
   builder.Services.AddVeracityAuthentication(builder.Configuration, builder.Environment);
   ```

3. **Middleware pipeline** — around the existing `app.UseMiddleware<SecurityHeadersMiddleware>();` line:
   ```csharp
   app.UseVeracityTokenCacheRecovery();        // add immediately BEFORE security headers
   app.UseMiddleware<SecurityHeadersMiddleware>();
   app.UseAuthentication();                     // add the next three AFTER security headers
   app.UseVeracity();
   app.UseAuthorization();
   ```

4. **Auth endpoints** — before the versioned API group is created, add:
   ```csharp
   app.MapAuthEndpoints();
   ```

5. **Protect the versioned API group** — add `.RequireAuthorization()` to the `apiGroup`:
   ```csharp
   var apiGroup = api.MapGroup("/api/v{version:apiVersion}")
       .HasApiVersion(1.0)
       .RequireAuthorization();
   ```

6. **Map Veracity API endpoints** — where the baseline left a placeholder comment for versioned endpoints, add the call(s) matching the version choice:
   ```csharp
   apiGroup.MapV3Endpoints();   // if V3
   apiGroup.MapV4Endpoints();   // if V4
   ```

Compare the result against `assets/Program.cs` to confirm the final structure.

---

## Step 5: Merge Configuration

Merge the Veracity sections into the existing appsettings files (do not overwrite unrelated keys such as `Logging`, `AllowedHosts`, or `CSP`).

- **`appsettings.json`** — merge in the `Veracity` section from `assets/veracity.section.json`, then add the API version URL key to that `Veracity` section based on Step 1:
  - **V4**: add `"VeracityGraphBaseUrl": "https://api.veracity.com/veracity/graph/v4"`
  - **V3**: add `"MyServicesApi": "https://api.veracity.com/veracity/services/v3"`
  - **Both**: add both keys.
- **`appsettings.Development.json`** — merge in the `Veracity` section from `assets/veracity.development.json`. Replace the `{PORT}` placeholder in `RedirectUrl` using the following rule:
  - **If `REDIRECT_BASE_URL` was passed by the caller** (e.g. by `veracity-auth-ui`) — extract the port from that URL and use it. For example, `REDIRECT_BASE_URL = https://localhost:5173` → `RedirectUrl = https://localhost:5173/signin-oidc`. This ensures the OIDC redirect targets the frontend dev-server origin, which proxies `/signin-oidc` to the BFF.
  - **Otherwise (standalone use)** — use the project's own HTTPS port (default `54438`, from `launchSettings.json`) → `RedirectUrl = https://localhost:54438/signin-oidc`.
  - **Only if V4 is selected** — also add a top-level `"ServiceId": "<your-service-id>"` key (a sibling of the `Veracity` section, not inside it). The V4 policy-validation endpoint reads it via `configuration["ServiceId"]`. Do **not** add this key for V3-only integrations.

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

1. **Client ID** — The application (client) ID from the Veracity Developer Portal
2. **Service ID** *(only if V4 is selected and the V4 policy-validation endpoint is used)* — The ID
   of the Veracity **service** this application is connected to. The V4 `GET /api/v1/veracity/v4/policy/validate`
   endpoint validates the signed-in user against this service (Veracity terms **and** the service's
   subscription/terms). The Service ID is **not** a secret.

   To make policy validation work the user must, in the [Veracity Developer Portal](https://developer.veracity.com):
   - **Create a service** — https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-a-service
   - **Connect the application (the one whose Client ID is configured above) to that service** so the
     service can enable user subscriptions and policy checks —
     https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/connect-an-application-to-a-service

   > Background on what the policy check does (the doc shows the V3 Policy Service, but the V4 endpoint
   > performs the equivalent service-specific check):
   > https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/services-api/policy-service

**Do NOT ask the user for their Client Secret or Subscription Key in the chat.** Instead, guide them to store these securely using `dotnet user-secrets`.

Once the user provides their Client ID (and Service ID for V4), replace the `<your-client-id>`
placeholder in the `Veracity` section of `appsettings.Development.json` (merged from
`assets/veracity.development.json`) with the actual value. **Only for V4**, also add/replace the
top-level `ServiceId` key (a sibling of `Veracity`) with the user-provided Service ID:

```json
"ServiceId": "<user-provided-service-id>",   // V4 only — omit for V3-only integrations
"Veracity": {
  "ClientId": "<user-provided-client-id>"
}
```

> **Note**: ClientId and ServiceId are intentionally kept only in `appsettings.Development.json` for local development, not in the base `appsettings.json`. `ServiceId` is a top-level key (read via `configuration["ServiceId"]` by the V4 policy-validation endpoint) that is added **only when V4 is selected**, while `ClientId` lives in the `Veracity` section and is always present. In production they are supplied via environment variables (`Veracity__ClientId`, `ServiceId`) or Azure Key Vault — see `references/production-setup.md`. Neither is a secret, but keeping them out of the base file gives a single, per-environment source of truth (and matches the JWT strategy, which keeps `Jwt:Audience` in the Development file only).

Then guide the user to store their secrets locally:

```bash
cd src/{{ProjectName}}
dotnet user-secrets init
dotnet user-secrets set "Veracity:ClientSecret" "<your-client-secret>"
dotnet user-secrets set "Veracity:SubscriptionKey" "<your-subscription-key>"
```

> ⚠️ **Security note:** Never paste your Client Secret or Subscription Key into a chat window or commit them to source control. Always use `dotnet user-secrets` for local development or Azure Key Vault / environment variables for production.

Remind the user to run the `dotnet user-secrets set` commands themselves in their terminal with their actual values.

---

## Production Environment

For production deployment guidance (Redis, Azure Key Vault, credential storage), read `references/production-setup.md`.

---

## Error Recovery

### `FileNotFoundException` for `Microsoft.Identity.Client` during sign-in

If sign-in fails with `System.IO.FileNotFoundException: Could not load file or assembly 'Microsoft.Identity.Client, ...'` (in `OnAuthorizationCodeReceived`), the direct MSAL package reference was missed. Add it as described in Step 2, then rebuild:

```bash
cd src/{{ProjectName}}
dotnet add package Microsoft.Identity.Client
```
