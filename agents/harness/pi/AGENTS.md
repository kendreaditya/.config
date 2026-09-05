# Global Pi Config

## Local Documentation

Use the documentation bundled with the active Pi installation when answering
questions about Pi itself, its SDK, extensions, themes, skills, or TUI. Resolve
the active installation from `command -v pi`; do not assume a versioned install
path.

Read the relevant document completely and follow its cross-references before
implementing Pi-specific changes. Common topics include `docs/extensions.md`,
`docs/themes.md`, `docs/skills.md`, `docs/prompt-templates.md`, `docs/tui.md`,
`docs/keybindings.md`, `docs/sdk.md`, `docs/custom-provider.md`,
`docs/models.md`, and `docs/environment-variables.md`.

## Shared Agent Configuration

- Skills: `~/.agents/skills/` → `~/.config/agents/skills/`
- Global Pi instructions: `~/.pi/agent/AGENTS.md` → this file
- Project instructions: Pi discovers `AGENTS.md` or `CLAUDE.md` while walking
  from the current directory toward the filesystem root.

Pi's `~/.pi/agent/settings.json`, authentication, sessions, and extensions are
machine-local and are not linked into the public dotfiles repository.

## Python Environment

System Python is PEP-668 externally managed. Use the shared virtual environment
at `~/workspace/.venv` for third-party packages:

- Install: `~/workspace/.venv/bin/pip install <pkg>`
- Run: `~/workspace/.venv/bin/python <script.py>`

Do not use `--break-system-packages` or `--user` with system Python.

## Environment Variables

API keys and secrets live in `~/.config/.env` (git-crypt encrypted and sourced
by `.zshrc`). A public template lives in `~/.config/.env.example`.
