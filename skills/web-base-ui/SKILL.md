---
name: web-base-ui
description: >-
  Scaffold a new frontend web project with the standard baseline every SPA needs: a React + Vite + TypeScript app (or a user-specified stack), a generated package.json with versions resolved from the npm registry, TypeScript + Vite config, a welcome page, and a selectable design system (ShadCN by default, or an existing/user-named design system such as MUI, Chakra, Ant, VUI, or a Google Stitch design.md). USE THIS SKILL whenever the user wants to create a new frontend project, bootstrap a React/Vite app, scaffold a web UI skeleton, set up a single-page app with sensible defaults, or needs a clean frontend baseline to build on. This skill does NOT add authentication or any backend integration — it produces an unauthenticated welcome-page baseline. For Veracity login (sign in/out, profile, services/applications) on top of a frontend, use the veracity-auth-ui skill, which calls this skill to scaffold first when no frontend project exists.
license: Apache-2.0
---

# Frontend Web UI Scaffolding (welcome-page baseline)

This skill creates a new **frontend SPA** with a production-sensible baseline — but **no authentication and no backend integration**. It is the foundation other skills build on (for example, `veracity-auth-ui` calls this skill to scaffold a frontend before adding Veracity login).

## What this skill produces

| Capability | Detail |
|------------|--------|
| App | React + Vite + TypeScript SPA (default), or a user-specified stack |
| Welcome page | A single welcome screen showing the project name |
| Dependencies | `package.json` **generated** at scaffold time with versions resolved from the npm registry as caret ranges |
| TypeScript | `tsconfig.json` (strict, `react-jsx`) |
| Dev server | Vite dev server over HTTPS (self-signed cert via `@vitejs/plugin-basic-ssl`), no backend proxy |
| Design system | Selectable: ShadCN by default; detected if the project already configures one; or a user-named system / Google Stitch `design.md` |
| Build gate | `<pm> install` + `<pm> run build` must succeed |

It does **not** add authentication, cookies, OIDC/JWT, backend proxies, or any Veracity-specific packages or endpoints. Those are layered on later by an auth skill. (The dev server does run over HTTPS with a self-signed cert — see the dev-server row above.)

## Phase 0: Gather requirements

Before scaffolding, settle the choices below. **Keep the happy path fast: apply the defaults and only ask the user when a decision is genuinely ambiguous, risky, or the user's request contradicts a default.** Record the answers — later phases consume them. When you do ask, prefer a single, focused multiple-choice question per topic.

> **Invoked by another skill?** When this skill is called by `veracity-auth-ui` (or another orchestrating skill), the caller passes the resolved **project name**, the target **frontend directory**, the **design system**, and the **tech stack**. Use those values directly and skip the resolution/questions below.

1. **Project name** — resolve a candidate using the rules in [Phase 1](#phase-1-resolve-project-name--layout), then **confirm it with the user** (or let them supply a different one). This is the one decision worth confirming even on the happy path, because it names every generated artifact.

2. **UI design system** — this skill is **design-system agnostic**: only the presentation layer varies. Resolve the design system in this order:
   1. **Detect a configured design system** — inspect the workspace for an existing one before defaulting: a component library or design-system package in a nearby `package.json` (e.g. `@veracity/vui`, `@mui/material`, `antd`, `@chakra-ui/react`, `@radix-ui/*`), a Tailwind/PostCSS config, a `components.json` (shadcn), or a design system the user names in their request. **If one is configured, use its components and patterns** — do not override it with the default.
   2. **Default to ShadCN** *(when none is configured)* — Tailwind + shadcn/ui primitives, driven by the **bundled** shadcn skill at [`vendor/shadcn/SKILL.md`](./vendor/shadcn/SKILL.md) (a redistributed MIT-licensed copy — see [its NOTICE](./vendor/shadcn/NOTICE.md); upstream: <https://github.com/shadcn-ui/ui/blob/main/skills/shadcn/SKILL.md>).
   3. **design.md** — build the UI to a Google Stitch `design.md` spec if the user asks. See <https://stitch.withgoogle.com/docs/design-md/overview>.
   4. **Other / user-provided** — any design system or component library the user names; fall back to the plain reference templates if none is workable.

   Only ask when the choice is genuinely ambiguous. See [UI design system](#ui-design-system--the-presentation-contract).

3. **Frontend tech stack** — default **React + Vite + TypeScript** (the stack the shipped `assets/` implement). Only deviate when the user explicitly asks for a different stack:
   - **React + Vite + TypeScript** *(default)* — render the `assets/` as-is.
   - **Vanilla JS/HTML** or an **alternative bundler** (e.g. webpack, Parcel, esbuild, plain `index.html`) — supported **when the user specifies it**. Reimplement the same baseline (a welcome page + dev server) in the chosen stack, using the React `assets/` as the reference. See [Alternative tech stacks](#alternative-tech-stacks-vanilla-jshtml--other-bundlers).
   Record the choice; it determines whether Phase 4 renders the React `assets/` or the agent generates equivalent files for the chosen stack.

## Phase 1: Resolve project name & layout

Derive the base project name (present it to the user for confirmation):

1. Existing `.sln` file → solution base name
2. Existing `.csproj` (under `src/` **or** at the repo root) → base name minus `.Web` / `.Api` / `.Client`
3. Git repository name → PascalCase
4. Current working directory name → PascalCase
5. **Fallback** — if none of the above yield a usable name (e.g. empty workspace, or only scratch/output directories), default to **`Web.Demo`**.

> **Never** derive the name from a scratch/output directory (`outputs/`, `temp/`); fall back to `Web.Demo` instead.

### Frontend location

By default the frontend is scaffolded into `src/{Base}.Client/`. When the caller (another skill) passes an explicit **frontend directory**, use that instead — for example a sibling of a backend project (`MyApi.Client/` next to `MyApi/`). The exact target is `{FrontendDir}`.

> **Safety**: if `{FrontendDir}` already exists and is non-empty, stop and ask before writing into it.

## Phase 4: Scaffold the frontend

> Phases 2 and 3 (backend / proxy resolution) intentionally do not exist in this skill — it produces a backend-less baseline. The phase numbering is kept aligned with `veracity-auth-ui` so the two skills read consistently.

The frontend target is `{FrontendDir}` as resolved in Phase 1.

> **Tech-stack branch (Phase 0 item 3).** The instructions below describe the **default React + Vite + TypeScript** path, which renders the shipped `assets/`. If the user chose an **alternative stack** (vanilla JS/HTML or a non-Vite bundler), do **not** render the React/Vite `assets/` verbatim — instead follow [Alternative tech stacks](#alternative-tech-stacks-vanilla-jshtml--other-bundlers) to generate stack-specific files that produce the same welcome-page baseline, and read the Phase 4a / 4b / 6 steps below as the *contract to satisfy* (dependency manifest, design-system UI, build gate) rather than literal Vite/TSX commands.

Render every file under [`assets/`](./assets/) into `{FrontendDir}`, applying these replacements. The `assets/` files are the **app shell + plain (fallback) presentation**; the presentation files may be replaced in [Phase 4b](#phase-4b-build-the-ui-with-the-chosen-design-system) by the chosen design system. The skill ships **no** `package.json` — it is **generated** in [Phase 4a](#phase-4a-generate-packagejson-resolve-versions-at-scaffold-time) from the dependency manifest with versions resolved at scaffold time.

| Placeholder | Replace with |
|-------------|--------------|
| `{{projectName}}` | The base project name (e.g. `MyApp`) |

File mapping (template → target under `{FrontendDir}`). The **layer** column marks whether a file is the design-system-agnostic **shell** (always rendered as-is) or **presentation** (kept for the plain default; replaced for other design systems):

| Template (`assets/`) | Target | Layer |
|----------------------|--------|-------|
| _(none — `package.json` is **generated**, see [Phase 4a](#phase-4a-generate-packagejson-resolve-versions-at-scaffold-time))_ | `package.json` | shell |
| `tsconfig.json` | `tsconfig.json` | shell |
| `vite.config.ts` | `vite.config.ts` | shell |
| `index.html` | `index.html` | shell |
| `gitignore` | `.gitignore` (note the leading dot) | shell |
| `src/main.tsx` | `src/main.tsx` | shell |
| `src/App.tsx` | `src/App.tsx` | shell (keep as-is) |
| `src/vite-env.d.ts` | `src/vite-env.d.ts` | shell |
| `src/components/WelcomeExperience.tsx` | `src/components/WelcomeExperience.tsx` | presentation (UI contract) |
| `src/components/AppHeader.tsx` | `src/components/AppHeader.tsx` | presentation |

`{{projectName}}` appears in `index.html` and `App.tsx` (as a `PROJECT_NAME` constant), and is also written into the generated `package.json` `name` field (Phase 4a); the presentation receives it as a **prop**, so generated design-system files need no `{{projectName}}` substitution. After substitution, grep the output for any leftover `{{`.

> **TSX caveat**: in `App.tsx`, `{{projectName}}` is the value of a string constant (`const PROJECT_NAME = '{{projectName}}'`). Once replaced with plain text (e.g. `MyApp`) it is a valid string literal. Never leave the literal `{{projectName}}` in a `.tsx` file, or the build will fail.

## Phase 4a: Generate `package.json` (resolve versions at scaffold time)

The skill does **not** ship a static `package.json`. Instead it declares the dependencies below and you **generate** `package.json` into `{FrontendDir}` at scaffold time, resolving each version against the **npm registry**. This keeps new scaffolds on current packages without a skill update for every minor/patch release.

> The manifest below is the **default React + Vite + TypeScript** set. For an alternative stack (Phase 0 item 3), keep the same registry-resolution rule but swap the stack-specific entries (e.g. replace `vite` / `@vitejs/*` with the chosen bundler, and drop the React/`@types/react*` deps for a vanilla build) — see [Alternative tech stacks](#alternative-tech-stacks-vanilla-jshtml--other-bundlers).

### Dependency manifest

Each row gives the package, the allowed **major range**, whether it is a runtime or dev dependency, and its purpose. The **range** column is the constraint you must respect; the **ceiling** (where present) caps the major to avoid an accidental breaking bump.

| Package | Kind | Range | Ceiling | Purpose |
|---------|------|-------|---------|---------|
| `react` | runtime | `^19` | — | React runtime |
| `react-dom` | runtime | `^19` | — | React DOM renderer (keep major in lockstep with `react`) |
| `@types/react` | dev | `^19` | — | React type definitions (match the `react` major) |
| `@types/react-dom` | dev | `^19` | — | React DOM type definitions (match the `react` major) |
| `@vitejs/plugin-react` | dev | `^5` | — | Vite React plugin |
| `@vitejs/plugin-basic-ssl` | dev | `^2` | — | Self-signed certificate for the HTTPS dev server |
| `vite` | dev | `^7` | — | Dev server + bundler |
| `typescript` | dev | `>=5 <6` | `<6` | TypeScript compiler (pin major to avoid accidental TS breaking changes) |

> Add any **design-system** dependencies chosen in [Phase 4b](#phase-4b-build-the-ui-with-the-chosen-design-system) (e.g. for ShadCN: `tailwindcss`, `@tailwindcss/vite` — the Vite build plugin that actually compiles Tailwind, kept on the same major as `tailwindcss` — `class-variance-authority`, `clsx`, `tailwind-merge`, the relevant Radix packages) using the **same registry-resolution rule** — resolve their latest compatible version at scaffold time rather than pinning them in this skill.

### Non-dependency fields (carry these verbatim)

The generated `package.json` must also include:

```jsonc
{
  "name": "{{projectName}}",      // the resolved base project name (Phase 1)
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "engines": { "node": ">=20.0.0" },
  "scripts": {
    "start": "vite --open",
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  }
}
```

### How to resolve versions

For **every** package in the manifest (and any Phase 4b design-system deps):

1. **Query the npm registry** for the latest version that satisfies the declared **range** and **ceiling** — e.g. `npm view <pkg> versions --json` (pick the highest matching the constraint) or `npm view <pkg>@"<range>" version`. Respect any ceiling so a `typescript` resolve never crosses into the next disallowed major.
2. Write the resolved version as a **caret major range** — `"^<resolved>"` (e.g. `"^19.2.1"`) — into `dependencies` (runtime) or `devDependencies` (dev) so future patch/minor installs stay current.
3. **Fallback (registry unreachable):** emit the bare floor of the declared range, i.e. `^<major>.0.0` (e.g. `^19.0.0`, `^5.0.0`), so the file is still valid and installable.
4. Keep `react` / `react-dom` on the **same major**, and `@types/react*` aligned to the resolved `react` major, to avoid type/runtime mismatch.

The result must be a **valid, immediately installable** `package.json` — Phase 6 (`<pm> install`) is the gate that confirms the resolved versions install cleanly.

## UI design system & the presentation contract

The skill is **design-system agnostic**: only the **presentation** layer changes. Use whatever design system the project already has configured (detected in Phase 0 item 2); when none is configured, the default is the **bundled** ShadCN skill in [`vendor/shadcn/`](./vendor/shadcn/). Every presentation must satisfy the **UI contract**: it implements `src/components/WelcomeExperience.tsx`, a pure, prop-driven component with this shape (see the reference in [`assets/`](./assets/src/components/WelcomeExperience.tsx)):

```ts
export interface WelcomeExperienceProps {
  projectName: string
}
```

Contract rules every design-system implementation must follow:

- **Render the welcome baseline** — a header showing the project name and a welcome page body.
- **Stay presentation-only** — receive everything via props; do not fetch data or own application state.

## Phase 4b: Build the UI with the chosen design system

Using the design system chosen in **Phase 0 item 2**, produce the presentation files (`src/components/WelcomeExperience.tsx` and any sub-components/styles) to the contract above. **Do not touch the app shell** (`App.tsx`, `main.tsx`).

- **ShadCN** *(default when no design system is configured)* — set up shadcn/ui deterministically, then rebuild `WelcomeExperience` (and a restyled `AppHeader`) using shadcn primitives (e.g. `Button`, `Card`). Follow the **bundled** shadcn skill at [`vendor/shadcn/SKILL.md`](./vendor/shadcn/SKILL.md) (a redistributed MIT-licensed copy; do not depend on fetching it from the network). ShadCN needs config the plain shell does not ship, so add and verify it as a unit:
  - **Tailwind CSS with its build plugin wired into the bundler** and a global stylesheet imported from `main.tsx`. For **Tailwind v4 + Vite** (the default stack) this means registering the **`@tailwindcss/vite`** plugin in `vite.config.ts` (add it to the `plugins` array alongside `react()` / `basicSsl()`) and importing a global CSS file whose first line is `@import "tailwindcss";`. **Do not rely on `@import "tailwindcss"` alone** — without the `@tailwindcss/vite` plugin (or the `@tailwindcss/postcss` PostCSS plugin) Tailwind never runs, the `@theme` / `@tailwind` / `@utility` at-rules are emitted verbatim, and **no utility classes are generated**, so the app renders unstyled even though the build still succeeds.
  - `components.json`, `src/lib/utils.ts` (the `cn` helper), and the shadcn deps (`tailwindcss`, **`@tailwindcss/vite`** — the Vite build plugin, required so Tailwind actually compiles — `class-variance-authority`, `clsx`, `tailwind-merge`, the relevant Radix packages) — add these to the generated `package.json` using the same registry-resolution rule as [Phase 4a](#phase-4a-generate-packagejson-resolve-versions-at-scaffold-time) (resolve the latest compatible version at scaffold time, write a caret range). Keep `@tailwindcss/vite` on the **same major** as `tailwindcss`.
  - The `@/` path alias in **both** `tsconfig.json` (`baseUrl` + `paths`) **and** `vite.config.ts` (`resolve.alias`), kept consistent. Do not break the existing Vite `react` / `basicSsl` plugin config when editing `vite.config.ts`.
  - After setup, confirm `@/components/...` and `@/lib/utils` imports resolve and the build passes (Phase 6 is the hard gate). **The build succeeding is NOT sufficient on its own** — Tailwind can be silently skipped. Additionally verify Tailwind actually compiled: the build must emit **no** `lightningcss` / bundler warnings like `Unknown at rule: @theme` / `@tailwind` / `@utility` (those warnings mean the plugin is missing and utilities were not generated), and the emitted CSS must contain real utility declarations (e.g. grep the `dist/assets/*.css` for `display:flex` / `border-radius`, not just the raw `@tailwind` directive). If Tailwind was skipped, add the `@tailwindcss/vite` plugin and rebuild before proceeding.
- **design.md** — obtain or generate a Google Stitch `design.md` spec (<https://stitch.withgoogle.com/docs/design-md/overview>) and build the presentation to it, still satisfying the contract.
- **Configured / user-provided design system** — when Phase 0 item 2 detected a design system already configured in the project (VUI, MUI, Chakra, Ant, a custom library, etc.), build the presentation with **that** system's components and patterns instead of the ShadCN default. If it cannot be set up cleanly, fall back to the plain reference templates and tell the user.

> **Fallback:** if the chosen design-system setup fails to build and cannot be fixed quickly, revert the presentation to the plain `assets/` templates (which already satisfy the contract) so the app still builds, and inform the user.

## Alternative tech stacks (vanilla JS/HTML / other bundlers)

The default and primary stack is **React + Vite + TypeScript**, rendered from the shipped `assets/`. When the user explicitly chose a different stack in **Phase 0 item 3** (vanilla JS/HTML, or an alternative bundler such as webpack/Parcel/esbuild), reproduce the same welcome-page baseline in the chosen stack, using the React `assets/` as the reference:

- **Same welcome baseline** — a page that renders the project name and a welcome message.
- **`package.json`** — still generated per [Phase 4a](#phase-4a-generate-packagejson-resolve-versions-at-scaffold-time), but with the dependency/script set appropriate to the chosen stack (e.g. swap `vite`/`@vitejs/*` for the chosen bundler; drop React deps for a vanilla build), still resolving versions from the npm registry as caret ranges.
- **Build is still the hard gate** (Phase 6): the chosen stack's build/typecheck must pass. If the alternative stack cannot be made to build, fall back to the default React + Vite + TypeScript stack and inform the user.

## Phase 6: Install & verify (build only)

Confirm `package.json` was **generated** (Phase 4a) — the skill ships none — and that every dependency uses a caret range with no leftover `{{projectName}}` in the `name` field. Detect the package manager (lockfile → `packageManager` field → CLI availability → default `npm`). Install the design-system dependencies added in Phase 4b along with the base deps, then build:

```bash
cd {FrontendDir}
<pm> install
<pm> run build   # default stack: tsc && vite build — must succeed
```

> For an **alternative stack** (Phase 0 item 3), run that stack's build/typecheck instead (the `build` script generated in Phase 4a); it is the same hard gate.

> The build is the **hard gate**, especially for ShadCN (path aliases, Tailwind, `@/lib/utils`). If it fails and cannot be fixed quickly, apply the Phase 4b fallback (revert presentation to the plain templates) so the app builds.

> **Tailwind can pass the build while producing no styles.** A missing `@tailwindcss/vite` plugin does **not** fail `vite build` — it only emits `Unknown at rule: @theme/@tailwind/@utility` warnings and ships CSS with the directives uncompiled, so the running app looks unstyled. As part of Phase 6, treat those warnings as a **failure**: confirm the emitted `dist/assets/*.css` contains real utility declarations (e.g. `display:flex`, `border-radius`) and that the `@tailwindcss/vite` plugin is registered in `vite.config.ts`. Fix and rebuild before declaring the scaffold done.

## Phase 7: Update README

Create or update `README.md` in the repo root to document:

1. **Architecture** — React+Vite frontend (built with the chosen design system); a single welcome page.
2. **Projects** — `{FrontendDir}`.
3. **Local development** — run the frontend dev server (Vite by default, or the chosen bundler).
4. **Skills applied** — add `web-base-ui` to the skills table.

> If a `README.md` already exists, **merge** — do not overwrite.

## Verification checklist

- [ ] Phase 0 requirements settled (name confirmed; design system — **detected if configured, else ShadCN**; **tech stack** — React+Vite+TS default) — using defaults where the user did not specify, asking only when ambiguous.
- [ ] Base name resolved and confirmed; frontend created at `{FrontendDir}` (default `src/{Base}.Client/`, or a caller-supplied directory).
- [ ] Frontend scaffolded; no `{{projectName}}` placeholder remains.
- [ ] `package.json` **generated** (Phase 4a), not rendered from a static asset; the skill ships none. Every runtime/dev dependency uses a **caret major range** (e.g. `^19.x.y`) resolved from the npm registry within its declared constraint, `typescript` stays `<6`, and `<pm> install` succeeds without manual edits.
- [ ] UI built with the resolved design system — a **project-configured** system when one was detected (Phase 0 item 2), otherwise the **bundled ShadCN** default (`vendor/shadcn/`). Presentation satisfies the `WelcomeExperience` contract; app shell (`App.tsx`, `main.tsx`) left intact.
- [ ] For a ShadCN/Tailwind build: the **`@tailwindcss/vite`** plugin is in `package.json` **and** registered in `vite.config.ts`; the build emits **no** `Unknown at rule: @theme/@tailwind/@utility` warnings; and the emitted CSS contains real utility declarations (Tailwind actually compiled — the app is styled, not just building).
- [ ] Tech stack recorded (Phase 0 item 3): default **React + Vite + TypeScript**, or the user-specified vanilla JS/HTML / alternative bundler.
- [ ] No authentication or backend integration added (no proxy, no auth packages). The HTTPS dev cert (`@vitejs/plugin-basic-ssl`) is part of the baseline.
- [ ] `<pm> install` and `<pm> run build` succeed.
- [ ] README created/updated with skills applied.

## Assets & references

- [`assets/`](./assets/) — the app shell + plain (fallback) presentation, rendered into `{FrontendDir}`. The presentation files (`WelcomeExperience.tsx`, `AppHeader.tsx`) are the reference implementation of the UI contract; other design systems replace them.
- [`vendor/shadcn/`](./vendor/shadcn/) — a **redistributed, MIT-licensed** copy of the upstream shadcn skill, used as the default design system when none is configured. See [`NOTICE.md`](./vendor/shadcn/NOTICE.md) for provenance/license and [`UPDATING.md`](./vendor/shadcn/UPDATING.md) for the repeatable refresh process.
