# Global Claude Code Config

## Local Documentation

Full Claude Code docs are available at `~/.config/claude/docs/` (65 Markdown files, refreshed via `sync-docs`).

When asked about Claude Code features, settings, hooks, MCP, skills, or any Claude Code behavior — read the relevant file from `~/.config/claude/docs/` first rather than guessing. Key files:

- `overview.md` — what Claude Code is
- `settings.md` — all settings options
- `hooks.md` / `hooks-guide.md` — hook system
- `skills.md` — skills system
- `mcp.md` — MCP server integration
- `commands.md` — slash commands
- `permissions.md` — permission model
- `memory.md` — memory/CLAUDE.md system

## Agents

Custom agent personas live in `~/.config/claude/agents/` (symlinked to `~/.claude/agents/`). Each `.md` file defines a role-specific behavior.

## Skills & Commands

- Skills: `~/.claude/skills/` → `~/.config/claude/skills/`
- Commands: `~/.claude/commands/` → `~/.config/claude/commands/`
