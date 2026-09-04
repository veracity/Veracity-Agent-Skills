---
name: veracity-auth-ui
description: >-
  Use this skill whenever the user wants Veracity login on a frontend or a complete Veracity web app. It adds Sign In/Out, user profile, and the user's Veracity services/applications (V3/V4) to a React (or other) SPA, wired to a Veracity BFF (/auth, /auth/challenge, /signout, /api/me) in .NET, Node, or Python. It scaffolds the frontend via web-base-ui and creates the BFF via veracity-auth-net (.NET default), veracity-auth-node, or veracity-auth-python when none exists, so it is the entry point for a full web app (frontend + backend): prefer it over the backend-only auth skills whenever the user asks for a "web app" or full application. Trigger it even without the word "Veracity": phrasings like "web app with login and show my applications", "add sign-in and list my applications", or "web app with Veracity authentication and V4 integration" map here. If a Veracity BFF already exists, use this skill to wire the frontend to it; for a plain unauthenticated frontend, use web-base-ui.
license: Apache-2.0
---

# Veracity Login Web App (authentication layer)

Add Veracity authentication to a web frontend. This skill layers login on top of a frontend SPA:

- **Sign In, Sign Out, authenticated user profile**, and the user's Veracity **services/applications** (V3/V4, optional).
- Wired to a **Veracity Identity-enabled BFF** (.NET, Node, or Python) exposing `/auth`, `/auth/challenge`, `/signout`, and `/api/me`.
- A dev-server **proxy** to the BFF over **HTTPS**, so the secure auth cookie flows same-origin.

The frontend checks `GET /auth`, shows a **Sign in** button that redirects to `/auth/challenge` when clicked, and shows the user (from `GET /api/me`) plus a **Sign out** link when authenticated. The auth core is fixed; the **login UI is built with the frontend's design system** (the one the scaffold already uses).

> **Separation of concerns**: This skill does **not** scaffold the baseline frontend itself. The baseline (project setup, `package.json` generation, TypeScript/Vite config, a welcome page, and the design-system machinery — ShadCN default, detected systems, design.md) is owned by the **`web-base-ui`** skill. This skill ensures that baseline exists (creating it via `web-base-ui` when missing) and then layers Veracity authentication on top. It also ensures a Veracity BFF exists (reusing one, using a user-provided URL, or creating one via **`veracity-auth-net`** for a .NET backend — the default — or **`veracity-auth-node`** / **`veracity-auth-python`** for a Node or Python backend).

## Required BFF endpoints

Whatever backend is used, it must expose at least:

| Endpoint | Purpose |
|----------|---------|
| `GET /auth` | Returns `{ "result": boolean }` — is the user signed in (anonymous-safe) |
| `GET /auth/challenge` | Triggers OIDC sign-in; accepts `?returnUrl=` (relative) |
| `GET /api/me` | Returns the current user; `401` if not authenticated |
| `GET /signout` | Signs the user out |

Optionally (enabled via [Step 2e](#step-2e--detect-the-policy-compliance-endpoint)):

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/veracity/v{3\|4}/policy/validate` | Returns `{ compliant, redirectUrl }` (`406` when the user must accept terms / lacks a subscription) — drives the on-load policy-compliance check |

## Phase 0: Gather requirements

Before doing anything, settle the choices below. **Keep the happy path fast: apply the defaults and only ask the user when a decision is genuinely ambiguous, risky, or the user's request contradicts a default.** Record the answers — later phases consume them. When you do ask, prefer a single, focused multiple-choice question per topic.

1. **Project name** — resolve a candidate using the rules in [Phase 1](#phase-1-resolve-project-name--layout), then **confirm it with the user** (or let them supply a different one). This names every generated artifact and is passed to `web-base-ui` when scaffolding.

2. **Backend (BFF) strategy** — decide how the Veracity backend is provided:
   - **Create a new BFF** (default when none is detected) — see Step 2c. When creating, also resolve the **backend stack** (`{BackendStack}`):
     - **.NET** (default) — created via `veracity-auth-net`; produces a `.sln` / `.csproj` project and runs over HTTPS.
     - **Node** — created via `veracity-auth-node` (Express baseline); produces a `package.json` project.
     - **Python** — created via `veracity-auth-python` (FastAPI baseline); produces a `pyproject.toml` project.

     Pick **.NET** unless the user asks for a Node/Express/Fastify/NestJS or Python/FastAPI/Flask/Django backend (or an existing non-.NET BFF is detected in Step 2a, which fixes the stack). Only ask when the user's intent is genuinely ambiguous. `{BackendStack}` selects the artifact conventions used throughout (name casing, project layout, backend-URL source) — see Phase 1.
   - **Reuse an existing BFF** found in the workspace — see Step 2a (its stack is detected, not chosen).
   - **Use an external backend URL** the user already runs — see Step 2b.
   Resolve this with the detection logic in Phase 2; only ask when truly ambiguous.

3. **Veracity Service API version** *(only when creating a new BFF in Step 2c)* — ask which Veracity Service API the BFF should integrate so it can serve the user's services/applications. Offer **exactly these three** choices (do **not** present a "both" or freeform "other" option — ask as a closed multiple-choice question):
   - **V4 (tenant-aware applications)** — recommended/default for new, tenant-aware apps; serves `/api/v1/veracity/v4/me/applications`. Reference docs: [VTM API overview](https://docs.veracity.com/pages/developer-foundations/access-management/veracity-tenant-management-vtm/vtm-api/vtm-api-overview) and [API Explorer](https://docs.veracity.com/apis/platform/ApiV4Prod).
   - **V3 (legacy services)** — for legacy-mode applications; serves `/api/v1/veracity/v3/services`. Reference docs: [MyServices V3 API Explorer](https://docs.veracity.com/apis/platform/veracity-myservices-v3).
   - **Neither** — no Veracity Service API integration; the BFF only handles authentication.

   Share the reference links above if the user is unsure which version to pick. Pass the choice to the backend skill selected in item 2 (`veracity-auth-net`, `veracity-auth-node`, or `veracity-auth-python`) in Step 2c. For a reused or external BFF, the version is whatever that backend already exposes (detected in Step 2d), not asked.

4. **Show the user's services / applications?** — default **yes**. When yes, the frontend lists the user's V3 services and/or V4 applications (whichever the BFF exposes). This preference is combined with the BFF's actual capability to produce the final flags — see [the flag model](#step-2d--detect-the-veracity-api-endpoints-v3--v4).

5. **UI design system & tech stack** — these are **owned by `web-base-ui`**, not this skill. You still need to know them so the login presentation matches the scaffold:
   - If a frontend scaffold already exists, **detect** its design system and tech stack from the project (see Phase 3.5) and build the login UI to match.
   - If you will scaffold via `web-base-ui` (Phase 3.5), resolve the **design system** (detect a configured one; else default **ShadCN**) and **tech stack** (default **React + Vite + TypeScript**) and pass them through to `web-base-ui`. See that skill's *UI design system* and *Alternative tech stacks* sections for the full rules — do not duplicate the machinery here.

## Phase 1: Resolve project name & layout

Derive the base project name (present it to the user for confirmation). The **name casing and layout conventions depend on `{BackendStack}`** (Phase 0 item 2): PascalCase dotted names (e.g. `Veracity.Demo`) for a **.NET** backend; kebab-case slugs (e.g. `veracity-demo`) for a **Node** or **Python** backend. Resolve the base name from the first rule that applies:

1. Existing `.sln` file → solution base name **(.NET signal → `{BackendStack}` = .NET)**
2. Existing `.csproj` (under `src/` **or** at the repo root) → base name minus `.Web` / `.Api` / `.Client` **(.NET signal → .NET)**
3. Existing Node `package.json` `name` → kebab-case slug **(Node signal → `{BackendStack}` = Node)**
4. Existing Python `pyproject.toml` `[project].name` → kebab-case slug **(Python signal → `{BackendStack}` = Python)**
5. Git repository name → PascalCase for .NET, kebab-case otherwise
6. Current working directory name → PascalCase for .NET, kebab-case otherwise
7. **Fallback** — if none of the above yield a usable name (e.g. empty workspace, or only scratch/output directories), default to **`Veracity.Demo`** (.NET) or **`veracity-demo`** (Node/Python).

> Rules 1–4 that match a project file also **confirm the backend stack** for a reused BFF; when *creating* a new BFF in an empty workspace, `{BackendStack}` comes from Phase 0 item 2 (default .NET) and the name casing follows it.

> **Never** derive the name from a scratch/output directory (`outputs/`, `temp/`); fall back to the stack-appropriate default instead.

### Frontend location — mirror the BFF, place it as a **sibling**

The frontend directory is **not** hardcoded to `src/`. It is placed **next to the BFF project** (the same parent directory), so it lives at the same level as the BFF project — never nested inside it. The frontend folder name follows `{BackendStack}`: `{Base}.Client` for **.NET** (a .NET idiom), `{base}-client` (kebab-case) for **Node** / **Python**. The exact target is finalized in Phase 2 once the BFF is resolved, using this rule:

- Let `{BffDir}` be the directory of the resolved/created BFF project.
- **Frontend target** `{FrontendDir}` = `<parent of {BffDir}>/{FrontendName}/`, where `{FrontendName}` = `{Base}.Client` (.NET) or `{base}-client` (Node/Python).

Examples:

| `{BackendStack}` | Resolved BFF directory | Frontend directory (`{FrontendDir}`) |
|------------------|------------------------|--------------------------------------|
| .NET | `src/{Base}.Web/` | `src/{Base}.Client/` |
| .NET | `{Base}.Api/` (repo root) | `{Base}.Client/` (repo root, sibling) |
| .NET | `MyApi/` (repo root) | `MyApi.Client/` (repo root, sibling) |
| Node | `src/{base}-api/` (or the Node BFF dir) | `src/{base}-client/` |
| Python | `src/{base}-api/` (or the Python BFF dir) | `src/{base}-client/` |
| _any_ | _user-provided URL, no local project_ | `src/{Base}.Client/` (.NET) or `src/{base}-client/` (default) |

When a **new** .NET BFF is created (Step 2c), it is placed at `src/{Base}.Web/`, so the frontend naturally lands at `src/{Base}.Client/`. When a **new** Node or Python BFF is created, the frontend is its `{base}-client` sibling.

## Phase 2: Resolve the BFF (default: create one)

A Veracity-integrated BFF is **required**. Resolve it in this priority order and **only ask the user when truly ambiguous**:

**Step 2a — Detect an existing BFF.** Search the **whole workspace** — not just `src/` — for a project that exposes `/auth` and `/auth/challenge`, in **any** backend stack. Grep recursively for the literal `/auth/challenge`, then classify the match by stack:

- **.NET** — the match appears in `.cs` files as Minimal API `MapGet("/auth/challenge"` **or** MVC Controllers `[HttpGet("/auth/challenge")]`; secondary signals: `MapGet("/auth"`, an `AuthController` class / `[HttpGet("/auth")]`, plus a `.csproj`/`.sln` nearby.
- **Node** — the match appears in `.ts`/`.js` files alongside Express/Fastify/NestJS markers (e.g. `registerAuthRoutes`, `app.get("/auth/challenge"`, `@Get("auth/challenge")`, `authRouter`) with a `package.json` nearby.
- **Python** — the match appears in `.py` files as a FastAPI/Flask/Django route (e.g. `@router.get("/auth/challenge")`, `@app.route("/auth/challenge")`, a `path("auth/challenge", ...)`) with a `pyproject.toml`/`requirements.txt` nearby.

Look at the repo root (e.g. `./MyApi/`) **and** under `src/`. If found, **reuse it** — do not create a new backend. Record its directory as `{BffDir}` and its stack as `{BackendStack}` (both feed Phase 1's naming/layout rule); detect its URL in Phase 3.

> A reused BFF may be **.NET** (Minimal API or MVC Controllers), **Node** (Express/Fastify/NestJS), or **Python** (FastAPI/Flask/Django) — whichever had Veracity auth added by the matching sibling skill. This does **not** affect the frontend: every stack exposes the **same** endpoint contract (`/auth`, `/auth/challenge`, `/api/me`, `/signout`, `/api/v1/veracity/v3/...`, `/api/v1/veracity/v4/...`). Only the detection greps and the backend-URL source (Phase 3) differ — the rendered frontend assets are identical.

**Step 2b — Did the user explicitly supply a backend?** Only if the user's request explicitly states they already have a Veracity backend (e.g. "I already have a BFF at `https://localhost:7123`") should you skip creating one. Ask for / use that base URL, validate it is a well-formed absolute `https` URL, optionally confirm it serves `/auth` (`curl -k <url>/auth`; treat failure as a warning, not a blocker), and use it directly in Phase 3. Do **not** scaffold any backend in this case. There is no local `{BffDir}`, so the frontend defaults to `src/{Base}.Client/` or `src/{base}-client/` per `{BackendStack}` (Phase 1).

**Step 2c — Otherwise, create a new BFF (default).** This is the default path for "create a new web app" / "from scratch" requests. **Do not ask** whether to create a backend and **do not** skip this step. Route to the sibling skill for `{BackendStack}` (Phase 0 item 2; default **.NET**):

1. **Determine `{FRONTEND_PORT}`** — the Vite dev server port the browser will use:
   - If the frontend project already exists at `{FrontendDir}`, read its `vite.config.ts` for an explicit `server.port` value.
   - Otherwise, use Vite's default: **`5173`**.
   - If the user has explicitly stated a different port, use that.

2. **Invoke the backend skill for `{BackendStack}`**, always passing Authentication strategy **OpenID Connect**, the Veracity Service API version from **Phase 0 item 3** (V3, V4, or neither), and **`REDIRECT_BASE_URL = https://localhost:{FRONTEND_PORT}`** so the OIDC callback lands on the frontend dev-server origin and flows back through the Vite proxy:

   | `{BackendStack}` | Skill | Project / location | Records `{BffDir}` | Backend artifacts |
   |------------------|-------|--------------------|--------------------|-------------------|
   | **.NET** (default) | `veracity-auth-net` | `src/{Base}.Web/` | `src/{Base}.Web/` | `.sln`, `.csproj`, `launchSettings.json` (HTTPS) |
   | **Node** | `veracity-auth-node` | `src/{base}-api/` (Express baseline) | the created project dir | `package.json` (HTTP by default) |
   | **Python** | `veracity-auth-python` | `src/{base}-api/` (FastAPI baseline) | the created project dir | `pyproject.toml` (HTTPS) |

   - For **.NET**, `REDIRECT_BASE_URL` makes `RedirectUrl` in `appsettings.Development.json` target `https://localhost:{FRONTEND_PORT}/signin-oidc`.
   - For **Node** / **Python**, `REDIRECT_BASE_URL` makes `REDIRECT_URI = https://localhost:{FRONTEND_PORT}/auth/callback` (the callback is forwarded by the SPA's `/auth` dev-proxy rule).
   - **Only the .NET path creates a `.sln` / `.csproj`.** Do **not** generate a solution file or any `.csproj`/`launchSettings.json` for a Node or Python backend — those skills own their `package.json` / `pyproject.toml` layout.

Record `{BffDir}` from the table above. After the backend skill completes, verify the four endpoints (`/auth`, `/auth/challenge`, `/api/me`, `/signout`) exist, then continue to Phase 3.

> The frontend is useless without a backend that integrates Veracity identity. When in doubt, **create the BFF** rather than asking or proceeding without one.

### Step 2d — Detect the Veracity API endpoints (V3 / V4)

Decide which Veracity data the frontend shows. Each version's display flag is the **AND** of two gates — the BFF can serve it **and** the user wants it (Phase 0 item 4, default `true`):

```
V3_ENABLED = BFF_V3_ENABLED && USER_WANTS_VERACITY_DATA
V4_ENABLED = BFF_V4_ENABLED && USER_WANTS_VERACITY_DATA
```

These become `__V3_ENABLED__` / `__V4_ENABLED__` in Phase 4, so the app never calls an endpoint the BFF lacks nor shows data the user hid.

Detect `BFF_Vx_ENABLED` by grepping the BFF source. For a **user-provided URL** (Step 2b) the source isn't available, so default both to `false` unless the user says the endpoints exist; when the BFF was just **created** in Step 2c, grep the *generated* source (capability depends on the API version passed to the backend skill).

Grep for the substring `veracity/v3` / `veracity/v4`, which matches **both** styles — Minimal API paths (`/veracity/v3/services`) **and** MVC Controller route attributes (`[Route("api/v1/veracity/v3")]`). The `MapVxEndpoints` / `VeracityVxController` symbols are additional style-specific signals.

| Flag | Grep the BFF for | Served path the frontend calls |
|------|------------------|--------------------------------|
| `BFF_V3_ENABLED` | `veracity/v3` — i.e. Minimal API `/veracity/v3/services` / `MapV3Endpoints`, or Controllers `[Route("api/v1/veracity/v3")]` / `VeracityV3Controller` | `/api/v1/veracity/v3/services` (lists the user's services) |
| `BFF_V4_ENABLED` | `veracity/v4` — i.e. Minimal API `/veracity/v4/me/applications` / `MapV4Endpoints`, or Controllers `[Route("api/v1/veracity/v4")]` / `VeracityV4Controller` | `/api/v1/veracity/v4/me/applications` (lists the user's applications) |

Results are rendered by `src/components/VeracityData.tsx`, proxied through the existing `/api` route.

### Step 2e — Detect the policy-compliance endpoint

**Do this only after the BFF has been resolved (Steps 2a–2c) — a reused, user-provided, or newly-created BFF.** Decide whether the frontend runs a **policy-compliance check** on load (verifying the signed-in user has accepted the latest Veracity terms and holds any required subscription, redirecting them if not).

Search the BFF for a route matching `policy/validate` — grep the source for the substring `policy/validate`, which matches **both** styles (Minimal API `MapGet("/veracity/v3/policy/validate"` / `.../v4/...` and MVC Controllers `[HttpGet("policy/validate")]` under a `[Route("api/v1/veracity/v{3|4}")]` controller). For a **user-provided URL** (Step 2b) the source is not available, so treat it as "not found" unless the user says the endpoint exists.

- **If found** — set `POLICY_ENABLED = true` and include it automatically. Inform the user: *"Detected `policy/validate` endpoint in the backend — adding policy compliance check on app load."*
- **If NOT found** — explain and ask (default **yes**): *"The backend does not currently have a `policy/validate` endpoint. This checks whether the user has accepted the latest Veracity terms on app load, redirecting them if not. Would you like to include it? The backend endpoint will need to be added separately. [Yes / No] (default: Yes)"* Set `POLICY_ENABLED` from the answer.

**Resolve `{POLICY_VALIDATE_PATH}`** (the path the frontend calls) from the BFF's Veracity API version:

| BFF exposes | `{POLICY_VALIDATE_PATH}` |
|-------------|--------------------------|
| a `veracity/v4/policy/validate` route (or V4 was chosen in Step 2c) | `/api/v1/veracity/v4/policy/validate` |
| a `veracity/v3/policy/validate` route (or V3 was chosen in Step 2c) | `/api/v1/veracity/v3/policy/validate` |
| neither can be determined (e.g. user-provided URL, endpoint added later) | default to `/api/v1/veracity/v4/policy/validate` |

`POLICY_ENABLED` is **independent** of the show-services preference (Step 2d): a project can run the compliance check without listing services, or vice versa.

> When the backend has no `policy/validate` endpoint but the user opts in, the frontend is wired to call it and you must tell the user the backend endpoint has to be added separately — the sibling **veracity-auth-net** (`.NET`), **veracity-auth-node**, and **veracity-auth-python** skills generate a matching `v3`/`v4` `policy/validate` endpoint driven by a configured service id.

## Phase 3: Resolve the backend URL (proxy target)

Resolve `{BACKEND_SERVER_URL}` from the source appropriate to `{BackendStack}`:

- **.NET BFF** (existing or newly-created) — read `src/{Base}.Web/Properties/launchSettings.json` (or the reused project's `Properties/launchSettings.json`). Use the `https` profile's `applicationUrl`; if it is semicolon-separated, pick the entry starting with `https://`. Inform the user: *"Detected backend URL `https://localhost:NNNN` from launchSettings.json."*
- **Node BFF** (`veracity-auth-node`) — there is no `launchSettings.json`. Use the port the skill reported (its README / `.env` `PORT`, default **`54438`**), giving `http://localhost:54438` unless the BFF was configured for HTTPS. Inform the user of the detected URL.
- **Python BFF** (`veracity-auth-python`) — no `launchSettings.json`. Use the skill's HTTPS dev port (README / settings, default **`54438`**), giving `https://localhost:54438`.
- **User-provided URL** — use it as-is.
- **Fallback** — if no URL can be determined, ask the user for the backend URL.

Store the result as `{BACKEND_SERVER_URL}`.

> **HTTP Node BFF reminder:** when `{BACKEND_SERVER_URL}` is `http://...` (a plain-HTTP `veracity-auth-node` BFF behind this HTTPS dev proxy), apply the `xfwd: true` proxy fix documented in Phase 4 so the secure session cookie is set correctly.

## Phase 3.5: Ensure the frontend scaffold exists (default: create one via `web-base-ui`)

Detect whether a scaffolded frontend project already exists at `{FrontendDir}` (or elsewhere in the workspace if the user points you at it):

- Look for a frontend project root — a `package.json` plus an app entry (`src/main.tsx` / `src/App.tsx` and `index.html` for the React+Vite default, or the equivalent for another stack).

**If no frontend scaffold exists → scaffold it first via the `web-base-ui` skill.**

Invoke the **`web-base-ui`** skill, passing:
- the **project name** confirmed in Phase 1,
- the target **frontend directory** `{FrontendDir}` resolved in Phase 1 (a **sibling** of the BFF project),
- the **design system** resolved in Phase 0 item 5 (detected configured system, else ShadCN default),
- the **tech stack** resolved in Phase 0 item 5 (React + Vite + TypeScript default).

After `web-base-ui` completes, you will have a clean, building welcome-page frontend at `{FrontendDir}` with `package.json`, `tsconfig.json`, a **plain** `vite.config.ts` (no proxy/HTTPS), the app shell, and the design system set up. Proceed to Phase 4 to integrate authentication into it.

**If a frontend scaffold already exists → skip scaffolding** and proceed directly to Phase 4, integrating auth into the existing project. **Detect** its design system (the `web-base-ui` detection rules) and tech stack, and add only what is missing; preserve existing components, config, and styles.

> In both cases, the remaining work is identical: you are **integrating Veracity authentication into an existing frontend baseline**. The only difference is whether that baseline was just created by `web-base-ui` or already present.

> **Safety**: if you are scaffolding and `{FrontendDir}` already exists and is non-empty, `web-base-ui` will stop and ask before writing into it.

## Phase 4: Apply authentication to the frontend

The frontend lives at `{FrontendDir}`. Integrate the auth core by rendering the auth assets and merging the proxy/HTTPS config into the existing scaffold. **Do not** re-scaffold `package.json`, `tsconfig.json`, `index.html`, `main.tsx`, or the design-system setup — those are owned by `web-base-ui` and already present.

> **Tech-stack branch.** The instructions below describe the **default React + Vite + TypeScript** path. If the frontend uses an **alternative stack** (vanilla JS/HTML or a non-Vite bundler), do **not** render the React/Vite `assets/` verbatim — instead follow [Alternative tech stacks](#alternative-tech-stacks-vanilla-jshtml--other-bundlers) to add the same auth-core contract (the four BFF endpoints, the login behavior, the dev-server proxy over HTTPS) to that stack, using the React `assets/` as the reference.

### Step 4a — Render the auth-core assets

Render these files from [`assets/`](./assets/) into `{FrontendDir}`, applying the replacements below. `src/App.tsx` **replaces** the welcome-shell `App.tsx` that `web-base-ui` produced (it adds the auth orchestration while keeping the project name).

| Placeholder | Replace with |
|-------------|--------------|
| `{{projectName}}` | The base project name (e.g. `MyApp`) |
| `{BACKEND_SERVER_URL}` | The resolved backend URL from Phase 3 |
| `__V3_ENABLED__` | `true` if `V3_ENABLED` (Step 2d), else `false` |
| `__V4_ENABLED__` | `true` if `V4_ENABLED` (Step 2d), else `false` |
| `__POLICY_ENABLED__` | `true` if `POLICY_ENABLED` (Step 2e), else `false` |
| `{POLICY_VALIDATE_PATH}` | The policy path resolved in Step 2e (e.g. `/api/v1/veracity/v4/policy/validate`) |

| Template (`assets/`) | Target | Layer |
|----------------------|--------|-------|
| `src/App.tsx` | `src/App.tsx` (replaces the welcome shell) | core (auth wiring — keep as-is) |
| `src/api/auth.ts` | `src/api/auth.ts` | core |
| `src/api/safeRedirect.ts` | `src/api/safeRedirect.ts` | core (redirect guards: open-redirect CWE-601 + XSS CWE-80) |
| `src/api/veracity.ts` | `src/api/veracity.ts` | core |
| `src/hooks/useAuth.ts` | `src/hooks/useAuth.ts` | core |
| `src/components/LoginExperience.tsx` | `src/components/LoginExperience.tsx` | presentation (UI contract) |
| `src/components/LoginHeader.tsx` | `src/components/LoginHeader.tsx` | presentation |
| `src/components/VeracityData.tsx` | `src/components/VeracityData.tsx` | presentation |

`{{projectName}}` appears in `App.tsx` (as a `PROJECT_NAME` constant); the presentation receives it as a **prop**, so generated design-system files need no `{{projectName}}` substitution. `__V3_ENABLED__` / `__V4_ENABLED__` / `__POLICY_ENABLED__` appear only in `App.tsx` (the `SHOW_V3` / `SHOW_V4` / `ENABLE_POLICY_CHECK` constants); `{POLICY_VALIDATE_PATH}` appears only in `src/api/veracity.ts` (the `POLICY_VALIDATE_PATH` constant). After substitution, grep the output for any leftover `{{`, `{BACKEND_SERVER_URL}`, `__V3_ENABLED__`, `__V4_ENABLED__`, `__POLICY_ENABLED__`, or `{POLICY_VALIDATE_PATH}`.

> **`__V3_ENABLED__` / `__V4_ENABLED__` / `__POLICY_ENABLED__` must become a bare `true` or `false`** so `App.tsx` reads `const SHOW_V3 = true` / `const SHOW_V4 = false` / `const ENABLE_POLICY_CHECK = true`. Never leave the literal placeholder — it is not valid TypeScript and the build will fail. `{POLICY_VALIDATE_PATH}` is a **string** constant (`const POLICY_VALIDATE_PATH = '{POLICY_VALIDATE_PATH}'`); once replaced with a real path (e.g. `/api/v1/veracity/v4/policy/validate`) it is a valid string literal — always replace it, even when `__POLICY_ENABLED__` is `false` (the helper is simply never called).

> **TSX caveat**: in `App.tsx`, `{{projectName}}` is the value of a string constant (`const PROJECT_NAME = '{{projectName}}'`). Once replaced with plain text (e.g. `MyApp`) it is a valid string literal. Never leave the literal `{{projectName}}` in a `.tsx` file, or the build will fail.

### Step 4b — Merge the dev-server proxy + HTTPS into `vite.config.ts`

`web-base-ui` ships a **plain** `vite.config.ts` (react plugin + dev server only). Auth requires a same-origin HTTPS proxy to the BFF so the secure auth cookie flows. **Merge** the following into the existing `vite.config.ts` (use [`assets/vite.config.ts`](./assets/vite.config.ts) as the target shape) **without removing** the `react()` plugin, the **`@tailwindcss/vite`** plugin (present when the design system is ShadCN/Tailwind — dropping it makes Tailwind stop compiling and the app renders unstyled), or any `resolve.alias` the design system added:

- Add the `@vitejs/plugin-basic-ssl` plugin and `server.https: {}` (HTTPS dev server).
- Add the `server.proxy` routes: `/api`, `/auth/challenge` (**before** `/auth`), `/auth`, `/signin-oidc`, `/signout`, all `secure: false`, targeting `{BACKEND_SERVER_URL}`. The V3/V4 API calls (`/api/v1/veracity/v3/services`, `/api/v1/veracity/v4/me/applications`) are proxied through the existing `/api` route — no separate route is needed.
- Verify no leftover `{BACKEND_SERVER_URL}` placeholder remains.

> **HTTP BFF behind the HTTPS proxy (Node/Python BFFs).** The default `.NET` BFF runs over HTTPS (`{BACKEND_SERVER_URL}` is `https://...`), so the secure session cookie flows without extra config. But when `{BACKEND_SERVER_URL}` is **`http://...`** — e.g. a **`veracity-auth-node`** or `veracity-auth-python` BFF running on plain HTTP behind this HTTPS dev proxy — the proxy→BFF hop is HTTP, so the BFF sees `req.secure === false` and will **not** set the `Secure`/`__Host-` session cookie. The OIDC callback then lands with an empty session and fails (state mismatch → 400). Fix: add **`xfwd: true`** to every proxy route (so `X-Forwarded-Proto: https` reaches the BFF) and ensure the BFF trusts the proxy (Express: `app.set("trust proxy", 1)`). Alternatively run the BFF over HTTPS.

Add **`@vitejs/plugin-basic-ssl`** (range `^2`) to the frontend's `package.json` `devDependencies`, resolving its latest compatible version from the npm registry as a caret range (same rule `web-base-ui` uses for the base manifest).

> **HTTPS dev server**: the frontend is served over **HTTPS** via `@vitejs/plugin-basic-ssl`. This matches the BFF's secure auth cookie (e.g. `__Host-` prefixed cookies require HTTPS) and keeps the same-origin proxy working. The plugin issues a self-signed dev certificate, so browsers show a one-time trust warning on first load — accept it to proceed. Register the resulting `https://localhost:NNNN` dev origin as a B2C redirect URI.

## UI design system & the presentation contract

The login UI is built with **the frontend's design system** (set up by `web-base-ui`, or already configured in an existing project). Only the **presentation** layer varies; the auth core is identical across design systems. Every presentation must satisfy the **UI contract**: it implements `src/components/LoginExperience.tsx`, a pure, prop-driven component with this shape (see the reference in [`assets/`](./assets/src/components/LoginExperience.tsx)):

```ts
export interface LoginExperienceProps {
  projectName: string
  loading: boolean
  isAuthenticated: boolean
  user: CurrentUser | null   // type imported from ../api/auth (type-only is fine)
  onSignIn: () => void
  onSignOut: () => void
  showV3: boolean
  showV4: boolean
}
```

Contract rules every design-system implementation must follow:

- **Render the same login states** — a **Sign in** button when signed out; the user's name (`user?.displayName || user?.email`) + a **Sign out** control when signed in; a loading indicator while `loading` is true.
- **Trigger auth only via callbacks** — call `onSignIn` / `onSignOut`; never navigate to `/auth/challenge` or `/signout`, never fetch `/auth` or `/api/me`, and never add a global fetch interceptor.
- **Show optional Veracity data via `<VeracityData isAuthenticated showV3 showV4 />`** (a small prop-driven component you may also restyle), gated by `showV3` / `showV4`.
- **Stay presentation-only** — receive everything via props; do not import `useAuth`. Importing the `CurrentUser` *type* from `../api/auth` is allowed.

## Phase 4c: Build the login UI with the frontend's design system

Build the presentation files (`src/components/LoginExperience.tsx` and any sub-components/styles) to the contract above, using the frontend's design system. **Do not touch the auth core** (`App.tsx`, `api/`, `hooks/`).

- **ShadCN** *(the default `web-base-ui` sets up when no design system was configured)* — rebuild `LoginExperience` (and a restyled `LoginHeader` / `VeracityData`) using shadcn primitives (e.g. `Button`, `Card`, `Avatar`). The shadcn setup (Tailwind, `components.json`, `@/` alias, `src/lib/utils.ts`) is already in place from `web-base-ui`; if you need to add primitives or guidance, use the **bundled** shadcn skill at [`../web-base-ui/vendor/shadcn/SKILL.md`](../web-base-ui/vendor/shadcn/SKILL.md) (a redistributed MIT-licensed copy provided by `web-base-ui`; do not depend on fetching it from the network). Keep the `@/` alias consistent in `tsconfig.json` and `vite.config.ts`, and do not break the proxy / `basicSsl` / `react` plugin config when editing `vite.config.ts`.
- **design.md** — when the frontend was built to a Google Stitch `design.md` spec, build the login presentation to the same spec, still satisfying the contract.
- **Configured / user-provided design system** — when the frontend already uses a design system (VUI, MUI, Chakra, Ant, a custom library, etc.), build the login presentation with **that** system's components and patterns. If it cannot be set up cleanly, fall back to the plain reference templates and tell the user.

> **Fallback:** if the chosen design-system presentation fails to build and cannot be fixed quickly, revert the login presentation to the plain `assets/` templates (which already satisfy the contract) so the app still builds, and inform the user.

## Alternative tech stacks (vanilla JS/HTML / other bundlers)

When the frontend uses a non-React/Vite stack (recorded in Phase 0 / detected in Phase 3.5), the **auth-core contract is unchanged** — only its implementation language/tooling differs. Reimplement the same contract in the frontend's stack, using the React `assets/` as the reference:

- **Same four BFF endpoints** — `GET /auth`, `GET /auth/challenge`, `GET /api/me`, `GET /signout` (see [Required BFF endpoints](#required-bff-endpoints)).
- **Same login behavior** — check `/auth` on load; fetch `/api/me` only when authenticated; **Sign in** = full-page navigation to `/auth/challenge?returnUrl=` (relative `returnUrl`); **Sign out** = full-page navigation to `/signout`; a `401` from `/api/me` triggers a scoped re-auth; **no global fetch interceptor**; `fetch` uses `credentials: 'include'`. (Mirror `assets/src/api/*`, `assets/src/hooks/useAuth.ts`, and `assets/src/App.tsx`.)
- **Same policy-compliance check (when `POLICY_ENABLED`)** — after a signed-in user is loaded, call the BFF `{POLICY_VALIDATE_PATH}` (`GET`, `credentials: 'include'`); on a `200`/`406` body of `{ compliant, redirectUrl }`, if `!compliant`, compute `sanitizeRedirectUrl(redirectUrl)` and navigate the browser **only to that sanitized value** (never the raw `redirectUrl`). Mirror `validatePolicy()` in `assets/src/api/veracity.ts`, `sanitizeRedirectUrl()` in `assets/src/api/safeRedirect.ts`, and its call site in `assets/src/hooks/useAuth.ts`.
- **Same dev-server proxy** — whatever dev server/bundler the frontend uses must proxy the same routes to `{BACKEND_SERVER_URL}` over HTTPS as `vite.config.ts` does (`/api`, `/auth/challenge` **before** `/auth`, `/signin-oidc`, `/signout`; `secure: false`). For non-Vite bundlers, configure the equivalent dev-server proxy + HTTPS.
- **Same auth-core vs presentation split** — keep auth wiring out of the presentation; expose the same login states regardless of how the UI is rendered.
- **Build is still the hard gate** (Phase 6): the chosen stack's build/typecheck must pass.

## Phase 5: Login-state UI (behavior implemented in the core)

The auth core implements the agreed behavior — **show login state, do not force**:

- `src/api/auth.ts` — `getAuthStatus()` (`/auth`), `getCurrentUser()` (`/api/me`, `credentials: 'include'`), `signIn()` (full nav to `/auth/challenge?returnUrl=`), `signOut()` (full nav to `/signout`). `returnUrl` is built from the **relative** `pathname + search + hash` only and is additionally passed through `toRelativeReturnUrl()` before navigation, so an explicitly-supplied `returnUrl` can never become an off-site redirect (open-redirect guard, CWE-601).
- `src/api/safeRedirect.ts` — the redirect guards: `toRelativeReturnUrl()` coerces a `returnUrl` to a safe same-origin relative path; `sanitizeRedirectUrl()` validates an absolute redirect target (the BFF policy `redirectUrl`) and returns a re-serialized safe URL string (or `null`) — only https same-origin or approved-Veracity-host targets pass, and every dangerous scheme (`javascript:`, `data:`, …) is rejected. Guards both CWE-601 (open redirect) and CWE-80 (XSS via `javascript:` URI). `isAllowedRedirect()` is a boolean wrapper.
- `src/hooks/useAuth.ts` — checks `/auth` on load; fetches `/api/me` **only when** `/auth` is true (anonymous visitors are never redirected). A `401` from `/api/me` triggers a silent re-auth. When `enablePolicyCheck` is passed (from `App.tsx`), a signed-in user is then checked via `validatePolicy()`; a non-compliant user is redirected **only** to `sanitizeRedirectUrl(redirectUrl)` — the sanitizer's return value, never the raw `policy.redirectUrl`, is assigned to `window.location.href`.
- `src/App.tsx` — the thin core shell: calls `useAuth`, sets `PROJECT_NAME` / `SHOW_V3` / `SHOW_V4` / `ENABLE_POLICY_CHECK`, passes the flags as props/args (`ENABLE_POLICY_CHECK` → `useAuth({ enablePolicyCheck })`). Auth wiring lives here, not in the presentation.
- `src/components/LoginExperience.tsx` — the UI-contract adapter (varies by design system): renders the login states and `<VeracityData>` from props only.
- `src/components/LoginHeader.tsx` — Sign in button (signed out) or user name + Sign out (signed in); prop-driven.
- `src/api/veracity.ts` — `getMyServices()` (`/api/v1/veracity/v3/services`), `getMyApplications()` (`/api/v1/veracity/v4/me/applications`), and `validatePolicy()` (`{POLICY_VALIDATE_PATH}`); each returns `null` on any error so missing endpoints degrade gracefully. `validatePolicy()` returns the `{ compliant, redirectUrl }` body on both `200` and `406`.
- `src/components/VeracityData.tsx` — when signed in, fetches and lists the V3 services and/or V4 applications, gated by the `showV3` / `showV4` props (`__V3_ENABLED__` / `__V4_ENABLED__` from Step 2d). Renders nothing when both are `false`, so the app never calls an endpoint the BFF does not expose.

> **Do not add a global fetch interceptor.** The 401→challenge recovery is scoped to `/api/me` so optional/anonymous calls never force a login.

### Optional variant — auto-challenge on load

If the user instead wants to **force** login (redirect immediately when not authenticated), change `useAuth` so that when `getAuthStatus()` returns `false` it calls `signIn()` instead of rendering the Sign in button. Only do this if the user explicitly asks for forced/mandatory login.

## Phase 6: Install & verify (build only)

Confirm the frontend `package.json` includes the auth-added `@vitejs/plugin-basic-ssl` dev dependency (caret range), and that no `{{projectName}}` / `{BACKEND_SERVER_URL}` / `__V3_ENABLED__` / `__V4_ENABLED__` placeholders remain. Detect the package manager (lockfile → `packageManager` field → CLI availability → default `npm`). Install and build:

```bash
cd {FrontendDir}
<pm> install
<pm> run build   # default stack: tsc && vite build — must succeed
```

> For an **alternative stack**, run that stack's build/typecheck instead; it is the same hard gate.

> The build is the **hard gate**, especially for ShadCN (path aliases, Tailwind, `@/lib/utils`). If it fails and cannot be fixed quickly, apply the Phase 4c fallback (revert presentation to the plain templates) so the app builds.

> **Optional manual smoke test (not a build gate).** A full sign-in test requires the BFF running, its secrets configured, and the dev origin registered as a B2C redirect URI. Describe it but do not treat failure as a build error:
> 1. Start the BFF, then `cd {FrontendDir} && <pm> start`.
> 2. Open the app, confirm `/auth` resolves and the Sign in button appears.
> 3. Click Sign in → Veracity login → redirected back signed in.

## Phase 7: Update README

Create or update `README.md` in the repo root to document:

1. **Architecture** — frontend (built with the chosen design system) + Veracity BFF (or external backend URL); login via `/auth` / `/auth/challenge` / `/api/me` / `/signout`.
2. **Projects** — `{FrontendDir}` (a sibling of the BFF project) and the BFF project directory (`{BffDir}`, e.g. `MyApi/`, `src/{Base}.Web/` for a .NET BFF, or `src/{base}-api/` for a Node/Python BFF).
3. **Local development** — run the BFF (or external backend), then the frontend dev server; its proxy points at `{BACKEND_SERVER_URL}`.
4. **Backend note** — the dev origin must be registered as a B2C redirect URI; the BFF emits an auth cookie that flows through the same-origin dev-server proxy. If the policy-compliance check is enabled (Step 2e), note that the BFF must expose a `policy/validate` endpoint (configured with the connected Veracity service id) — the frontend redirects non-compliant users to accept terms / obtain a subscription.
5. **Skills applied** — add `veracity-auth-ui` (and `web-base-ui` and/or the backend skill used — `veracity-auth-net`, `veracity-auth-node`, or `veracity-auth-python`) to the skills table.

> If a `README.md` already exists, **merge** — do not overwrite.

## Verification checklist

- [ ] Phase 0 requirements settled (name confirmed; BFF strategy; Veracity API version when creating a BFF; show-services preference; design system & tech stack known — detected for an existing scaffold, or resolved and passed to `web-base-ui`) — using defaults where the user did not specify, asking only when ambiguous.
- [ ] Base name resolved and confirmed with stack-appropriate casing (PascalCase for .NET, kebab-case for Node/Python); frontend at `{FrontendDir}` — a **sibling** of the BFF project (e.g. `MyApi.Client/` next to `MyApi/`, or `{base}-client/` next to a Node/Python BFF), never nested inside the API project and never forced under a new `src/` folder when the BFF is at the repo root.
- [ ] Frontend scaffold resolved via one path: **existing scaffold reused** (auth detected its design system & stack) **or new welcome-page baseline created via `web-base-ui`** (default when none exists). The skill did NOT re-scaffold `package.json` / `tsconfig.json` / design-system setup when a scaffold already existed.
- [ ] BFF resolved via one path: existing reused (any stack) / explicit user-provided URL / **new BFF created via the `{BackendStack}` skill — `veracity-auth-net` (.NET, default), `veracity-auth-node`, or `veracity-auth-python`**. Only the .NET path creates a `.sln`/`.csproj`; Node/Python create no solution file. All expose `/auth` + `/auth/challenge`. A new web-app request must NOT end up with a frontend and no Veracity backend.
- [ ] Backend URL resolved from the stack-appropriate source (launchSettings.json for .NET, the Node/Python BFF port for those stacks, or user-provided); no `{BACKEND_SERVER_URL}` placeholder remains in `vite.config.ts`.
- [ ] Auth core (`api/`, `hooks/useAuth`, `App.tsx` shell) rendered into `{FrontendDir}`; `App.tsx` replaced the welcome shell; no `{{projectName}}` placeholder remains.
- [ ] `@vitejs/plugin-basic-ssl` added to the frontend `package.json` as a caret range; `<pm> install` succeeds.
- [ ] Final V3/V4 flags = BFF capability **AND** the user's show-services preference (Step 2d); `__V3_ENABLED__` / `__V4_ENABLED__` replaced with bare `true`/`false` in `App.tsx` (no placeholder remains). When enabled, `VeracityData` lists `/api/v1/veracity/v3/services` and/or `/api/v1/veracity/v4/me/applications`.
- [ ] Policy-compliance decided (Step 2e): `policy/validate` detected → included automatically (user informed), else asked (default yes). `__POLICY_ENABLED__` replaced with bare `true`/`false` in `App.tsx` and `{POLICY_VALIDATE_PATH}` replaced with the versioned path in `src/api/veracity.ts` (no placeholders remain). When enabled, a signed-in, non-compliant user is redirected to `redirectUrl`; when the backend lacks the endpoint but the user opted in, they were told it must be added separately.
- [ ] Login UI built with the frontend's design system (ShadCN default set up by `web-base-ui`, or a project-configured system). Presentation satisfies the `LoginExperience` contract — Sign in/out via `onSignIn`/`onSignOut` only, **no** direct auth-endpoint calls in the presentation, **no** global interceptor; auth core (`App.tsx`, `api/`, `hooks/`) left intact.
- [ ] Dev-server proxy **merged** into the existing `vite.config.ts` with all five routes; `/auth/challenge` before `/auth`; `secure: false`; the `react()` plugin and any design-system `@/` alias preserved. Dev server runs over **HTTPS** (`@vitejs/plugin-basic-ssl` + `server.https`).
- [ ] `/auth` checked on load; Sign in → `/auth/challenge?returnUrl=`; Sign out → `/signout`; 401 on `/api/me` → challenge; **no global interceptor**.
- [ ] `<pm> install` and `<pm> run build` succeed.
- [ ] README created/updated with skills applied.

## Assets & references

- [`assets/`](./assets/) — the **auth core + plain (fallback) login presentation**, rendered into the existing `{FrontendDir}`. The presentation files (`LoginExperience.tsx`, `LoginHeader.tsx`, `VeracityData.tsx`) are the reference implementation of the UI contract; other design systems replace them. `vite.config.ts` here is the **target shape** for merging the proxy + HTTPS into the scaffold's plain config — not a file to overwrite.
- [`../web-base-ui/`](../web-base-ui/) — the scaffolding skill this one delegates to when no frontend exists. It owns the baseline (`package.json` generation, TypeScript/Vite config, welcome page) and the design-system machinery, including the bundled [`vendor/shadcn/`](../web-base-ui/vendor/shadcn/).
