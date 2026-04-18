---
name: logseq-plugin
description: Bootstrap, author, debug, and publish Logseq plugins. Use when the user asks to create a logseq plugin, build a logseq plugin, scaffold a logseq plugin, add a feature to an existing Logseq plugin, fix a Logseq plugin bug, publish a plugin to the Logseq marketplace, or when working in a repo that contains a `logseq` field in package.json. Triggers on phrases "create a logseq plugin", "build a logseq plugin", "scaffold a logseq plugin", "new logseq plugin", "logseq plugin development", "logseq plugin API", "publish to logseq marketplace", "logseq plugin bug", "@logseq/libs".
---

# Logseq Plugin

Author Logseq Desktop plugins using `@logseq/libs` + Vite + TypeScript. Covers scaffolding a new plugin, extending an existing one, navigating Logseq's plugin API, avoiding well-known gotchas, and publishing to the `logseq/marketplace` registry.

## Anti-triggers

Do NOT use this skill for:
- **Using Logseq itself** (not writing plugins) — user questions about Logseq syntax, features, or configuration as an end user.
- **Logseq themes** — themes ship CSS only; use standard CSS / theme authoring workflows.
- **Non-plugin Logseq integrations** — Logseq HTTP API, mobile bindings, database introspection outside a plugin context.

## Decision tree

1. **New plugin?** → §1 Scaffold.
2. **Existing plugin repo** (has `logseq` field in `package.json`)? → §2 Extend.
3. **Debugging weird DOM / query / render behavior?** → §3 Gotchas, then `references/gotchas.md`.
4. **Publishing to the marketplace?** → §4 Publish.

## §1. Scaffold a new plugin

Copy `assets/starter/` into the target directory, rename, and install.

```bash
cp -R ~/.config/claude/skills/logseq-plugin/assets/starter/ ~/workspace/<plugin-name>
cd ~/workspace/<plugin-name>
```

Edit `package.json`:
- `name` — match the directory name.
- `description` — one-line summary.
- `repository.url` — GitHub URL.
- `logseq.id` — same as `name` (lowercase, hyphen-separated). This is the plugin's marketplace identifier.
- `logseq.title` — user-facing display name.

Edit `src/main.ts`: replace the placeholder `style.key` and log label with the plugin id.

Edit `README.md`: explain what it does and how to load.

Install + build:

```bash
npm install
npm run build           # or: npm run dev  (vite build --watch)
```

Load in Logseq Desktop: **Settings → Advanced → Developer mode** (enable) → top-right ⋯ → **Plugins → Load unpacked plugin** → select the plugin folder. Reload from the Plugins page after each rebuild.

The starter boots a valid plugin (empty `provideStyle`, one console log). Pick the architecture you need — the two canonical shapes are documented with code sketches in `references/architecture.md`:

- **Journal-page injection** (like Resurface): `MutationObserver` on body, read date from DOM title, inject HTML next to `.references`.
- **Sidebar / header UI** (like File Explorer): `provideUI` into `.cp__header` or `.left-sidebar-inner`, with `provideModel` for click routing via `data-on-click`.

## §2. Extend an existing plugin

When dropped into an unfamiliar plugin repo:

1. **Read `CLAUDE.md` first if present** — it contains the project's onboarding order and gotchas. Follow the order.
2. **Check `package.json`** — `logseq` field (id, title), `main` field (entry HTML), build scripts (likely `vite build`).
3. **Map the entry pipeline** — find `logseq.ready(main)` (usually `src/main.ts`). Trace what `main()` does: `provideStyle` → `state.load` → first run/render → listeners (`onRouteChanged`, `MutationObserver`, `onCurrentGraphChanged`, `DB.onChanged`).
4. **Identify the injection surface** — DOM injection via `.insertAdjacentElement`, `logseq.provideUI` (templated HTML slot), or `logseq.provideModel` (click routing).
5. **Check state** — `src/state.ts` typically has a singleton with a `Persisted` type, `load()`/`dump()` methods, and loose transient fields. Anything in `dump()` gets persisted via `logseq.updateSettings`; everything else is per-session.
6. **Add the feature** — follow existing patterns rather than importing new ones. If adding a slash command, follow `logseq.Editor.registerSlashCommand`; if adding a sidebar panel, follow `provideUI` with a fresh `key`.

See `references/apis.md` for the full API cheatsheet.

## §3. Top gotchas (quick-hit)

Each of these ate real hours. Expanded explanations in `references/gotchas.md`.

1. **Date comes from the DOM title, not `Editor.getCurrentPage()`.** `getCurrentPage()` returns `null` on fresh journal mounts. Read `.journal-title h1.title` with a `h1.title` fallback, and parse both ISO (`2026-04-17`) and pretty (`Apr 17th, 2026`) formats.
2. **`logseq.DB.datascriptQuery` returns flat, namespace-stripped pull keys.** A pull of `:block/uuid` comes back as `pull.uuid`, not `pull["block/uuid"]`. Nested pulls: `pull.page.id`, not `pull["block/page"]["db/id"]`. Always use a defensive reader with both shapes as fallbacks. Log a sample pull at startup (`diagnoseSchema`) — the shape is right there.
3. **`.references` is a DOM sibling of `.journal.page`, not a child.** Rooting `querySelector('.references')` at the journal page element will miss it. Try the journal root, then fall back to `document.querySelector`. Journal-root selectors vary across builds: try `.journal-item`, `.journal.page`, `.page.is-journals`, `.page-inner-wrap.is-journals` in order.
4. **Chevron placement needs inline `margin-left: -30px`.** External CSS loses specificity fights with themes, and `.block-control` collapses to zero width without a flex-parent context. Set `style="width:14px;height:16px;margin-left:-30px"` inline on the `<a class="block-control">` — do not "clean up" this inline style.
5. **Clear transient state on every render.** Sets like `collapsedCards` accumulate stale uuids as the user navigates. Persist only what users explicitly want to outlast a session (typically: section-level collapse, user preferences). Call `state.collapsedCards.clear()` at the top of `run()`.
6. **Plugin HTML lives outside Logseq's React tree** — you cannot make injected blocks inline-editable. Fallback: on click, call `Editor.scrollToBlockInPage(uuid)` to jump to the native editable rendering on the source page.
7. **`.ls-foldable-*` classes are master-only.** Stable Logseq 0.10.x uses a simpler foldable shape (`<div class="content"><div class="flex-1 flex-row foldable-title">...`). Target 0.10 unless you know the user is on a DB-based beta.

## §4. Publish to the marketplace

Full step-by-step in `references/marketplace.md`. The happy path:

1. **Cut a GitHub release.** The starter ships `.github/workflows/release.yml` — push a `v*` tag (e.g. `git tag v0.1.0 && git push --tags`) and it builds + zips `dist/ + package.json + icon.svg + README.md` into `<plugin-id>.zip` attached to the Release.
2. **Fork `logseq/marketplace`**, branch `add-<plugin-id>`.
3. **Add two files** at `packages/<plugin-id>/`:
   - `manifest.json` — `{ title, description, author, repo, icon: "icon.svg", theme: false }`
   - `icon.svg` — 128x128 recommended.
4. **Open a PR** against `logseq/marketplace:master` with a short description, repo link, feature list. A reviewer will merge if the release zip is present.

## §5. Build + load + reload workflow

```bash
npm run dev          # vite build --watch — rebuilds on file change
```

In Logseq Desktop: Plugins page → find your plugin → click the reload icon. This re-runs `main()` with the fresh bundle without restarting Logseq.

Console logs from plugins appear in Logseq's main DevTools (`Cmd+Opt+I` / `Ctrl+Shift+I`). Always prefix logs with `[<plugin-id>]` for grepping.

## File map

- `SKILL.md` — this file.
- `references/architecture.md` — bootstrap lifecycle, state pattern, journal-injection vs sidebar-UI archetypes with code sketches, delegated click handler pattern.
- `references/apis.md` — cheatsheet of `logseq.*` APIs grouped by namespace, each with a real call site.
- `references/datascript.md` — pull-query shape, namespace-stripped keys, defensive reader, DB-graph vs file-graph fallbacks.
- `references/gotchas.md` — expanded debugging notes for §3 plus more.
- `references/marketplace.md` — full publication flow with worked example.
- `assets/starter/` — copy-and-adapt plugin skeleton.

## Commit discipline

When editing an existing plugin:
- Always read the relevant doc (project `CLAUDE.md`, `docs/architecture.md`, `docs/debugging-notes.md`) before modifying a pipeline.
- Test `npm run build` before committing. TypeScript errors in a Logseq plugin are easy to miss because the runtime is tolerant.
- Keep the `logseq.id` stable once published — changing it breaks upgrade paths for existing installs.
- Do not commit `dist/` (gitignored in the starter).
