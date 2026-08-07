# Veracity JWT Bearer — Python / FastAPI Reference

Use this file when the chosen strategy is **JWT Bearer**. It mirrors the .NET
`AddJwtBearerAuthentication`: the API is **stateless** and validates access tokens that callers
already hold against the Veracity B2C tenant. Implemented in `assets/app/auth/jwt.py`.

There is no client secret, no token acquisition, and no session — the server only verifies tokens.

## How validation works

`assets/app/auth/jwt.py`:
- `PyJWKClient(settings.jwks_uri)` fetches the Veracity B2C signing keys from
  `{authority}/discovery/v2.0/keys` and selects the key matching the token's `kid`.
- `jwt.decode(...)` verifies **signature** (RS256), **audience** (`Jwt:Audience` = the API's own
  Client ID), **issuer**, and **expiry**, with `leeway=60` seconds (matching the .NET skill's
  1-minute clock skew; tighter than common defaults).
- `require_user` is a FastAPI dependency: a protected route declares
  `user: Principal = Depends(require_user)`. A missing or invalid token raises **401** with
  `WWW-Authenticate: Bearer` — never a redirect, correct for an API.

> The signing-key resolution is injectable (`set_key_resolver`) so unit tests validate the
> accept/reject logic with a locally generated RSA keypair, without calling B2C. Production leaves
> the resolver unset, so it uses the live B2C JWKS endpoint.

## Configuration values to collect

Ask the user for (non-secret, safe to share):

1. **Audience (Client ID)** — the API app registration's Client ID (a GUID). This is the value
   Veracity places in the token's `aud` claim. Goes in `.env` as `JWT_AUDIENCE`.

Explain before asking: *"To secure your API you need a Veracity app registration for the API,
which gives a **Client ID** (a GUID) that Veracity puts in the `aud` claim so your API can
validate tokens. Find it in the [Veracity Developer Portal](https://developer.veracity.com) under
your API app's Settings page ('App / Api ID'). It is not a secret."*

## Project structure

For a new JWT/stateless API scaffold, create the project under the resolved Python project slug with
an `-api` suffix:

```text
src/{project-slug}-api/
├── pyproject.toml
├── .env.example
├── .gitignore
├── app/
│   ├── main.py
│   ├── settings.py
│   ├── security_headers.py
│   ├── health.py
│   ├── dev_server.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── jwt.py
│   └── veracity/
│       ├── __init__.py
│       └── client.py
└── tests/
```

Set `pyproject.toml` `[project].name` to `{project-slug}-api`. Keep the import package as `app`
unless the user explicitly asks to rename it; if renamed, update imports, tests, scripts, and
`[tool.hatch.build.targets.wheel].packages` consistently. For a single-strategy JWT project,
delete `app/auth/oidc.py` and OIDC-only tests, or leave them unused only if the user wants to keep
the full reference test surface.

## Authority (Production by default)

```
Authority : https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0
JWKS      : {Authority}/discovery/v2.0/keys
Issuer    : https://login.veracity.com/a68572e3-63ce-4bc1-acdc-b64943502e9d/v2.0/
```

Only override for Test/Staging when explicitly requested:

| Environment | Authority | Issuer tenant GUID |
|-------------|-----------|--------------------|
| **Production** (default) | `https://login.veracity.com/dnvglb2cprod.onmicrosoft.com/B2C_1A_Identity/v2.0` | `a68572e3-63ce-4bc1-acdc-b64943502e9d` |
| **Test** | `https://logintest.veracity.com/dnvglb2ctest.onmicrosoft.com/B2C_1A_Identity/v2.0` | `ed815121-cdfa-4097-b524-e2b23cd36eb6` |
| **Staging** | `https://loginstag.veracity.com/dnvglb2cstag.onmicrosoft.com/B2C_1A_Identity/v2.0` | `307530a1-6e70-4ef7-8875-daa8f5a664ec` |

`Settings.jwt_authority`, `jwks_uri`, and `issuer` are derived from these; change the authority
and tenant GUID for a non-production environment.

## Optional: Swagger OAuth2 Authorize

By default, **No**. If the user wants the Swagger UI **Authorize** button to obtain a token and
test protected endpoints (the analog of the .NET `SwaggerExtensions.cs`), the cleanest Python
option is the **`fastapi-azure-auth`** package, which provides B2C bearer schemes with a built-in
Swagger OAuth2 (Authorization Code + PKCE) flow:

```python
from fastapi_azure_auth import B2CMultiTenantAuthorizationCodeBearer

azure_scheme = B2CMultiTenantAuthorizationCodeBearer(
    app_client_id=settings.jwt_audience,
    openid_config_url=f"{settings.jwt_authority}/.well-known/openid-configuration",
    openapi_authorization_url=f"{settings.jwt_authority}/oauth2/v2.0/authorize",
    openapi_token_url=f"{settings.jwt_authority}/oauth2/v2.0/token",
    scopes={settings.veracity_scope: "user_impersonation"},
    validate_iss=False,
)
```

Pass `swagger_ui_init_oauth={"clientId": settings.swagger_client_id, "usePkceWithAuthorizationCodeGrant": True}`
to `FastAPI(...)`. If you collect a **Swagger Client ID** (a *separate* B2C registration for the
Swagger UI), add `https://<host>/docs/oauth2-redirect` to its reply URLs. Any Swagger client
secret is a secret — set it via `.env`, never in chat. For most APIs the PyJWT validation in the
asset is sufficient and Swagger OAuth2 can be skipped.

## Program wiring

`assets/app/main.py` (JWT branch) mounts a versioned router with a protected sample endpoint:

```python
protected = APIRouter(prefix="/v1", tags=["protected"])

@protected.get("/me")
async def me(user: jwt_auth.Principal = Depends(jwt_auth.require_user)):
    return {"id": user.subject, "name": user.name}
```

Apply `Depends(require_user)` to every protected route (or use a router-level dependency
`APIRouter(dependencies=[Depends(require_user)])` for "secure by default").

## Local development

See `references/config-and-secrets.md` for the shared `veracity-dev` HTTPS setup. JWT validation
does not depend on HTTPS by itself, but this scaffold still runs HTTPS-first locally. When
applying the skill, generate the local cert/key pair and write the matching paths to `.env`. If you
enable Swagger OAuth2 Authorize, register `https://localhost:54438/docs/oauth2-redirect` (or your
chosen host/port) on the Swagger client app registration.

## Verify

- From `src/{project-slug}-api`, run `uv run pytest`.
- `GET /v1/me` without a token → **401**.
- `GET /v1/me` with a malformed/expired/wrong-audience/wrong-issuer token → **401**
  (covered by `assets/tests/test_jwt.py`).
- `GET /v1/me` with a valid Veracity token (correct `aud`/`iss`, unexpired) → **200**.
- `GET /docs` → Swagger renders; protected endpoints show the bearer requirement.

## Error recovery

- **All requests 401 with issuer/JWKS errors** — authority/issuer mismatch for the environment.
  Compare against the authority table above. Decode the token at https://jwt.ms and check `iss`.
- **Valid token still 401 (audience)** — `JWT_AUDIENCE` must equal the token's `aud` claim.
- **Freshly issued token immediately 401** — clock drift beyond the 60s `leeway`; sync the server
  clock or adjust `jwt_leeway_seconds`.
