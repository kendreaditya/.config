<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/config-dark.svg">
    <img src="assets/config-light.svg" alt=".config" width="400">
  </picture>
</p>

<p align="center">Personal dotfiles and cross-platform dev environment.</p>

<div align="center">
  <video src="https://github.com/user-attachments/assets/3be1b63d-0be1-4f7a-8101-d3b6a09972f9" width="300" controls></video>
</div>

## Quick Start

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/kendreaditya/.config/main/install.sh | bash
```

**Windows (PowerShell, Admin):**
```powershell
irm https://raw.githubusercontent.com/kendreaditya/.config/main/install.ps1 | iex
```

The bootstrap auto-detects the platform, installs prereqs (Xcode CLT / git), clones this repo to `~/.config`, then runs the matching `setup-*` script.

## What gets installed

- **Package manager native** — Homebrew (macOS), apt/snap (Linux), winget (Windows)
- **Core CLIs** — neovim, tmux, fzf, ripgrep, gh, fastfetch, atuin, yq, yt-dlp
- **Runtimes** — Node (via fnm), Python, Bun, Deno
- **Apps** — VS Code, Chrome, Obsidian, Postman, Raycast/Ulauncher, Zoom, Tailscale
- **Claude Code + Codex CLIs**, Oh My Zsh, npm globals, Python venv, vim-plug
- **Fonts** from `assets/fonts/` → installed to the OS font directory
- **System defaults** — dock/finder/sidebar (macOS), GNOME settings (Linux), PowerToys installed + PSReadLine/oh-my-posh profile configured (Windows)
- **Symlinks** — scripts to `~/.local/bin`, agent config (`agents/`) to `~/.claude/` and `~/.codex/`

## Working on this repo

This repo is **public**. Don't work directly on `main` — default to a
per-device branch instead, and stay there permanently:

```bash
git switch -c "device/$(hostname -s)"     # or: git switch -c "device/$(scutil --get LocalHostName)" on macOS
```

Everything lives on that branch first, including work-specific or
machine-local config — it's never pushed, and this checkout is never
branch-switched back to `main`. `main` gets its own permanent, linked
worktree instead, set up once:

```bash
agents/skills/dotconfig-branching/scripts/worktree-add.sh ~/.config-main main
```

(This wraps `git worktree add` plus a fix for a git-crypt limitation with
linked worktrees — see `SKILL.md` for why it's needed.)

Only promote a change to `main` once it's genuinely portable and safe to
publish:

```bash
agents/skills/dotconfig-branching/scripts/publish.sh <path> [<path>...]
agents/skills/dotconfig-branching/scripts/publish.sh -m "msg" <path>...
agents/skills/dotconfig-branching/scripts/publish.sh --no-push <path>...
```

`publish.sh` wraps `promote.sh`, which checks out just those paths from your
device branch into main's worktree, runs `vet.sh` (checks for internal
hostnames, credential-shaped strings, force-added ignored files, absolute home
paths) against the staged diff, commits there, then cherry-picks that commit
back onto your device branch so it stays a superset of what's public.
`publish.sh` then pushes `main` and verifies that superset property.

Run `promote.sh` directly, or `publish.sh --no-push`, when you'd rather review
before publishing — `promote.sh` stops before `git push` and prints the command.

Neither one rebases your device branch onto `main`: the two branches share no
common ancestor after a past history scrub, so a rebase would replay your whole
branch against unrelated commits. The cherry-pick is what keeps device ahead.

Full details: `agents/skills/dotconfig-branching/SKILL.md`.
