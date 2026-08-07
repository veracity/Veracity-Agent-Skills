# Updating the bundled shadcn/ui skill

The `vendor/shadcn/` directory is a **redistributed copy** of the upstream `shadcn`
agent skill (MIT licensed). Because it is a snapshot, it must be refreshed
periodically so teams scaffolding with `veracity-auth-ui` get current shadcn
guidance. This is a documented, repeatable process — run it whenever upstream changes
materially (or on a regular cadence).

## Source of truth

- Repo: <https://github.com/shadcn-ui/ui>
- Skill path: `skills/shadcn/`
- License: `LICENSE.md` (repo root)

## Steps

1. **Check for upstream changes** — compare the latest commit that touches the skill
   path against the `Vendored from commit` recorded in [`NOTICE.md`](./NOTICE.md):

   ```bash
   curl -s "https://api.github.com/repos/shadcn-ui/ui/commits?path=skills/shadcn&sha=main&per_page=1" \
     | grep -E '"sha"|"date"'
   ```

   If the SHA matches `NOTICE.md`, the bundle is current — stop.

2. **Re-download the files** from `main` (raw URLs) into this directory, overwriting
   the existing copies. Keep the file set in sync with upstream — add any new files
   the upstream `SKILL.md` starts referencing, and remove ones it drops:

   ```bash
   base="https://raw.githubusercontent.com/shadcn-ui/ui/main/skills/shadcn"
   for f in SKILL.md cli.md customization.md mcp.md registry.md; do
     curl -sSL "$base/$f" -o "$f"
   done
   for f in base-vs-radix.md composition.md forms.md icons.md styling.md; do
     curl -sSL "$base/rules/$f" -o "rules/$f"
   done
   curl -sSL "https://raw.githubusercontent.com/shadcn-ui/ui/main/LICENSE.md" -o LICENSE
   ```

3. **Verify the bundle is self-contained** — confirm every relative markdown link in
   the re-downloaded **upstream** files still resolves inside `vendor/shadcn/`. Check
   only the upstream-copied files (not `NOTICE.md` / `UPDATING.md`), and treat
   `#anchor` suffixes and the non-`.md` `LICENSE` target as valid:

   ```bash
   # List every relative link target; manually confirm each path exists in this dir.
   grep -rnoE '\]\((\./|\.\./)[^)]+\)' \
     SKILL.md cli.md customization.md mcp.md registry.md rules/ \
     | sed -E 's/.*\]\(([^)#]+)(#[^)]*)?\)/\1/' | sort -u
   ```

   Every listed path must exist under `vendor/shadcn/`. If a new referenced file
   appears, vendor it too (step 2) and update the file list in `NOTICE.md`.

4. **Confirm the license is unchanged** — verify `LICENSE` is still MIT. If upstream
   changes its license, **stop** and escalate; do not redistribute under new terms
   without review.

5. **Update provenance** — edit [`NOTICE.md`](./NOTICE.md): set `Vendored from commit`
   to the new SHA, `Commit date`, and `Vendored on` to today. Note any modifications
   (there should be none beyond `NOTICE.md` / `UPDATING.md`).

6. **Sanity check the consuming skill** — re-read `veracity-auth-ui/SKILL.md`
   Phase 4b to confirm the ShadCN setup steps (Tailwind/PostCSS, `components.json`,
   `cn` helper, `@/` alias) still match upstream guidance; adjust if the upstream
   workflow changed.

7. **Commit** the refreshed bundle and the updated `NOTICE.md` in a single change so
   the provenance and the files stay consistent.
