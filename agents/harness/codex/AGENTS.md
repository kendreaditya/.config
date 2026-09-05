# Global Codex Config

## Local Documentation

Vendored Claude Code documentation is available at `~/.config/agents/docs/`
(refreshed via `sync-docs`). Use it only for Claude Code questions; for Codex
behavior, inspect the installed Codex CLI help and current configuration rather
than treating Claude-specific documentation as authoritative.

Relevant Claude Code reference files include:

- `overview.md` — what Claude Code is
- `settings.md` — all settings options
- `hooks.md` / `hooks-guide.md` — hook system
- `skills.md` — skills system
- `mcp.md` — MCP server integration
- `commands.md` — slash commands
- `permissions.md` — permission model
- `memory.md` — memory/AGENTS.md system

## Agents

Custom agent definitions live in `~/.config/agents/harness/codex/agents/`
(symlinked to `~/.codex/agents/`). Shared persona source files live in
`~/.config/agents/personas/`.

## Skills & Commands

- Skills: `~/.codex/skills/user/` → `~/.config/agents/skills/`
- Prompts: `~/.codex/prompts/` → `~/.config/agents/commands/`
- Cross-harness discovery: `~/.agents/skills/` → `~/.config/agents/skills/`

## Python Environment

System Python is PEP-668 externally-managed. Use the shared venv at `~/workspace/.venv` for any `pip install` or running scripts that need third-party packages:

- Install: `~/workspace/.venv/bin/pip install <pkg>`
- Run: `~/workspace/.venv/bin/python <script.py>`

Do not use `--break-system-packages` or `--user` against system Python.

## Environment Variables

API keys and secrets live in `~/.config/.env` (encrypted in the repo via git-crypt, auto-sourced by `.zshrc`). A template lives in `.env.example`. If `$TODOIST_API_TOKEN` or similar looks empty in a new shell, re-source it:

```bash
source ~/.config/.env
```
