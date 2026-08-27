# AGENTS.md

This file is the harness-agnostic entry point for AI coding agents working in
this repository (Codex, Claude Code, opencode, and others). It documents the
repo's real on-disk layout. Harness-specific notes are called out inline.

> Maintenance note: do NOT generate this file by find-replacing `Claude` with
> another harness name in CLAUDE.md. Directory names on disk are literal, and a
> blind rename corrupts every path. Edit prose by hand; keep paths verbatim.

## What This Repo Is

Personal dotfiles and agent configuration for macOS. Two main concerns:
(1) `agents/` — behavioral files shared across AI harnesses, symlinked into each
harness's config dir; (2) macOS/Linux/Windows environment bootstrap via
`setup-macos.sh`.

## agents/ layout

```
agents/
  skills/            96 skills, harness-agnostic (SKILL.md is a de-facto standard)
  commands/          slash commands / prompts
  memory/            long-term notes (git-crypt encrypted)
  personas/          role prompts, one .md per agent type
  harness/
    claude/          settings.json, CLAUDE.md, output-styles/, mcp-servers.json
    codex/           AGENTS.md, agents/*.toml
  link.sh            wires all of the above into ~/.claude and ~/.codex
```

Shared dirs are symlinked into every harness; `harness/<name>/` only into that
harness. Run `agents/link.sh` after changing the layout — it is idempotent and
refuses to overwrite real files. `--dry-run` previews.

Two naming details worth knowing: Claude calls role prompts "agents", so
`~/.claude/agents` points at `agents/personas/`. Codex namespaces user skills, so
they land at `~/.codex/skills/user` and its generated `.system/` dir survives.

## Health checks

Every CLI in `scripts/` implements a `smoke` subcommand (exit 0 healthy, 3 needs
auth, other = broken). `scripts/doctor` discovers them and runs them all, so it
never needs to know how any individual tool works:

```bash
doctor                # everything
doctor <name>...      # specific CLIs
doctor --list         # what's discovered, and which support smoke
```

When adding a CLI, add a `smoke` handler to it — do not teach `doctor` about it.

## Scripts Architecture

`~/.config/scripts/` is on `$PATH` and `setup-macos.sh` also mirrors its executables into `~/.local/bin`. Most entries are **symlinks into `agents/skills/<name>/scripts/`** so a skill's CLI is callable directly from the shell (e.g. `wcb`, `shortn`, `mm`, `logseq`, `levels`, `tiktok`, `cleansubs`). A handful are first-class scripts that live here directly: `sync-docs`, `yfin`, `bestbuy`, `url`, `zsh-profile`, `wallpaper/`, `halflife.d/`, `trashlog.d/`.

Python scripts that need third-party packages either:
- Use a dedicated skill venv (`agents/skills/<name>/scripts/.venv`, created by the skill's `setup`), or
- Use the shared venv at `~/.config/config-venv/` (created by `setup-macos.sh`) via a direct shebang (e.g. `sync-docs`).

## Common Commands

### Setup
```bash
# macOS dev environment (Homebrew, Oh My Zsh, symlinks, system defaults, MCP sync)
./setup-macos.sh

# Install/update shared-venv Python dependencies
~/.config/config-venv/bin/pip install -r requirements.txt
```

### Running Scripts
```bash
# Scripts are on PATH after setup; run directly:
wcb https://docs.example.com
shortn input.md -t 8000
```

### Adding a New Script
1. Create `scripts/myscript` (make executable: `chmod +x scripts/myscript`).
2. If it needs third-party packages, either point the shebang at `~/.config/config-venv/bin/python3` or package it as a skill with its own `scripts/.venv`.
3. `setup-macos.sh` automatically symlinks every executable in `scripts/` into `~/.local/bin/` on the next run.

## Python Venv & Dependencies

The shared venv at `~/.config/config-venv/` is created by `setup-macos.sh`. Scripts that need it point their shebang directly at `~/.config/config-venv/bin/python3`. Dependencies live in `requirements.txt`.

## Claude Code Config

`~/.config/agents/` stores Claude Code's behavioral files, version-controlled here and symlinked into `~/.claude/`. Shared dirs are symlinked in for every harness; `harness/claude/` only for Claude Code:

| Path | Purpose |
|------|---------|
| `agents/harness/claude/settings.json` | Claude Code preferences (plugins, voice, model) |
| `agents/harness/claude/system-prompt.txt` | Global Claude personality/behavior overrides |
| `agents/skills/` | Installed skills, shared with every harness |
| `agents/commands/` | Custom slash commands (e.g. `/gdrive-read`), shared |
| `agents/personas/` | Role/persona prompts — one `.md` per agent type, shared |
| `agents/harness/claude/mcp-servers.json` | MCP server definitions (tracked source of truth) |
| `agents/harness/claude/docs/` | Local Claude Code docs (generated, gitignored — run `sync-docs` to regenerate) |

Symlinks: `~/.claude/{skills,commands,agents,settings.json}` → `~/.config/agents/{skills,commands,personas,harness/claude/settings.json}` (Claude calls role prompts "agents", hence `personas` → `~/.claude/agents`). Set up by `agents/link.sh`.

`~/.claude.json` itself is **not** tracked — it mixes MCP config with mutable session state (OAuth tokens, per-project history, counters). `setup-macos.sh` re-registers servers from `mcp-servers.json` via `claude mcp add-json ... -s user` on every run.

### Adding or editing an MCP server
1. Edit `~/.config/agents/harness/claude/mcp-servers.json` (keyed by server name).
2. Apply immediately without re-running the full setup:
   ```bash
   name=myserver   # matches key in mcp-servers.json
   claude mcp remove "$name" -s user 2>/dev/null
   claude mcp add-json "$name" "$(jq -c --arg n "$name" '.[$n]' ~/.config/agents/harness/claude/mcp-servers.json)" -s user
   ```
   Or just re-run the MCP sync block in `setup-macos.sh`.

```bash
# Refresh local Claude Code documentation
sync-docs
```

`agents/` convention: create `agents/personas/researcher.md`, `agents/personas/coder.md`, etc. with role-specific system prompts.

## Shell Config

- Main shell config: `.zshrc` (Oh My Zsh, robbyrussell theme)
- `ZDOTDIR=$HOME/.config` is set so zsh reads from this directory
- Custom scripts on PATH via `~/.local/bin`
