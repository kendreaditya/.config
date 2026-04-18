# Publishing to the Logseq Marketplace

The `logseq/marketplace` repo is a central registry. Plugins listed there appear in-app under **Plugins → Marketplace**. This is how most users install plugins.

## Prerequisites

1. **Plugin repo** on GitHub with a working `npm run build`.
2. **GitHub release** with the plugin zipped and attached as a release asset. The marketplace installer downloads this zip when users click "Install."
3. **Icon** — a 128x128 PNG or SVG in the plugin repo root (`icon.svg` recommended).
4. **README** — at minimum: what the plugin does, how to install, screenshots.

## Step 1: Cut a release

The starter template ships `.github/workflows/release.yml` that automates this. Push a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow:
- Runs `npm ci && npm run build`.
- Copies `dist/*` + a stripped `package.json` (no `scripts` or `devDependencies`) + `icon.svg` + `README.md` into a staging dir.
- Zips the staging dir into `<plugin-id>.zip`.
- Attaches the zip to a new GitHub Release via `softprops/action-gh-release@v2`.

Verify the release appears at `https://github.com/<user>/<repo>/releases` with the zip asset.

**Manual fallback** if you're not using the workflow:

```bash
npm run build
mkdir release
cp -r dist/* release/
# Strip dev metadata from package.json for the release copy.
node -e "const p=require('./package.json'); p.main='index.html'; delete p.scripts; delete p.devDependencies; require('fs').writeFileSync('release/package.json', JSON.stringify(p, null, 2))"
cp icon.svg README.md release/
cd release && zip -r ../<plugin-id>.zip .
```

Then `gh release create v0.1.0 <plugin-id>.zip --generate-notes`.

## Step 2: Fork `logseq/marketplace`

```bash
gh repo fork logseq/marketplace --clone
cd marketplace
git remote add upstream https://github.com/logseq/marketplace.git
git fetch upstream master
git checkout master && git reset --hard upstream/master
git checkout -b add-<plugin-id>
```

## Step 3: Add two files

Create `packages/<plugin-id>/manifest.json`:

```json
{
  "title": "My Plugin",
  "description": "One-sentence description — appears in the marketplace listing.",
  "author": "<github-username>",
  "repo": "<github-username>/<repo-name>",
  "icon": "icon.svg",
  "theme": false
}
```

Fields:
- `title` — display name (human-readable, Title Case).
- `description` — short pitch. Keep under ~120 chars for the listing card.
- `author` — your GitHub username (or "Name <email>" format).
- `repo` — `<user>/<repo>` — marketplace looks here for releases.
- `icon` — filename of the icon inside the release zip (not the marketplace dir). Must match what the release packaging copies in.
- `theme` — `false` for plugins, `true` for themes.
- `effect` — optional `true` if the plugin has side effects on the page body.

Copy the icon from your plugin repo:

```bash
cp ~/workspace/<plugin-name>/icon.svg packages/<plugin-id>/icon.svg
```

## Step 4: Open the PR

```bash
git add packages/<plugin-id>/manifest.json packages/<plugin-id>/icon.svg
git commit -m "Add <Plugin Title> plugin"
git push -u origin add-<plugin-id>

gh pr create --repo logseq/marketplace --base master --head <user>:add-<plugin-id> \
  --title "Add <Plugin Title> plugin" \
  --body "$(cat <<'EOF'
## Plugin: <Plugin Title>

<1-2 sentence pitch>

- **Repo:** https://github.com/<user>/<repo>
- **Release:** https://github.com/<user>/<repo>/releases/tag/v0.1.0 (zip attached)
- **Author:** @<user>

## Features

- <bullet>
- <bullet>

## Checklist

- [x] Release has a `<plugin-id>.zip` attached.
- [x] README explains what the plugin does and how to use it.
- [x] Screenshot / gif in README.
EOF
)"
```

## Step 5: Wait for review

Marketplace maintainers check:
- Release asset exists and unzips correctly.
- Icon displays.
- README is reasonable.
- No duplicated `id` with an existing plugin.

Typical turnaround: a few days to a week. Ping politely in the PR if it stalls past two weeks.

## Worked example

`logseq/marketplace#770` — Resurface plugin submission. Structure:

- `packages/resurface/manifest.json`
- `packages/resurface/icon.svg`

Manifest content:

```json
{
  "title": "Resurface",
  "description": "Passive re-exposure to your past. Injects a section above Linked References on every journal page showing one bullet block per rung of a time-decay ladder (1d, 3d, 1w, 2w, 1mo, 2mo, 6mo, 1y, 2y, 5y, 10y).",
  "author": "kendreaditya",
  "repo": "kendreaditya/resurface",
  "icon": "icon.svg",
  "theme": false
}
```

## After merge

Logseq's marketplace is rebuilt periodically. Once merged, your plugin appears in-app within a few hours. Every new GitHub release automatically becomes an available update — no marketplace PR needed.

## Updating an existing listing

Only reopen the marketplace PR if the `manifest.json` or `icon.svg` needs to change (title, description, icon, author field, repo URL). For code updates: just cut a new release with a higher version tag; the marketplace picks it up automatically.

Do not change the `logseq.id` in a released plugin — it breaks the upgrade path for existing users.
