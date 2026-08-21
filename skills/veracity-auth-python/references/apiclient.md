# Veracity API Client — Python Reference

Use this file to call the **Veracity Platform API** (V3 and/or V4) from Python. It mirrors the
.NET `veracity-apiclient` skill: a typed client generated from the OpenAPI spec, plus an auth
layer that attaches a **Bearer token** (acquired on behalf of the signed-in user) and the
**`Ocp-Apim-Subscription-Key`** header. The auth layer and MSAL token providers are
framework-agnostic and live in `assets/veracity_core/apiclient.py` + `assets/veracity_core/obo.py`
(FastAPI re-exports them via `assets/app/veracity/client.py`), so the FastAPI, Flask, and Django
adapters all call the same client.

## Two parts

### 1. Typed client — analog of NSwag

Generate a typed, Pydantic-based httpx client from the Veracity OpenAPI spec using
**`openapi-python-client`**:

```bash
pip install openapi-python-client

# V4 — Veracity Platform API
openapi-python-client generate --url https://docs.veracity.com/api/transformer/apispecs/ApiV4Prod

# V3 — Veracity MyServices
openapi-python-client generate --url https://docs.veracity.com/api/transformer/apispecs/veracity-myservices-v3
```

If the live download fails, download the spec manually from the docs site and use
`--path <spec.json>`. Commit the generated package; regenerate when the spec changes (document
this in the project README, the same way the .NET skill does).

| Spec | Download URL | Base URL (Production) |
|------|--------------|-----------------------|
| **V4** | `https://docs.veracity.com/api/transformer/apispecs/ApiV4Prod` | `https://api.veracity.com/veracity/graph/v4` |
| **V3** | `https://docs.veracity.com/api/transformer/apispecs/veracity-myservices-v3` | `https://api.veracity.com/veracity/services/v3` |

For a small number of calls you can skip generation and use raw `httpx` against the base URL.

### 2. Auth layer — analog of the .NET delegating handler

`assets/app/veracity/client.py` provides `VeracityAuth(httpx.Auth)`, which on every request sets:

- `Authorization: Bearer <token>` — from a `TokenProvider` callable.
- `Ocp-Apim-Subscription-Key: <key>` — the API Management subscription key (a secret).

Wire it into the generated client's underlying httpx client, or into `make_v3_client` /
`make_v4_client` helpers.

## Acquiring the user access token

For an **OIDC BFF** app, the access token used to call the Veracity API is acquired **at login**:
`Settings.login_scopes` adds the Veracity API scope (`…/user_impersonation`) to the OIDC scopes, so
the authorization-code exchange returns a token already scoped for `api.veracity.com`. The BFF stores
that token in the session and the proxy uses it directly (see `assets/veracity_core/proxy.py`):

```python
from veracity_core.apiclient import make_v4_client
client = make_v4_client(settings, lambda: session_access_token)  # token from the session
resp = client.get("/my/profile")
```

- Scope (Production): `https://dnvglb2cprod.onmicrosoft.com/83054ebf-1d7b-43f5-82ad-b2bde84d7b75/user_impersonation`
- This mirrors Microsoft.Identity.Web in the .NET skill. **Do not** use MSAL on-behalf-of for the
  BFF: Azure AD B2C does not reliably support OBO, and with the API scope requested at login it is
  unnecessary. (An earlier revision used OBO and failed with *"No Veracity access token in session"*.)
- The app registration must be authorized for the Veracity API scope.

For a **JWT Bearer** API that needs to call the Veracity API as itself (not a user), use MSAL
client-credentials — `build_client_credentials_token_provider` in `assets/veracity_core/obo.py`
(`acquire_token_for_client`).

## BFF proxy endpoints

`assets/veracity_core/proxy.py` exposes the framework-agnostic helpers behind the versioned
proxy routes the **veracity-auth-ui** frontend calls (mirroring the .NET BFF's contract). Each
adapter (FastAPI `app/veracity/routes.py`, Flask `veracity_flask/veracity_api.py`, Django
`veracity_django/veracity_api.py`) wires them at:

| Endpoint | Core helper | Upstream | Notes |
|----------|-------------|----------|-------|
| `GET /api/v1/veracity/v3/services` | `get_my_services` | `GET /my/services` | User's services (V3) |
| `GET /api/v1/veracity/v3/policy/validate` | `validate_policy_v3` | `GET /my/policies/validate()` | Veracity-wide check (no service id); returns `{compliant, redirectUrl}`; HTTP `406` when a policy/subscription is outstanding (V3) |
| `GET /api/v1/veracity/v4/me/applications` | `get_my_applications` | `GET /me/applications` | User's applications (V4) |
| `GET /api/v1/veracity/v4/policy/validate` | `validate_policy_v4` | `POST /me/policy-verifications/{SERVICE_ID}` | Service-specific check; returns `{compliant, redirectUrl}`; HTTP `406` (or `403` carrying a redirect URL) when a policy/subscription is outstanding — a `403` without a redirect URL is relayed as `403` (V4) |

> Generate **only** the endpoints for the API version the user chose (V3 **or** V4). Both
> `policy/validate` variants validate the signed-in user's policies, but differ in scope: **V4** is
> service-specific and requires `SERVICE_ID`, while **V3** validates the user's Veracity-wide
> policies and needs no service id — so keep just the one matching the chosen version (alongside
> `v3/services` **or** `v4/me/applications`).

### Keep only your chosen version (V3 **or** V4)

The bundled asset code ships **both** versions so the reference test suite can exercise each
flow. A real project integrates exactly one version, so after choosing, **delete the other
version's code** everywhere it appears — do not leave the unused version in the generated project:

| Artifact | V3-only project keeps | V4-only project keeps |
|----------|-----------------------|-----------------------|
| `veracity_core/proxy.py` helpers | `get_my_services`, `validate_policy_v3` | `get_my_applications`, `validate_policy_v4` |
| `veracity_core/apiclient.py` client maker | `make_v3_client` | `make_v4_client` |
| `veracity_core/settings.py` base URL | `api_v3_base_url` | `api_v4_base_url` |
| Adapter routes (FastAPI `app/veracity/routes.py`, Flask/Django `veracity_api.py`) | `v3/services`, `v3/policy/validate` | `v4/me/applications`, `v4/policy/validate` |
| Tests (`tests/test_veracity_proxy.py`) | the V3 cases | the V4 cases |

Also update each adapter's imports from `veracity_core.proxy` / `veracity_core.apiclient` so they
no longer reference the deleted helpers. `SERVICE_ID` is required **only** by V4 `policy/validate`
(V3 policy validation is Veracity-wide and needs no service id), so a V3-only project omits it
entirely; a V4-only project keeps it unless it drops policy validation.

### Policy validation — `SERVICE_ID` (V4 only)

`validate_policy_v3` and `validate_policy_v4` both check the signed-in user's policies, but they
differ in scope:

- **V4** validates the user against the specific Veracity **service** this app is connected to
  (Veracity terms **and** that service's subscription/terms). The service id is read from
  configuration (`SERVICE_ID` → `Settings.service_id`), **not** the request, so a caller cannot
  validate an arbitrary application (mirrors the .NET `ServiceId`). The V4 helper calls
  `POST /me/policy-verifications/{SERVICE_ID}`. **`SERVICE_ID` is required for V4.**
- **V3** validates the user against **all** the Veracity policies that apply to them via
  `GET /my/policies/validate()` (return URL sent via the `returnUrl` header; success is `204`). It
  takes **no** service id, so V3-only projects do **not** need `SERVICE_ID` at all.

`SERVICE_ID` is **not** a secret. Add it to `.env` **only when using V4**:

```
# in .env (non-secret) — V4 policy validation only
SERVICE_ID=<your-service-id>
```

To make **V4** policy validation work, in the [Developer Portal](https://developer.veracity.com):
[create a service](https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/create-a-service)
and [connect this application to that service](https://docs.veracity.com/pages/developer-foundations/manage-your-projects/developer-portal/connect-an-application-to-a-service)
so it enables user subscription and policy checks. Reference (V3 Policy Service; the V4 endpoint
performs the service-specific equivalent):
https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/services-api/policy-service

## Subscription key (secret)

`Ocp-Apim-Subscription-Key` is **never** committed. Locally it lives in `.env` as
`SUBSCRIPTION_KEY` (gitignored); in deployed environments it comes from Azure Key Vault / pipeline
variables. Tell the user to set it themselves:

```
# in .env (local only)
SUBSCRIPTION_KEY=<your-ocp-apim-subscription-key>
```

Get the value from the [Veracity Developer Portal](https://developer.veracity.com) → your app
resource → **Settings**. See
https://docs.veracity.com/pages/developer-foundations/identity-and-authentication/authentication-for-apis

## Per-environment base URLs (override only when requested)

| Environment | V4 base | V3 base | Scope |
|-------------|---------|---------|-------|
| **Production** (default) | `https://api.veracity.com/veracity/graph/v4` | `https://api.veracity.com/veracity/services/v3` | `…/83054ebf-1d7b-43f5-82ad-b2bde84d7b75/user_impersonation` |
| **Test** | `https://api-test.veracity.com/veracity/graph/v4` | `https://api-test.veracity.com/veracity/services/v3` | `https://dnvglb2ctest.onmicrosoft.com/a4a8e726-c1cc-407c-83a0-4ce37f1ce130/user_impersonation` |
| **Staging** | `https://api-stag.veracity.com/veracity/graph/v4` | `https://api-stag.veracity.com/veracity/services/v3` | `https://dnvglb2cstag.onmicrosoft.com/28b7ec7b-db04-40bb-a042-b7ac5a8b36be/user_impersonation` |

## Verify

`assets/tests/test_oidc.py::test_veracity_auth_injects_headers` confirms an outgoing request
carries both `Authorization: Bearer …` and `Ocp-Apim-Subscription-Key`. After setting a real
subscription key and completing login, a call to `GET /my/profile` (V4) should return the user's
profile.
