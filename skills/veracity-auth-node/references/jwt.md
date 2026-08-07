# Veracity JWT Bearer — Full Reference

Use this file once the user has chosen **Veracity JWT Bearer** as their authentication
strategy. JWT Bearer is **stateless** — the API validates access tokens that callers already
hold. There is no client secret, no token acquisition, and no session on the server side.

This is the NodeJS equivalent of `AddJwtBearer` in the .NET `veracity-identity-backend` skill,
using [`jose`](https://github.com/panva/jose) for JWKS-based validation.

---

## Phase 3: CONFIGURE (collect values)

Ask the user:

1. **Audience (Client ID)** — the API's own app-registration Client ID (a GUID). This is the
   value Veracity B2C places in the `aud` claim of access tokens issued for this API. Stored as
   `JWT_AUDIENCE`.

   Present this before asking:

   > *"To secure your API with Veracity Identity, you need a **Veracity app registration** for
   > the API. This gives it a **Client ID** (a GUID that Veracity places in the `aud` claim of
   > access tokens so your API can validate them). If you haven't registered yet, see:*
   > - *Getting started: https://docs.veracity.com/pages/developer-foundations/introduction/getting-started-as-a-developer*
   > - *Authentication for APIs: https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/authentication-for-apis*
   > - *Create an application: https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-an-application*
   >
   > *Find the **Client ID** in the [Developer Portal](https://developer.veracity.com) under
   > your API app registration's **Settings** page (labelled "App / Api ID"). It is not a secret
   > and is safe to share here."*

   Then ask: **"What is your Veracity API app registration Client ID (Audience)?"**

No secrets are collected for JWT Bearer — the API only validates tokens; it never requests them.

---

## Phase 3: GENERATE

### Dependencies

```bash
npm install jose
```

### Files — shared core (always copy)

| Asset | Target |
|-------|--------|
| `assets/core/jwtVerifier.ts` | `src/auth/jwtVerifier.ts` |

`jwtVerifier.ts` is framework-agnostic. It exports `extractBearer(header)` and
`verifyBearerToken(token)`, resolving the Veracity B2C JWKS via `jose.createRemoteJWKSet`
(cached/rotated automatically).

### Files — Choose your framework (copy one adapter)

**Express** (middleware): `assets/express/jwt/jwtMiddleware.ts` → `src/auth/jwtMiddleware.ts`

**Fastify** (`preHandler` hook): `assets/fastify/jwt/jwtPlugin.ts` → `src/auth/jwtPlugin.ts`

**NestJS** (guard + module): `assets/nestjs/jwt/jwt-auth.guard.ts` → `src/auth/jwt-auth.guard.ts`
and `assets/nestjs/jwt/jwt.module.ts` → `src/auth/jwt.module.ts`

Replace `__PROJECT_NAME__` placeholder when copying. For a **CommonJS** NestJS project, drop the
`.js` extension from relative imports.

In every framework the adapter (`requireAuth` middleware/hook, or `JwtAuthGuard`):

- Reads the `Authorization: Bearer <token>` header (returns `401` if missing/malformed).
- Resolves the signing keys from the Veracity B2C JWKS endpoint via
  `jose.createRemoteJWKSet` (cached/rotated automatically).
- Verifies the token with `jose.jwtVerify`, validating **issuer**, **audience**, **lifetime**,
  and **signature**, with `clockTolerance: 60` seconds (matches the .NET 1-minute `ClockSkew`).
- On success attaches the decoded claims to `req.user`; on failure returns `401`.

Apply it to protected routes:

```ts
// Express:
import { requireAuth } from "./auth/jwtMiddleware.js";
app.use("/api", requireAuth, apiRouter); // health endpoints stay above this line

// Fastify (per-route or per-encapsulated-scope):
import { requireAuth } from "./auth/jwtPlugin.js";
fastify.get("/api/v1/thing", { preHandler: requireAuth }, handler);

// NestJS:
// import { JwtModule } into a feature module, then @UseGuards(JwtAuthGuard) on
// protected controllers/handlers. Health endpoints stay unguarded.
```

There is **no** session, login, logout, or `/api/me` BFF flow for JWT Bearer.

---

## Environment Variables (Production B2C by default)

### Extend the env schema (`src/config/env.ts`)

The baseline env module (from `web-backend-node`) only knows `NODE_ENV`/`PORT`/TLS. Add the JWT fields to the zod schema:

```ts
  // --- Veracity JWT Bearer ---
  JWT_AUTHORITY: z.string().url().optional(),
  JWT_AUDIENCE: z.string().optional(),
```

### `.env` values

Add to `.env` (all non-secret) — all environments default to **Production**:

```dotenv
# Veracity B2C (JWT Bearer)
JWT_AUTHORITY=https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0
JWT_AUDIENCE=<api-client-id>
```

The middleware derives the JWKS URI and issuer from `JWT_AUTHORITY`
(`${JWT_AUTHORITY}/.well-known/openid-configuration` → `jwks_uri` and `issuer`).

### Alternative B2C Authority URLs (use only when explicitly requested)

| Environment | JWT_AUTHORITY |
|-------------|---------------|
| **Test** | `https://logintest.veracity.com/dnvglb2ctest.onmicrosoft.com/B2C_1A_Identity/v2.0` |
| **Staging** | `https://loginstag.veracity.com/dnvglb2cstag.onmicrosoft.com/B2C_1A_Identity/v2.0` |

Replace `JWT_AUTHORITY` in that environment's `.env.<environment>` when targeting Test/Staging.

---

## Phase 4: VERIFY

- `npm run build` compiles.
- A protected endpoint without a token returns `401` (not a redirect).
- A protected endpoint with a valid Veracity token returns `200`.
- A token with the wrong `aud` returns `401` (audience validation).
- The health endpoints remain reachable without a token.

---

## Error Recovery

### Wrong B2C tenant / authority mismatch
**Symptom**: all requests `401` with issuer validation or metadata fetch errors.
**Recovery**: confirm `JWT_AUTHORITY` uses the correct Instance/Domain for the environment
(Production by default; Test/Staging table above). A common mistake is the production authority
in a non-production environment.

### Audience mismatch
**Symptom**: valid tokens return `401` with audience validation failure.
**Recovery**: confirm `JWT_AUDIENCE` matches the `aud` claim. Decode the token at
[jwt.ms](https://jwt.ms) and compare.

### Clock skew / token expired
**Symptom**: freshly issued tokens immediately `401` on lifetime.
**Recovery**: the middleware uses `clockTolerance: 60`. Sync the server clock if it drifts more
than a minute; adjust the tolerance in `jwtMiddleware.ts` only if callers issue very
short-lived tokens.

### JWKS fetch failure
**Symptom**: intermittent `401` or 5xx with network errors resolving keys.
**Recovery**: ensure the server can reach the B2C JWKS endpoint; `createRemoteJWKSet` caches
keys, so transient outages should not affect already-fetched keys.
