# Raycast config

Version-controlled Raycast settings. Lets you sync hotkeys / aliases /
snippets across Macs without paying for Raycast Pro's cloud sync.

## Files

| File                 | Purpose                                                        | Tracked in git? |
| -------------------- | -------------------------------------------------------------- | --------------- |
| `settings.json`      | Human-readable source of truth (hotkeys, aliases, snippets, extensions) | ✅ yes          |
| `build-rayconfig.sh` | Converts `settings.json` → importable `Raycast.rayconfig`      | ✅ yes          |
| `build-rayconfig.jq` | jq filter that reshapes `settings.json` into Raycast's internal schema | ✅ yes          |
| `Raycast.rayconfig`  | Generated importable file (or original encrypted export)       | ❌ gitignored   |
| `extensions/`        | Raycast's own installed extension code — DO NOT touch          | ❌ gitignored   |
| `ai/`                | Raycast-owned, empty                                           | ❌ gitignored   |

The gitignore rule lives in `~/.config/.gitignore` as
`raycast/*` + `!raycast/settings.json` (and the build scripts).

## Why this exists

Raycast stores settings in encrypted SQLite databases under
`~/Library/Application Support/com.raycast.macos/`. There is no plaintext
config file to symlink, and cloud sync requires a paid Pro subscription.
The `.rayconfig` export format is the only escape hatch for portable
backups, but it's an opaque blob — useless for diffing what changed.

This folder solves both:

1. **`settings.json` is the source of truth** — diffable, editable, committed.
2. **`build-rayconfig.sh` rebuilds an importable `.rayconfig` from it** — so
   you can restore on any Mac via Raycast's "Import Settings & Data".

## Workflow

### Export (Raycast → settings.json)

When you change something in Raycast and want to capture it:

1. Raycast → Settings → "Export Settings & Data" → save to `~/Downloads/`
2. Decrypt the export (default Raycast password is your "Export Passphrase"
   from Settings → Raycast):
   ```bash
   openssl enc -d -aes-256-cbc -nosalt \
     -in ~/Downloads/Raycast\ *.rayconfig \
     -k 'YOUR_EXPORT_PASSWORD' 2>/dev/null \
     | tail -c +17 | gunzip > /tmp/decrypted.json
   ```
3. Manually port the relevant changes into `settings.json` (the only stable
   keys are `hotkeys`, `aliases`, `snippets`, `extensions` — see schema below)
4. `git diff settings.json` → commit

### Import (settings.json → Raycast)

On a fresh Mac, or when restoring after a wipe:

```bash
~/.config/raycast/build-rayconfig.sh   # writes ./Raycast.rayconfig
```

Then in Raycast: **Import Settings & Data** → pick `Raycast.rayconfig` →
done. No password required (see "Format" below).

After import, manually install the extensions listed in
`settings.json -> extensions[]` from the Raycast Store. The build script
doesn't auto-install them — extensions are apps, not config.

## Format (reverse-engineered)

Raycast `.rayconfig` exports look like this:

```
[16-byte random header] + [gzip(JSON)]   — then optionally AES-256-CBC encrypted
```

But Raycast's IMPORT parser is far more lenient than its export format:

- ✅ Encryption is **optional** — Raycast accepts plain gzipped JSON
- ✅ The 16-byte header is **optional** — Raycast accepts bare gzip
- ✅ Most `builtin_package_*` keys are **optional** — only `rootSearch` and
     `snippets` are needed for hotkeys/aliases/snippets

So `build-rayconfig.sh` writes the bare minimum: a single `gzip -nc` of the
internal-schema JSON. No encryption, no header, no password. Verified
working 2026-04-17 against Raycast 1.104.x.

Format details cribbed from:
<https://gist.github.com/jeremy-code/50117d5b4f29e04fcbbb1f55e301b893>

## What's NOT tracked

By design, `settings.json` skips:

- **Quicklinks** — only had 2 disabled defaults; not worth the noise
- **Disabled commands** — 33 builtin UI toggles; generic, not personal
- **User activity / telemetry** — 4.3 MB of every command run, every AI chat
- **Extension internals** — `prefs`, `tokenSets`, `commands` per extension
  (the extensions list in `settings.json` is **name-only reference**)
- **Onboarding flags, frecency timestamps, anonymous IDs** — runtime state

If you ever need full fidelity, re-export from Raycast and keep the encrypted
`.rayconfig` as a local-only backup (it's already gitignored).
