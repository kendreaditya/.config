---
name: disk-hygiene
description: macOS disk cleanup, cache pruning, stale file detection, and Downloads triage. TRIGGERS - disk space, cleanup, disk usage, stale files, cache clean, brew cleanup, forgotten files, Downloads cleanup, free space, storage, dust, dua, gdu, ncdu.
allowed-tools: Read, Bash, Write, Glob, Grep, AskUserQuestion
---

# Disk Hygiene

> Audit disk usage, clean developer caches, find forgotten large files, and triage Downloads on macOS.

## When to Use This Skill

Use this skill when:

- User asks about disk space, storage, or cleanup
- System is running low on free space
- User wants to find old/forgotten large files
- User wants to clean developer caches (brew, uv, pip, npm, cargo)
- User wants to triage their Downloads folder
- User asks about disk analysis tools (dust, dua, gdu, ncdu)

## TodoWrite Task Templates

### Template A - Full Disk Audit

```
1. Run disk overview (df -h / and major directories)
2. Audit developer caches (uv, brew, pip, npm, cargo, rustup, Docker)
3. Scan for forgotten large files (>50MB, not accessed in 180+ days)
4. Present findings with AskUserQuestion for cleanup choices
5. Execute selected cleanups
6. Report space reclaimed
```

### Template B - Cache Cleanup Only

```
1. Measure current cache sizes
2. Run safe cache cleanups (brew, uv, pip, npm)
3. Report space reclaimed
```

### Template C - Downloads Triage

```
1. List Downloads contents with dates and sizes
2. Categorize into groups (media, dev artifacts, personal docs, misc)
3. Present AskUserQuestion multi-select for deletion/move
4. Execute selected actions
```

### Template D - Forgotten File Hunt

```
1. Scan home directory for large files not accessed in 180+ days
2. Group by location and type (media, ISOs, dev artifacts, documents)
3. Present findings sorted by size
4. Offer cleanup options via AskUserQuestion
```

---

## Phase 1 - Disk Overview

Get the lay of the land before diving into specifics.

```bash
/usr/bin/env bash << 'OVERVIEW_EOF'
echo "=== Disk Overview ==="
df -h /

echo ""
echo "=== Major Directories ==="
du -sh ~/Library/Caches ~/Library/Logs ~/Library/Application\ Support \
  ~/.Trash ~/Downloads ~/Documents ~/Desktop ~/Movies ~/Music ~/Pictures \
  2>/dev/null | sort -rh

echo ""
echo "=== Developer Tool Caches ==="
du -sh ~/.docker ~/.npm ~/.cargo ~/.rustup ~/.local ~/.cache \
  ~/.conda ~/.pyenv ~/.local/share/mise 2>/dev/null | sort -rh
OVERVIEW_EOF
```

## Phase 2 - Cache Audit & Cleanup

### Cache Size Reference

| Cache       | Location                            | Typical Size | Clean Command                             |
| ----------- | ----------------------------------- | ------------ | ----------------------------------------- |
| uv          | `~/Library/Caches/uv/`              | 5-15 GB      | `uv cache clean`                          |
| Homebrew    | `~/Library/Caches/Homebrew/`        | 3-10 GB      | `brew cleanup --prune=all`                |
| pip         | `~/Library/Caches/pip/`             | 0.5-2 GB     | `pip cache purge`                         |
| npm         | `~/.npm/_cacache/`                  | 0.5-2 GB     | `npm cache clean --force`                 |
| cargo       | `~/.cargo/registry/cache/`          | 1-5 GB       | `cargo cache -a` (needs cargo-cache)      |
| rustup      | `~/.rustup/toolchains/`             | 2-8 GB       | `rustup toolchain remove <old>`           |
| Docker      | Docker.app                          | 5-30 GB      | `docker system prune -a`                  |
| Playwright  | `~/Library/Caches/ms-playwright/`   | 0.5-2 GB     | `npx playwright uninstall`                |
| sccache     | `~/Library/Caches/Mozilla.sccache/` | 1-3 GB       | `rm -rf ~/Library/Caches/Mozilla.sccache` |
| huggingface | `~/.cache/huggingface/`             | 1-10 GB      | `rm -rf ~/.cache/huggingface/hub/<model>` |
| mediaanalysisd | `~/Library/Containers/com.apple.mediaanalysisd/Data/Library/Caches/` | 5-140 GB | see below — known macOS Sequoia bug |
| pyppeteer   | `~/Library/Application Support/pyppeteer/` | 0.5-2 GB | `rm -rf ~/Library/Application\ Support/pyppeteer` |
| Chrome OptGuideOnDeviceModel | `~/Library/Application Support/Google/Chrome/OptGuideOnDeviceModel/` | 4 GB | `rm -rf ~/Library/Application\ Support/Google/Chrome/OptGuideOnDeviceModel` |
| Xcode DerivedData | `~/Library/Developer/Xcode/DerivedData/` | 2-20 GB | `rm -rf ~/Library/Developer/Xcode/DerivedData` |
| Xcode Previews | `~/Library/Developer/Xcode/UserData/Previews/` | 1-5 GB | `rm -rf ~/Library/Developer/Xcode/UserData/Previews` |
| iOS Simulator caches | `~/Library/Developer/CoreSimulator/Caches/` | 3-10 GB | `xcrun simctl delete unavailable` |
| Android AVD | `~/.android/avd/` | 5-15 GB | delete unused AVDs via Android Studio or `rm -rf ~/.android/avd/<name>` |
| Android SDK system-images | `~/Library/Android/sdk/system-images/` | 2-8 GB | remove unused API levels via Android Studio SDK Manager |
| Warp autoupdate | `~/Library/Application Support/dev.warp.Warp-Stable/autoupdate/` | 200-500 MB | `rm -rf ~/Library/Application\ Support/dev.warp.Warp-Stable/autoupdate` |

### Safe Cleanup Commands (Always Re-downloadable)

```bash
/usr/bin/env bash << 'CACHE_CLEAN_EOF'
set -euo pipefail

echo "=== Measuring current cache sizes ==="
echo "uv:       $(du -sh ~/Library/Caches/uv/ 2>/dev/null | cut -f1 || echo 'N/A')"
echo "Homebrew: $(du -sh ~/Library/Caches/Homebrew/ 2>/dev/null | cut -f1 || echo 'N/A')"
echo "pip:      $(du -sh ~/Library/Caches/pip/ 2>/dev/null | cut -f1 || echo 'N/A')"
echo "npm:      $(du -sh ~/.npm/_cacache/ 2>/dev/null | cut -f1 || echo 'N/A')"

echo ""
echo "=== Cleaning ==="
brew cleanup --prune=all 2>&1 | tail -3
uv cache clean --force 2>&1
pip cache purge 2>&1
npm cache clean --force 2>&1
CACHE_CLEAN_EOF
```

### Troubleshooting Cache Cleanup

| Issue                               | Cause                      | Solution                                  |
| ----------------------------------- | -------------------------- | ----------------------------------------- |
| `uv cache` lock held                | Another uv process running | Use `uv cache clean --force`              |
| `brew cleanup` skips formulae       | Linked but not latest      | Safe to ignore, or `brew reinstall <pkg>` |
| `pip cache purge` permission denied | System pip vs user pip     | Use `python -m pip cache purge`           |
| Docker not running                  | Docker Desktop not started | Start Docker.app first, or skip           |

## Phase 3 - Forgotten File Detection

Find large files that have not been accessed in 180+ days.

```bash
/usr/bin/env bash << 'STALE_EOF'
echo "=== Large forgotten files (>50MB, untouched 180+ days) ==="
echo ""

# Scan home directory (excluding Library, node_modules, .git, hidden dirs)
find "$HOME" -maxdepth 4 \
  -not -path '*/\.*' \
  -not -path '*/Library/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -type f -atime +180 -size +50M 2>/dev/null | \
while read -r f; do
  mod_date=$(stat -f '%Sm' -t '%Y-%m-%d' "$f" 2>/dev/null)
  size=$(du -sh "$f" 2>/dev/null | cut -f1)
  echo "${mod_date} ${size} ${f}"
done | sort

echo ""
echo "=== Documents & Desktop (>10MB, untouched 180+ days) ==="
find "$HOME/Documents" "$HOME/Desktop" \
  -type f -atime +180 -size +10M 2>/dev/null | \
while read -r f; do
  mod_date=$(stat -f '%Sm' -t '%Y-%m-%d' "$f" 2>/dev/null)
  size=$(du -sh "$f" 2>/dev/null | cut -f1)
  echo "${mod_date} ${size} ${f}"
done | sort
STALE_EOF
```

### Common Forgotten File Types

| Type                  | Typical Location     | Example                      |
| --------------------- | -------------------- | ---------------------------- |
| Windows/Linux ISOs    | Documents, Downloads | `.iso` files from VM setup   |
| CapCut/iMovie exports | Movies/              | Large `.mp4` renders         |
| Phone video transfers | Pictures/, DCIM/     | `.MOV` files from iPhone     |
| Old Zoom recordings   | Documents/           | `.aac`, `.mp4` from meetings |
| Orphaned downloads    | Documents/           | `CFNetworkDownload_*.mp4`    |
| Screen recordings     | Documents/, Desktop/ | Capto/QuickTime `.mov`       |

## Phase 4 - Downloads Triage

Use AskUserQuestion with multi-select to let the user choose what to clean.

### Workflow

1. List all files in `~/Downloads` with dates and sizes
2. Categorize into logical groups
3. Present AskUserQuestion with categories as multi-select options
4. Offer personal/sensitive PDFs separately (keep, move to Documents, or delete)
5. Execute selected actions

### Categorization Pattern

```bash
/usr/bin/env bash << 'DL_LIST_EOF'
echo "=== Downloads by date and size ==="
find "$HOME/Downloads" -maxdepth 1 \( -type f -o -type d \) ! -path "$HOME/Downloads" | \
while read -r f; do
  mod_date=$(stat -f '%Sm' -t '%Y-%m-%d' "$f" 2>/dev/null)
  size=$(du -sh "$f" 2>/dev/null | cut -f1)
  echo "${mod_date} ${size} $(basename "$f")"
done | sort
DL_LIST_EOF
```

### AskUserQuestion Template

When presenting Downloads cleanup options, use this pattern:

- **Question 1** (multiSelect: true) - "Which items in ~/Downloads do you want to delete?"
  - Group by type: movie files (with total size), old PDFs/docs, dev artifacts, app exports
- **Question 2** (multiSelect: false) - "What about personal/sensitive PDFs?"
  - Options: Keep all, Move to Documents, Delete (already have copies)
- **Question 3** (multiSelect: false) - "Ongoing cleanup tool preference?"
  - Options: dust + dua-cli, Hazel automation, custom launchd script

## Disk Analysis Tools Reference

### Comparison (Benchmarked on ~632GB home directory, Apple Silicon)

| Tool        | Wall Time | CPU Usage            | Interactive Delete       | Install                |
| ----------- | --------- | -------------------- | ------------------------ | ---------------------- |
| **dust**    | **20.4s** | 637% (parallel)      | No (view only)           | `brew install dust`    |
| **gdu-go**  | 28.8s     | 845% (very parallel) | Yes (TUI)                | `brew install gdu`     |
| **dua-cli** | 37.1s     | 237% (moderate)      | Yes (staged safe delete) | `brew install dua-cli` |
| **ncdu**    | 96.6s     | 43% (single-thread)  | Yes (TUI)                | `brew install ncdu`    |

### Recommended Combo

- **`dust`** for quick "where is my space going?" - fastest scanner, tree output
- **`dua i`** or **`gdu-go`** for interactive exploration with deletion

### Quick Usage

```bash
# dust - instant tree overview
dust -d 2 ~              # depth 2
dust -r ~/Library         # reverse sort (smallest first)

# dua - interactive TUI with safe deletion
dua i ~                   # navigate, mark, delete with confirmation

# gdu-go - ncdu-like TUI, fast on SSDs
gdu-go ~                  # full TUI with delete support
gdu-go -n ~              # non-interactive (for scripting/benchmarks)
```

### Install All Tools

```bash
brew install dust dua-cli gdu
```

**Note**: gdu installs as `gdu-go` to avoid conflict with coreutils.

## Quick Wins Summary

Ordered by typical space reclaimed (highest first):

| Action                          | Typical Savings | Risk                       | Command                             |
| ------------------------------- | --------------- | -------------------------- | ----------------------------------- |
| `uv cache clean`                | 5-15 GB         | None (re-downloads)        | `uv cache clean --force`            |
| `brew cleanup --prune=all`      | 3-10 GB         | None (re-downloads)        | `brew cleanup --prune=all`          |
| Delete movie files in Downloads | 2-10 GB         | Check first                | Manual after AskUserQuestion        |
| `npm cache clean --force`       | 0.5-2 GB        | None (re-downloads)        | `npm cache clean --force`           |
| `pip cache purge`               | 0.5-2 GB        | None (re-downloads)        | `pip cache purge`                   |
| Prune old rustup toolchains     | 2-5 GB          | Keep current               | `rustup toolchain list` then remove |
| Docker system prune             | 5-30 GB         | Removes stopped containers | `docker system prune -a`            |
| Empty Trash                     | Variable        | Irreversible               | `rm -rf ~/.Trash/*`                 |

## Post-Change Checklist

After modifying this skill:

1. [ ] Cache commands tested on macOS (Apple Silicon)
2. [ ] Benchmark data still current (re-run if tools updated)
3. [ ] AskUserQuestion patterns match current tool API
4. [ ] All bash blocks use `/usr/bin/env bash << 'EOF'` wrapper
5. [ ] No hardcoded user paths (use `$HOME`)
6. [ ] Append changes to [evolution-log.md](./references/evolution-log.md)

## macOS System Bloat — Hidden Large Caches

### com.apple.mediaanalysisd (5–140 GB) — macOS Sequoia Bug

Apple's background ML service for Photos face/object detection. Known to grow unbounded in macOS Sequoia — some users report 50–140GB. Safe to clear; only analysis metadata is deleted, not photos.

```bash
# Do NOT use launchctl stop — exits with code 150
# Do NOT try to rm the container root — SIP-protected
# Only clear the cache subdirectory:
rm -rf ~/Library/Containers/com.apple.mediaanalysisd/Data/Library/Caches/com.apple.mediaanalysisd/
```

macOS will rebuild the cache gradually in the background. A restart helps reinitialize cleanly but is not required.

### Xcode / iOS Developer Bloat

```bash
# DerivedData — build artifacts, 100% safe, Xcode rebuilds on next build
rm -rf ~/Library/Developer/Xcode/DerivedData

# SwiftUI preview caches
rm -rf ~/Library/Developer/Xcode/UserData/Previews

# iOS Simulator dyld caches — Xcode rebuilds automatically
# Also removes unavailable/old simulator devices
xcrun simctl delete unavailable

# Check what simulator runtimes are installed
xcrun simctl runtime list
```

### ncdu Apparent vs Real Sizes

`ncdu`, `dust`, `dua`, and `du` all report **apparent sizes** by default, not actual disk blocks used. This matters for:
- **Google Drive stubs** — show full size, use 0 bytes (see Google Drive section)
- **Sparse files** — VM disk images (.img, .qcow2, .raw) often report 2-10x their actual usage
- **APFS clones** — shared blocks counted multiple times

Always verify with `du -sh` (actual) vs `ls -lh` (apparent) before assuming a file is eating disk.

### app bundles still on disk after uninstall

Uninstalling an app via drag-to-Trash only removes the `.app` bundle. App data remains in:
- `~/Library/Application Support/<AppName>`
- `~/Library/Containers/<bundle-id>`
- `~/Library/Preferences/<bundle-id>.plist`
- `~/Library/Caches/<bundle-id>`

After removing apps, scan these locations for orphaned data:

```bash
/usr/bin/env bash << 'ORPHAN_EOF'
echo "=== Potentially orphaned app data (>100MB, app not in /Applications) ==="
for dir in ~/Library/Application\ Support/*/; do
  app=$(basename "$dir")
  size=$(du -sm "$dir" 2>/dev/null | cut -f1)
  if [ "${size:-0}" -gt 100 ]; then
    # Check if matching .app exists
    if ! ls /Applications/ | grep -qi "$app" 2>/dev/null; then
      echo "  ${size}MB  $dir"
    fi
  fi
done
ORPHAN_EOF
```

Browser-based apps (Chromium derivatives) are especially prone to leaving behind large `OptGuideOnDeviceModel` folders and multi-profile data.

### Chrome / Chromium-based Bloat

Each Chromium-based browser (Chrome, Edge, Brave, Arc, Comet, Cursor, Windsurf) installs its own copy of:
- `OptGuideOnDeviceModel/` — Chrome's on-device AI weights (~4GB per browser)
- Browser extensions with embedded ML models (~30MB per profile per extension version)

Find and remove all copies:
```bash
# Find all OptGuideOnDeviceModel copies across all browsers
find ~/Library/Application\ Support ~/.gemini -name "OptGuideOnDeviceModel" -type d 2>/dev/null \
  | xargs -I{} du -sh {}

# Remove all copies (Chrome will re-download when needed)
find ~/Library/Application\ Support ~/.gemini -name "OptGuideOnDeviceModel" -type d 2>/dev/null \
  | xargs rm -rf
```

---

## Google Drive File Stream — Stub vs Local Detection

Google Drive File Stream (DriveFS) on macOS shows files at full size in Finder and in tools like `ncdu`, `du`, and `find`, but files may be **stubs** — cloud-only placeholders that take zero local disk space. Always verify before counting Google Drive files as local usage.

### How to Check

```bash
# Check if a file is a stub (0B actual) or downloaded (full size)
echo "apparent: $(ls -lh "$FILE" | awk '{print $5}')"
echo "actual:   $(du -sh "$FILE" | cut -f1)"
echo "xattr:    $(xattr "$FILE")"
```

**Stub indicators:**
- `du -sh` returns `0B` despite `ls -l` showing full size
- `xattr` contains `com.google.drivefs.item-id#S` — the `#S` suffix means stub/cloud-only

**Downloaded indicators:**
- `du -sh` matches `ls -l` size
- `xattr` contains `com.google.drivefs.item-id` (no `#S`)

### Bulk Check — Find All Actually-Downloaded Large GDrive Files

```bash
/usr/bin/env bash << 'GDRIVE_EOF'
GDRIVE="$HOME/Library/CloudStorage/$(ls ~/Library/CloudStorage/ | grep -i google | head -1)"

echo "=== Actually downloaded Google Drive files >100MB ==="
find "$GDRIVE" -type f -size +100M 2>/dev/null | while read -r f; do
  actual=$(du -sk "$f" 2>/dev/null | cut -f1)
  if [ "$actual" -gt 102400 ]; then  # >100MB actually on disk
    size=$(du -sh "$f" 2>/dev/null | cut -f1)
    echo "$size  $f"
  fi
done | sort -rh
GDRIVE_EOF
```

### Key Insight
Tools like `ncdu`, `dust`, `dua` report **apparent sizes** for Google Drive stubs, not actual disk usage. A folder showing 80GB in ncdu may use 0 bytes locally. Always use `du -sh` or check `xattr` to confirm before treating GDrive files as local storage consumers.

---

## Troubleshooting

| Issue                                 | Cause                            | Solution                                   |
| ------------------------------------- | -------------------------------- | ------------------------------------------ |
| `uv cache clean` hangs                | Lock held by running uv          | Use `--force` flag                         |
| `brew cleanup` frees 0 bytes          | Already clean or formulae linked | Run `brew cleanup --prune=all`             |
| `find` reports permission denied      | System Integrity Protection      | Add `2>/dev/null` to suppress              |
| `gdu` command not found               | Installed as `gdu-go`            | Use `gdu-go` (coreutils conflict)          |
| `dust` shows different size than `df` | Counting method differs          | Normal - `df` includes filesystem overhead |
| Stale file scan is slow               | Deep directory tree              | Limit `-maxdepth` or exclude more paths    |
| Docker not accessible                 | Desktop app not running          | Start Docker.app or skip Docker cleanup    |
