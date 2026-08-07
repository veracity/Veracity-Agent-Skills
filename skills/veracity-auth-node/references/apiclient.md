# Veracity API Client (V3/V4) — Full Reference

Use this file for **Phase 4: API CLIENT**. It generates a typed client for the Veracity
Platform API (V3 and/or V4) and exposes BFF proxy endpoints, mirroring the .NET
`veracity-apiclient` skill (which used NSwag + a delegating handler).

In NodeJS the typed client is produced from the OpenAPI spec with
[`openapi-typescript`](https://github.com/openapi-ts/openapi-typescript) (types) +
[`openapi-fetch`](https://github.com/openapi-ts/openapi-typescript/tree/main/packages/openapi-fetch)
(runtime). An `openapi-fetch` **middleware** attaches the Bearer token and subscription key —
the equivalent of `VeracityApiAuthHandler.cs`.

> **Prerequisite:** This depends on the **OIDC BFF** setup (`references/oidc.md`) because the
> proxy endpoints call the Veracity API **on behalf of the signed-in user**, using a token from
> MSAL `acquireTokenSilent`. For a stateless JWT API that must call the Veracity API
> service-to-service, see *Service-to-service* at the end.

---

## Phase 4a: DISCOVER

Ask the user: **which API version(s)** — V3, V4, or both? Default: **both**.

> `Ocp-Apim-Subscription-Key` is a secret — never ask for it in chat. It goes in `.env.local`
> (see Configure below).

---

## Phase 4b: GENERATE — download specs + generate types

Create `src/veracity/specs/` and download the latest specs (fall back to a manual download if
needed):

```bash
# V3 (if generating V3)
curl -sf -H "Accept: application/json" \
  "https://docs.veracity.com/api/transformer/apispecs/veracity-myservices-v3" \
  -o src/veracity/specs/ApiV3.json

# V4 (if generating V4)
curl -sf -H "Accept: application/json" \
  "https://docs.veracity.com/api/transformer/apispecs/ApiV4Prod" \
  -o src/veracity/specs/ApiV4.json
```

Install and run the type generator:

```bash
npm install -D openapi-typescript
npm install openapi-fetch

# V3
npx openapi-typescript src/veracity/specs/ApiV3.json -o src/veracity/generated/apiV3.d.ts
# V4
npx openapi-typescript src/veracity/specs/ApiV4.json -o src/veracity/generated/apiV4.d.ts
```

Add a regeneration script to `package.json`:

```json
{
  "scripts": {
    "veracity:gen": "openapi-typescript src/veracity/specs/ApiV3.json -o src/veracity/generated/apiV3.d.ts && openapi-typescript src/veracity/specs/ApiV4.json -o src/veracity/generated/apiV4.d.ts"
  }
}
```

Only include the V3 and/or V4 lines that match the user's choice.

---

## Phase 4c: SETUP — auth client + typed clients

### Shared core (always copy)

| Asset | Target |
|-------|--------|
| `assets/core/veracityApiClient.ts` | `src/veracity/veracityApiClient.ts` |

### Choose your framework (copy one adapter set)

**Express:**

| Asset | Target |
|-------|--------|
| `assets/express/apiclient/veracityApiMiddleware.ts` | `src/veracity/veracityApiMiddleware.ts` |
| `assets/express/apiclient/apiV3Routes.ts` | `src/veracity/apiV3Routes.ts` (only if V3 selected) |
| `assets/express/apiclient/apiV4Routes.ts` | `src/veracity/apiV4Routes.ts` (only if V4 selected) |

**Fastify:**

| Asset | Target |
|-------|--------|
| `assets/fastify/apiclient/veracityApiHelpers.ts` | `src/veracity/veracityApiHelpers.ts` |
| `assets/fastify/apiclient/apiV3Routes.ts` | `src/veracity/apiV3Routes.ts` (only if V3 selected) |
| `assets/fastify/apiclient/apiV4Routes.ts` | `src/veracity/apiV4Routes.ts` (only if V4 selected) |

**NestJS:**

| Asset | Target |
|-------|--------|
| `assets/nestjs/apiclient/veracity-api.service.ts` | `src/veracity/veracity-api.service.ts` |
| `assets/nestjs/apiclient/veracity-v3.controller.ts` | `src/veracity/veracity-v3.controller.ts` (only if V3 selected) |
| `assets/nestjs/apiclient/veracity-v4.controller.ts` | `src/veracity/veracity-v4.controller.ts` (only if V4 selected) |
| `assets/nestjs/apiclient/veracity.module.ts` | `src/veracity/veracity.module.ts` |

- **`veracityApiClient.ts`** (core) — exports `createVeracityClient(version, getAccessToken)`
  which builds an `openapi-fetch` client bound to the correct base URL and registers a
  middleware, plus the raw-fetch helpers `veracityApiFetch` / `parsePolicyRedirect` and
  `acquireUserApiToken(account)`. The per-framework adapter
  (`veracityApiMiddleware.ts` / `veracityApiHelpers.ts` / `veracity-api.service.ts`) adds
  `userApiToken(req)` that reads the signed-in user's MSAL account from the session. Together they add:
  - `Authorization: Bearer <token>` — token from MSAL `acquireTokenSilent` for the Veracity
    API scope (passed in via `getAccessToken`, sourced from the user's session).
  - `Ocp-Apim-Subscription-Key: <key>` — from `env.VERACITY_SUBSCRIPTION_KEY`.

  Import the generated `paths` types (`apiV3.d.ts` / `apiV4.d.ts`) to type the client. Remove
  the V3 or V4 branch if only one was requested.

- **`apiV3Routes.ts`** — the BFF proxy endpoints (require auth). Exposed under the **same
  versioned contract as the .NET BFF** so a `veracity-auth-ui` frontend and its capability
  detection work unchanged:

  | Endpoint | Upstream (V3) | Description |
  |----------|---------------|-------------|
  | `GET /api/v1/veracity/v3/services` | `/my/services` | Services the current user can access |
  | `GET /api/v1/veracity/v3/notifications/count` | `/my/messages/count` | Notification count for the current user |
  | `GET /api/v1/veracity/v3/policy/validate` | `/my/policies/validate()` | On `406` returns `{ compliant: false, redirectUrl }` |

- **`apiV4Routes.ts`** — the BFF proxy endpoints (require auth), mirroring `VeracityV4Endpoints.cs`:

  | Endpoint | Upstream (V4) | Description |
  |----------|---------------|-------------|
  | `GET /api/v1/veracity/v4/me/applications` | `/me/applications` | Applications licensed to the user |
  | `GET /api/v1/veracity/v4/me/tenants` | `/me/tenants` | Tenants the current user belongs to |
  | `GET /api/v1/veracity/v4/policy/validate` | `POST /me/policy-verifications/{VERACITY_SERVICE_ID}` | Service id read from config; on `406` returns `{ compliant: false, redirectUrl }` |
  | `GET /api/v1/veracity/v4/tenants/{tenantId}/applications` | `/tenants/{tenantId}/applications` | Applications for a tenant |

  All adapters use the shared `veracityApiFetch` + `parsePolicyRedirect` helpers plus a
  framework-specific `userApiToken` (the raw-fetch equivalent of the .NET delegating handler).

  > **Contract note:** the frontend (`veracity-auth-ui`) calls `GET /api/v1/veracity/v3/services`
  > and `GET /api/v1/veracity/v4/me/applications`, and detects BFF capability by grepping the
  > substrings `veracity/v3` / `veracity/v4`. These paths satisfy that contract, so this Node
  > BFF can serve a `veracity-auth-ui` frontend exactly as the .NET BFF does.

Wire the proxy endpoints after the auth setup (only the versions generated):

```ts
// Express (app.ts):
import { registerApiV3Routes } from "./veracity/apiV3Routes.js";
import { registerApiV4Routes } from "./veracity/apiV4Routes.js";
registerApiV3Routes(app);
registerApiV4Routes(app);

// Fastify (instance):
import { apiV3Routes } from "./veracity/apiV3Routes.js";
import { apiV4Routes } from "./veracity/apiV4Routes.js";
await fastify.register(apiV3Routes);
await fastify.register(apiV4Routes);

// NestJS: import { VeracityModule } into AppModule (after AuthModule). Include only the
// controllers for the version(s) you generated in veracity.module.ts.
```

---

## Phase 4d: CONFIGURE — env vars

### Extend the env schema (`src/config/env.ts`)

Add the API-client fields to the zod schema:

```ts
  // --- Veracity Platform API client ---
  VERACITY_API_V3_BASE_URL: z.string().url().optional(),
  VERACITY_API_V4_BASE_URL: z.string().url().optional(),
  VERACITY_API_SCOPE: z.string().optional(),
  VERACITY_SERVICE_ID: z.string().optional(), // ONLY for V4 policy/validate — omit for V3-only apps
  VERACITY_SUBSCRIPTION_KEY: z.string().optional(), // secret -> .env.local
```

### `.env` values

Add to `.env` (non-secret) — Production by default. Include only the versions requested:

```dotenv
# Veracity Platform API
VERACITY_API_V4_BASE_URL=https://api.veracity.com/veracity/graph/v4
VERACITY_API_V3_BASE_URL=https://api.veracity.com/veracity/services/v3
VERACITY_API_SCOPE=https://dnvglb2cprod.onmicrosoft.com/83054ebf-1d7b-43f5-82ad-b2bde84d7b75/user_impersonation
# Only needed for the V4 policy/validate endpoint — the Veracity service this app is connected to.
VERACITY_SERVICE_ID=<service-id>
```

> **`VERACITY_SERVICE_ID`** is the ID of the Veracity **service** this application is connected
> to. The `GET /api/v1/veracity/v4/policy/validate` endpoint validates the signed-in user against
> this service (Veracity terms **and** the service's subscription/terms). It is read from config,
> not the request, so a caller cannot validate an arbitrary application. It is **not** a secret.
> To make it work, in the [Developer Portal](https://developer.veracity.com):
> [create a service](https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-a-service)
> and [connect this application to that service](https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/connect-an-application-to-a-service)
> so it enables user subscription and policy checks. Background (the doc shows the V3 Policy
> Service, but the V4 endpoint performs the equivalent check):
> https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/services-api/policy-service

The subscription key is a **secret** — write it as a placeholder into the gitignored
`.env.local` scaffold (create/append the file) for the user to fill in themselves; do not ask for it in chat:

```text
VERACITY_SUBSCRIPTION_KEY=YOUR_SUBSCRIPTION_KEY_HERE
```

> Get the key from the [Developer Portal](https://developer.veracity.com) → your app resource →
> **Settings**. More on API auth & subscription keys:
> https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/authentication-for-apis

### Alternative API URLs / scopes (use only when explicitly requested)

| Environment | V4 base URL | V3 base URL | Scope |
|-------------|-------------|-------------|-------|
| **Test** | `https://api-test.veracity.com/veracity/graph/v4` | `https://api-test.veracity.com/veracity/services/v3` | `https://dnvglb2ctest.onmicrosoft.com/a4a8e726-c1cc-407c-83a0-4ce37f1ce130/user_impersonation` |
| **Staging** | `https://api-stag.veracity.com/veracity/graph/v4` | `https://api-stag.veracity.com/veracity/services/v3` | `https://dnvglb2cstag.onmicrosoft.com/28b7ec7b-db04-40bb-a042-b7ac5a8b36be/user_impersonation` |

---

## Phase 4e: VERIFY

- `npm run build` compiles (generated `.d.ts` types resolve).
- Sign in, then `GET /api/v1/veracity/v3/services` returns the user's services (if V3 generated).
- `GET /api/v1/veracity/v4/me/applications` returns the user's applications (if V4 generated).
- `GET /api/v1/veracity/v3/notifications/count` returns a count (V3).
- `GET /api/v1/veracity/v3/policy/validate` (or `.../v4/policy/validate`) returns
  `{ compliant: true }`, or `{ compliant: false, redirectUrl }` when the API responds `406`.

---

## Service-to-service (JWT Bearer projects)

If a stateless JWT API needs to call the Veracity API without a user, use the MSAL
**client-credentials** flow (`ConfidentialClientApplication.acquireTokenByClientCredential`)
with the API scope, instead of `acquireTokenSilent`. This requires a `CLIENT_SECRET` in
`.env.local` even for an otherwise stateless API. Otherwise the proxy endpoints above assume a
signed-in user (OIDC BFF).

---

## Regeneration note (for README)

Document that the typed client is generated from the OpenAPI specs and regenerated with
`npm run veracity:gen` after downloading updated specs. The generated `*.d.ts` files are
committed; do not edit them by hand.
