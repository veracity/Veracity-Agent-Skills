# Veracity OpenID Connect (BFF) — Full Reference

Use this file once the user has chosen **Veracity OpenID Connect** as their authentication
strategy. This implements the **Backend-for-Frontend (BFF)** pattern: the NodeJS server holds
a confidential client (`@azure/msal-node`), runs the authorization-code + PKCE flow, stores
tokens server-side in a session, and exposes login/logout/me endpoints. The browser only ever
holds an opaque, `__Host-`-prefixed session cookie.

This is the NodeJS equivalent of `Microsoft.Identity.Web`'s `AddMicrosoftIdentityWebApp` +
cookie session in the .NET `veracity-identity-backend` skill.

---

## Phase 3: CONFIGURE (collect values)

Collect only **non-secret** values in chat.

1. **Client ID** — a GUID identifying the application in the Veracity **Production** B2C
   tenant. Stored as `CLIENT_ID` in the env files.

   Present this before asking:

   > *"To connect your application to Veracity Identity, you need a **Veracity app
   > registration**. This gives your app a **Client ID** (a GUID that identifies it in the
   > Veracity B2C tenant) and a **Client Secret** (a credential used to request tokens). If you
   > haven't registered yet, see:*
   > - *Getting started: https://docs.veracity.com/pages/developer-foundations/introduction/getting-started-as-a-developer*
   > - *How Veracity Identity works: https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/veracity-identity-provider-idp*
   > - *Create an application: https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-an-application*
   >
   > *Find the **Client ID** in the [Developer Portal](https://developer.veracity.com) under
   > your app registration's **Settings** page (labelled "App / Api ID"). The Client ID is not a
   > secret and is safe to share here."*

   Then ask: **"What is your Veracity app registration Client ID?"**

2. **Redirect URI** — the BFF callback. Stored as `REDIRECT_URI`. Choose it by scenario:
   - **Invoked by a frontend workflow with `REDIRECT_BASE_URL`** (e.g. `veracity-auth-ui`
     passing `https://localhost:5173`) → use `{REDIRECT_BASE_URL}/auth/callback`. This makes
     the OIDC callback land on the **frontend** dev-server origin (which proxies `/auth/*` to
     this BFF), so the session cookie is established on the origin the browser actually uses.
   - **Standalone BFF** → default `https://localhost:<port>/auth/callback` (or `http://` for
     plain local dev without TLS; the `__Host-` cookie then requires the HTTPS note below).

   The chosen path must be registered as a reply URL in the Veracity app registration.

> **Client Secret (secret — never ask in chat).** Write it as a placeholder into the
> gitignored `.env.local` scaffold (create the file if it does not exist) for the user to fill in:
>
> ```text
> CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
> ```
>
> They create/view client secrets in the Developer Portal under the app registration's
> **Settings** page (shown only once at creation).
>
> **Session secret — generate it via a command that writes it, do not ask the user and do not
> write the value yourself.** Unlike `CLIENT_SECRET`, `SESSION_SECRET` has no external source: it
> is an app-internal signing key. **Run a command that generates a strong 32-byte random value and
> appends it directly to `.env.local`**, so the secret never appears in your output (do not leave a
> placeholder, do not ask the user to run a command, and do not echo/print the value). Use Node's
> crypto (always available in a Node project, cross-platform including Windows):
>
> ```bash
> node -e "const fs=require('fs');fs.appendFileSync('.env.local','SESSION_SECRET='+require('crypto').randomBytes(32).toString('base64')+'\n')"
> ```
>
> The command writes the `SESSION_SECRET=<value>` line for you; there is nothing to copy or paste.

**Optional — Redis session store** (only if the user explicitly requests multi-instance /
Data Protection parity). Then the Redis connection string is also a secret in `.env.local`:

```text
REDIS_URL=rediss://:YOUR_REDIS_ACCESS_KEY@YOUR_REDIS_HOST:6380
```

---

## Phase 3: GENERATE

### Dependencies

Always add the MSAL client (framework-agnostic):

```bash
npm install @azure/msal-node
```

Then add the **session** packages for your framework:

```bash
# Express OR NestJS (both run on the Express platform by default):
npm install express-session
npm install -D @types/express-session

# Fastify:
npm install @fastify/session @fastify/cookie

# Optional Redis session store (Express/NestJS): connect-redis + ioredis
#   Fastify multi-instance store: use a @fastify/session-compatible store (e.g. connect-redis via @mgcrea/fastify-session, or a custom store)
npm install connect-redis ioredis
```

### Files — shared core (always copy)

| Asset | Target |
|-------|--------|
| `assets/core/msalClient.ts` | `src/auth/msalClient.ts` |
| `assets/core/claims.ts` | `src/auth/claims.ts` |

- **`msalClient.ts`** — builds a `ConfidentialClientApplication` against the Veracity B2C
  authority, exposes `getAuthCodeUrl`, `acquireTokenByCode`, and `acquireTokenSilent` (for the
  downstream Veracity API). Mirrors MSAL token acquisition in .NET.
- **`claims.ts`** — the `SessionUser` shape + `mapClaims` used to project B2C ID-token claims.

### Files — Choose your framework (copy one adapter set)

**Express** (`app.get`/`app.use` middleware & routes):

| Asset | Target |
|-------|--------|
| `assets/express/oidc/authMiddleware.ts` | `src/auth/authMiddleware.ts` |
| `assets/express/oidc/authRoutes.ts` | `src/auth/authRoutes.ts` |

**Fastify** (plugins + `preHandler` hook; session on `request.session`):

| Asset | Target |
|-------|--------|
| `assets/fastify/oidc/authPlugin.ts` | `src/auth/authPlugin.ts` |
| `assets/fastify/oidc/authRoutes.ts` | `src/auth/authRoutes.ts` |

**NestJS** (DI service + guard + controller + module):

| Asset | Target |
|-------|--------|
| `assets/nestjs/oidc/session.types.ts` | `src/auth/session.types.ts` |
| `assets/nestjs/oidc/msal.service.ts` | `src/auth/msal.service.ts` |
| `assets/nestjs/oidc/session-auth.guard.ts` | `src/auth/session-auth.guard.ts` |
| `assets/nestjs/oidc/auth.controller.ts` | `src/auth/auth.controller.ts` |
| `assets/nestjs/oidc/auth.module.ts` | `src/auth/auth.module.ts` |

Replace `__PROJECT_NAME__` / `__PROJECT_SLUG__` placeholders when copying. For a **CommonJS**
NestJS project, drop the `.js` extension from relative imports in the copied files.

- **Guard/middleware** (`authMiddleware.ts` / `authPlugin.ts` / `session-auth.guard.ts`) — if
  no authenticated session, requests to `/api/*` return `401` (machine-readable). The Express and
  Fastify adapters additionally redirect non-`/api` paths to `/auth/challenge` (mirrors the .NET
  `OnRedirectToIdentityProvider` `/api` 401 behavior); the NestJS `SessionAuthGuard` returns a
  clean `401` and relies on the SPA to navigate to `/auth/challenge` (see the frontend contract
  note below).
- **Auth routes/controller** (`authRoutes.ts` / `auth.controller.ts`) — the BFF endpoints (table below).

### Session cookie (`__Host-` prefix)

> **Never hard-code a fallback secret.** Wire the session `secret` as `env.SESSION_SECRET`
> **directly** — never write `env.SESSION_SECRET ?? "…"` or any literal default string. A
> hard-coded fallback (e.g. `"change-me-in-env-local-32-chars-min"`) is flagged by Veracode as a
> hard-coded credential and silently defeats fail-fast validation. Because `SESSION_SECRET` is a
> **required** `z.string().min(32)` field in the env schema, `env.SESSION_SECRET` is already typed
> `string` (never `undefined`), so no fallback is needed and the app refuses to boot if it is
> missing or too short.

**Express / NestJS** — `express-session` is configured in `app.ts` (Express) or `main.ts`
(NestJS, on the underlying Express instance) with:

```ts
app.set("trust proxy", 1);
app.use(
  session({
    name: "__Host-veracity.session",
    secret: env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    // store: new RedisStore({ client }),  // only when Redis requested
    cookie: {
      secure: true,        // required for __Host- prefix
      httpOnly: true,
      sameSite: "lax",
      path: "/",           // required for __Host- prefix
      maxAge: 8 * 60 * 60 * 1000,
    },
  }),
);
```

**Fastify** — register `@fastify/cookie` then `@fastify/session` on the instance with the same
cookie rules (set `fastify.get`... after this):

```ts
await fastify.register(cookie);
await fastify.register(fastifySession, {
  secret: env.SESSION_SECRET,        // >= 32 chars
  cookieName: "__Host-veracity.session",
  // store: new RedisStore(...),      // only when Redis requested
  cookie: {
    secure: true,        // required for __Host- prefix
    httpOnly: true,
    sameSite: "lax",
    path: "/",           // required for __Host- prefix
    maxAge: 8 * 60 * 60 * 1000,
  },
});
```

> Set `trustProxy: true` in the Fastify factory (`Fastify({ trustProxy: true })`) so
> `X-Forwarded-Proto` is honoured — the Fastify equivalent of `app.set("trust proxy", 1)`.

> The `__Host-` prefix requires `Secure`, `Path=/`, and **no** `Domain`. Over plain HTTP on
> localhost browsers reject `Secure` cookies; document that local dev should use HTTPS (e.g. a
> dev TLS proxy) or temporarily drop the `__Host-` prefix for localhost only.

> **Running the BFF on HTTP behind a frontend HTTPS dev proxy (e.g. Vite).** This is the common
> setup when a `veracity-auth-ui` frontend proxies to this Node BFF. The browser→proxy hop is
> HTTPS but the proxy→BFF hop is plain HTTP, so `req.secure` is `false` and **express-session
> refuses to set the `Secure __Host-` cookie** — the OIDC callback then finds an empty session
> (`authState` missing) and fails with **400**. To fix, both sides must cooperate:
>
> 1. **BFF**: call `app.set("trust proxy", 1)` (already in the template) so Express honours
>    `X-Forwarded-Proto`.
> 2. **Proxy**: forward the header. In `vite.config.ts` set `xfwd: true` on every proxied
>    route (`/api`, `/auth`, `/signout`, `/signin-oidc`). Vite does **not** send
>    `X-Forwarded-*` by default, so without this the BFF never sees the request as HTTPS.
>
> Alternatively, run the BFF itself over HTTPS (TLS cert) so the whole chain is HTTPS — then
> `xfwd` is unnecessary. When the frontend proxies to a `.NET` BFF (Kestrel HTTPS) this is
> already the case, which is why the default `veracity-auth-ui` vite config does not set `xfwd`.

### BFF Endpoints (match the .NET `AuthEndpoints.cs`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth` | GET | Anonymous | Sign-in status → `{ result: boolean }` |
| `/api/me` | GET | Required | Current user `{ id, displayName, email, firstName, lastName }` |
| `/auth/challenge` | GET | Anonymous | Starts OIDC login; accepts optional `?returnUrl=` |
| `/auth/callback` | GET | Anonymous | Redirect URI; exchanges code, establishes session |
| `/signOut` | GET | Anonymous | Clears session and redirects to the Veracity logout page |

> **Sign-out redirect (`LOGOUT_REDIRECT_URI`)** — `/signOut` reads the post-logout URL from
> `LOGOUT_REDIRECT_URI`, falling back to `https://www.veracity.com/auth/logout`.

> **Open-redirect guard (`safeReturnUrl`, CWE-601)** — the `returnUrl` accepted by
> `/auth/challenge` is caller-supplied, so it must never be stored or redirected to without
> validation. `safeRedirect.ts` exports `safeReturnUrl`, which returns a guaranteed
> root-relative path and collapses any absolute, protocol-relative (`//host`),
> backslash-obfuscated, or scheme-bearing value to `/`. Apply it when storing the value in
> `/auth/challenge`, when consuming it in `/auth/callback` (defense-in-depth), and when the
> `requireAuth` guard builds `/auth/challenge?returnUrl=`. The fixed `LOGOUT_REDIRECT_URI` is
> not user input and is used as-is.

> **Frontend contract — sign-in must target `/auth/challenge`, not `/auth`.** A common wiring
> mistake is pointing the "Sign in" button at `/auth`. `GET /auth` is only a **status check**
> that returns `{ result: boolean }` and never redirects — clicking it just shows
> `{"result":false}`. The button (or `signIn()` helper) must do a full-page navigation to
> `/auth/challenge?returnUrl=<relative-url>`, which is the endpoint that redirects to the
> Veracity B2C login page. Use a full navigation (`window.location.href = ...`), not `fetch()`,
> because the 302 goes cross-origin into B2C and would fail CORS. The `veracity-auth-ui`
> frontend already does this correctly (`src/api/auth.ts` `signIn()`); keep any custom frontend
> consistent with it.

### Program wiring

**Express** (`app.ts`):

```ts
import session from "express-session";
import { registerAuthRoutes } from "./auth/authRoutes.js";

// after helmet + json, before protected routers:
app.use(session({ /* see above */ }));
registerAuthRoutes(app);
// protected feature routers mounted after this point use requireAuth
```

**Fastify** (instance bootstrap):

```ts
import cookie from "@fastify/cookie";
import fastifySession from "@fastify/session";
import { authRoutes } from "./auth/authRoutes.js";

// after @fastify/helmet + health routes:
await fastify.register(cookie);
await fastify.register(fastifySession, { /* see above */ });
await fastify.register(authRoutes);
// protected route plugins apply { preHandler: requireAuth }
```

**NestJS** (`main.ts` + `AppModule`):

```ts
// main.ts — before app.listen():
import session from "express-session";
import helmet from "helmet";

app.use(helmet());
app.set("trust proxy", 1);
app.use(session({ /* see above */ }));

// app.module.ts:
// @Module({ imports: [AuthModule /*, VeracityModule */] })
// Protect feature controllers/handlers with @UseGuards(SessionAuthGuard).
```

> **NestJS route prefix**: `/auth`, `/auth/callback` and `/signOut` must stay at the origin
> root. If the app uses `app.setGlobalPrefix("api")`, exclude those paths (`setGlobalPrefix("api",
> { exclude: ["auth", "auth/callback", "auth/challenge", "signOut"] })`) so the OIDC redirect URI
> and logout resolve correctly.

---

## Environment Variables (Production B2C by default)

### Extend the env schema (`src/config/env.ts`)

The baseline env module (from `web-backend-node`) only knows `NODE_ENV`/`PORT`/TLS. Add the OIDC fields to the zod schema:

```ts
  // --- Veracity OIDC ---
  B2C_INSTANCE: z.string().url().optional(),
  B2C_DOMAIN: z.string().optional(),
  B2C_POLICY: z.string().optional(),
  B2C_TENANT_ID: z.string().optional(),
  CLIENT_ID: z.string().optional(),
  CLIENT_SECRET: z.string().optional(), // secret -> .env.local
  REDIRECT_URI: z.string().url().optional(),
  SCOPES: z.string().default("openid profile email offline_access"),
  LOGOUT_REDIRECT_URI: z.string().url().default("https://www.veracity.com/auth/logout"),
  SESSION_SECRET: z.string().min(32, "SESSION_SECRET must be at least 32 characters"), // secret -> .env.local (REQUIRED; app fails fast if missing/weak)
  REDIS_URL: z.string().optional(), // optional secret -> only for multi-instance
```

And export the authority helper alongside `env`:

```ts
// Helper: full B2C authority for OIDC.
export function b2cAuthority(): string {
  return `${env.B2C_INSTANCE}/${env.B2C_DOMAIN}/${env.B2C_POLICY}/v2.0`;
}
```

### `.env` values

Add to `.env` (non-secret) — all environments default to **Production**:

```dotenv
# Veracity B2C (OIDC)
B2C_INSTANCE=https://login.veracity.com
B2C_DOMAIN=dnvglb2cprod.onmicrosoft.com
B2C_POLICY=B2C_1A_Identity
B2C_TENANT_ID=a68572e3-63ce-4bc1-acdc-b64943502e9d
CLIENT_ID=<client-id>
REDIRECT_URI=http://localhost:54438/auth/callback
SCOPES=openid profile email offline_access
LOGOUT_REDIRECT_URI=https://www.veracity.com/auth/logout
```

The authority is constructed as `${B2C_INSTANCE}/${B2C_DOMAIN}/${B2C_POLICY}/v2.0`.

Secrets go in `.env.local` only. `CLIENT_SECRET` and (optional) `REDIS_URL` are **placeholders the user fills in** (external sources). `SESSION_SECRET` is **generated by a command that writes it directly into `.env.local`** (`node -e "const fs=require('fs');fs.appendFileSync('.env.local','SESSION_SECRET='+require('crypto').randomBytes(32).toString('base64')+'\n')"`) so the value never appears in the agent's output. Generate the gitignored `.env.local` scaffold so the user only fills in the placeholder values — do not leave them to create the file themselves.

### Alternative B2C Tenant Values (use only when explicitly requested)

| Environment | B2C_INSTANCE | B2C_DOMAIN | B2C_TENANT_ID | LOGOUT_REDIRECT_URI |
|-------------|--------------|------------|---------------|---------------------|
| **Test** | `https://logintest.veracity.com` | `dnvglb2ctest.onmicrosoft.com` | `ed815121-cdfa-4097-b524-e2b23cd36eb6` | `https://wwwtest.veracity.com/auth/logout` |
| **Staging** | `https://loginstag.veracity.com` | `dnvglb2cstag.onmicrosoft.com` | `307530a1-6e70-4ef7-8875-daa8f5a664ec` | `https://wwwstag.veracity.com/auth/logout` |

Replace the four values in that environment's `.env.<environment>` when targeting Test/Staging.

---

## Phase 4: VERIFY

- `npm run build` compiles.
- Start the app; `GET /auth` returns `{ "result": false }` when signed out.
- `GET /auth/challenge` redirects to the Veracity B2C login page.
- After login, `GET /api/me` returns the user object; `GET /auth` returns `{ "result": true }`.
- `GET /signOut` clears the session and redirects to the Veracity logout page.
- An unauthenticated `GET /api/me` returns `401` (not a redirect).

---

## Error Recovery

### `__Host-` cookie rejected on localhost
**Symptom**: session never persists in local dev over HTTP.
**Recovery**: serve local dev over HTTPS, or drop the `__Host-` prefix and `secure:true` for
localhost only (keep them for all deployed environments).

### OIDC callback returns 400 (state mismatch) behind a frontend HTTPS proxy
**Symptom**: after login, `/auth/callback` responds `400 invalid_auth_response`; the session is
empty on the callback even though `/auth/challenge` ran. Happens when the BFF runs on plain HTTP
behind a Vite (or similar) HTTPS dev proxy.
**Cause**: the proxy→BFF hop is HTTP, so `req.secure` is `false` and express-session never issued
the `Secure __Host-` cookie during `/auth/challenge`; the callback therefore has no `authState`.
**Recovery**: set `xfwd: true` on every proxied route in `vite.config.ts` (so `X-Forwarded-Proto`
reaches the BFF) and keep `app.set("trust proxy", 1)` on the BFF — or run the BFF over HTTPS. See
the "Running the BFF on HTTP behind a frontend HTTPS dev proxy" note in the cookie section above.

### Client Secret missing at runtime
**Symptom**: token exchange fails with an MSAL "invalid_client" / missing credential error.
**Recovery**: confirm `CLIENT_SECRET` is present in `.env.local` (local) or the environment /
Key Vault (deployed). Never commit it.

### Wrong B2C tenant for environment
**Symptom**: authority metadata fetch fails or login errors at startup.
**Recovery**: verify `B2C_INSTANCE`, `B2C_DOMAIN`, and `B2C_TENANT_ID` match the intended
environment (Production by default; Test/Staging table above).

### Session not shared across instances
**Symptom**: user appears signed in on one instance but unauthenticated on another.
**Recovery**: enable the Redis session store (`connect-redis` + `ioredis`) so all instances
share session state — the equivalent of Redis Data Protection in .NET.
