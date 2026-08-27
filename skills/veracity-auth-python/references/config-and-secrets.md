# Configuration & Secrets — Python Reference

Configuration uses **pydantic-settings** (`assets/veracity_core/settings.py`, re-exported by
`assets/app/settings.py` for FastAPI) — the Python analog of the .NET `appsettings` + `IOptions`
pattern. The **same settings model and Veracity constants are shared** across the FastAPI, Flask,
and Django adapters (they all read `veracity_core`). Values are read from environment variables and
an optional `.env` file.

## Where values live

| Concern | Local development | Deployed environments |
|---------|-------------------|-----------------------|
| Non-secret config (Client ID, audience, env, base URLs) | `.env` or environment variables | environment variables / app config |
| **Secrets** (`CLIENT_SECRET`, `SESSION_SECRET`, `SUBSCRIPTION_KEY`, Swagger client secret) | `.env` — **gitignored** (the analog of `dotnet user-secrets`) | **Azure Key Vault** / pipeline variables |

`.env` is listed in `.gitignore`. **Never commit a real `.env`** and **never ask the user to
paste a secret value into the chat**. When applying this skill, generate local-only values such as
`SESSION_SECRET` by running a command that writes them **directly** into `.env` — never emit or
print the secret value yourself; only leave placeholders for secrets that must come from the
user or Key Vault.

## The settings model

`assets/app/settings.py` bakes in the **Production** Veracity B2C constants (authority, tenant
GUID, policy, API base URLs, default scope, logout URI) so a project works out of the box against
Production. Per-instance values come from the environment:

| Env var | Meaning | Secret? |
|---------|---------|---------|
| `APP_ENV` | `Development` / `Test` / `Stag` / `Prod` | no |
| `APP_HOST` | local bind host for the HTTPS dev server (`localhost` default) | no |
| `APP_PORT` | local HTTPS port for `veracity-dev` (`54438` default) | no |
| `HTTPS_CERT_FILE` | local HTTPS certificate path (`.certs/localhost.pem`) | no |
| `HTTPS_KEY_FILE` | local HTTPS private-key path (`.certs/localhost-key.pem`) | no |
| `AUTH_STRATEGY` | `oidc` or `jwt` | no |
| `CLIENT_ID` | Veracity app registration Client ID (OIDC) | no |
| `CLIENT_SECRET` | OIDC client secret | **yes** |
| `SESSION_SECRET` | Signs the session cookie (OIDC) | **yes** |
| `COOKIE_SECURE` | `true` (default); keep enabled for local HTTPS and deployed environments | no |
| `REDIRECT_URI` | Absolute OIDC callback URL registered with B2C (OIDC). Empty = derive from request (single origin). Set to the veracity-auth-ui Vite proxy origin (`https://localhost:5173/auth/callback`) when a SPA fronts the BFF. | no |
| `OIDC_HTTP_TIMEOUT` | Seconds Authlib waits when fetching B2C discovery metadata / tokens (default `30`). Raised above httpx's 5s default so a slow network or corporate/VPN proxy TLS handshake doesn't 500 the login with a `ConnectTimeout`. | no |
| `JWT_AUDIENCE` | API app registration Client ID (JWT) | no |
| `SERVICE_ID` | Veracity service this app is connected to; used **only** by the V4 `policy/validate` endpoint (V3 policy validation is Veracity-wide and needs no service id). Not a secret. | no |
| `SUBSCRIPTION_KEY` | `Ocp-Apim-Subscription-Key` for the Veracity API | **yes** |

## Local HTTPS setup

The scaffold's `veracity-dev` launcher is shared by **both** auth strategies and starts Uvicorn
with `HTTPS_CERT_FILE` / `HTTPS_KEY_FILE`.

- **OIDC:** HTTPS is required locally because the BFF uses a secure session cookie
  (`__Host-session`) and the callback URL should match the app registration exactly.
- **JWT:** token validation itself does **not** require HTTPS, but the scaffold still defaults to
  HTTPS for consistent local browser testing and for the optional Swagger OAuth2 authorize flow.

When applying this skill:

1. Work from the resolved project directory (`src/{project-slug}-web` for OIDC or
   `src/{project-slug}-api` for JWT).
2. Copy `.env.example` to `.env`.
3. For OIDC projects, generate a strong `SESSION_SECRET` by running a command that writes it
   **directly** into `.env` so the value never appears in your output (it replaces the
   `.env.example` placeholder line): `python -c "import secrets,re,pathlib; p=pathlib.Path('.env'); p.write_text(re.sub(r'(?m)^SESSION_SECRET=.*$', 'SESSION_SECRET='+secrets.token_urlsafe(32), p.read_text()))"`. Never echo or print the generated value.
4. The local cert/key pair is generated **automatically**: the `veracity-dev` launcher calls
   `scripts/generate_dev_cert.py` on startup when the files at `HTTPS_CERT_FILE` / `HTTPS_KEY_FILE`
   are missing (default: `.certs/localhost.pem` and `.certs/localhost-key.pem`). You can also run it
   ahead of time with `uv run veracity-dev-cert`. No manual `mkcert` step or `.env` editing is
   required — the paths already match `.env.example`.
5. The generator prefers `mkcert` when it is on `PATH` because it produces a certificate trusted by
   the OS/browser. When `mkcert` is unavailable it falls back to a self-signed localhost
   certificate/key pair generated with the `cryptography` library (already a dependency), so local
   HTTPS works with no extra tooling to install.

```bash
cd src/{project-slug}-{web|api}
Copy-Item .env.example .env     # Windows PowerShell (or: cp .env.example .env)
# For OIDC, generate SESSION_SECRET with a command that writes it directly into .env (never print it):
#   python -c "import secrets,re,pathlib; p=pathlib.Path('.env'); p.write_text(re.sub(r'(?m)^SESSION_SECRET=.*$', 'SESSION_SECRET='+secrets.token_urlsafe(32), p.read_text()))"
# then edit .env: set CLIENT_ID / JWT_AUDIENCE and any
# remaining user-managed secret values. The localhost cert/key is created automatically.
uv run veracity-dev            # generates .certs/localhost*.pem on first run, then serves HTTPS
```

Default local URL: `https://localhost:54438`.

## Deployed: Azure Key Vault

Mirror the .NET skill's Key Vault posture. Read secrets at startup with
`azure-identity` + `azure-keyvault-secrets`:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

client = SecretClient(vault_url=f"https://{vault_name}.vault.azure.net", credential=DefaultAzureCredential())
client_secret = client.get_secret("ClientSecret").value
```

Or inject secrets as environment variables via Key Vault references in the hosting platform (App
Service / Container Apps), so `pydantic-settings` picks them up with no code change. Grant the
app's managed identity the **Key Vault Secrets User** role.

## Per-environment overrides

All environments default to **Production** B2C. To target Test/Staging for a specific
environment, override the authority/tenant (JWT) or Instance/Domain/TenantId (OIDC) — value tables
are in `references/jwt.md` and `references/oidc.md`. Drive selection off `APP_ENV` if you need
different values per environment.

## Verify secrets are set (without printing values)

```bash
cd src/{project-slug}-{web|api}
python -c "from app.settings import get_settings as g; s=g(); print({'client_id_set': bool(s.client_id), 'client_secret_set': bool(s.client_secret), 'subscription_key_set': bool(s.subscription_key)})"
```

This prints booleans only — never the secret values.
