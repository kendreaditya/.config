<p align="center">
  <img src="assets/config-logo.png" alt=".config" width="400" />
</p>

<p align="center">Personal dotfiles and macOS environment for Aditya Kendre — version-controlled and symlinked into place on a fresh machine.</p>

## Quick Start

**One-liner — no git required:**
```bash
curl -sSL https://raw.githubusercontent.com/kendreaditya/.config/main/install.sh | bash
```

Or clone manually if you prefer SSH:
```bash
git clone git@github.com:kendreaditya/.config.git ~/.config
~/.config/setup-macos.sh
```

The bootstrap (`install.sh`) installs Xcode CLT if missing, clones this repo to `~/.config`, then runs `setup-macos.sh`.

### What gets installed

- **Homebrew formulae** — imagemagick, ffmpeg, gh, fzf, neovim, tmux, atuin, ripgrep, himalaya, mas, imsg, and more
- **Casks** — Raycast, Zed, Ghostty, Warp, Obsidian, VS Code, Chrome, Karabiner, Hammerspoon, and more
- **Mac App Store** — Tailscale (via `mas`)
- **Claude Code CLI** — from `claude.ai/install.sh`
- **Oh My Zsh**, npm globals, Python venv, vim-plug for Neovim
- **Fonts** — anything in `assets/fonts/` installed to `~/Library/Fonts/`
- **macOS defaults** — dock, finder, sidebar, TouchID for sudo
- **Symlinks** — scripts to `~/.local/bin`, Claude config to `~/.claude/`

### Interactive prompts during install

The script pauses for:
- **Sudo password** (2–3 times) — Homebrew, TouchID setup, some defaults
- **Apple ID** — App Store sign-in is required for `mas install` to work. If not signed in, Tailscale install silently fails — sign in first via App Store.app

---

## What's Here

### `setup-macos.sh`
Full macOS setup script. Idempotent — safe to re-run.

### `scripts/`
Custom CLI tools symlinked to `~/.local/bin`.

| Script | Description | Usage |
|---|---|---|
| `wcb` | Async web scraper → LLM-optimized markdown | `wcb https://docs.example.com` |
| `shortn` | Compress markdown to token limit (TextRank) | `shortn input.md -t 8000` |
| `sync-docs` | Download Claude Code docs to `~/.config/claude/docs/` | `sync-docs` |
| `url` | Generate HTML redirect files | `url example.com` |
| `vtt2txt` | Convert VTT subtitles to plain text | `vtt2txt input.vtt` |
| `zsh-profile` | Print slowest zsh startup items | `zsh-profile` |

Shared modules: `_utils.py` (venv, progress, markdown), `_context.py` (tokenizer wrappers).

### `claude/`
Claude Code behavioral config — symlinked into `~/.claude/` by `setup-macos.sh`.

| Path | Purpose |
|---|---|
| `claude/CLAUDE.md` | Global Claude instructions |
| `claude/settings.json` | Claude Code preferences |
| `claude/skills/` | Installed agent skills |
| `claude/commands/` | Custom slash commands |
| `claude/agents/` | Role-specific agent personas |

> `claude/docs/` is gitignored — regenerate with `sync-docs`.

### `assets/`
- `assets/fonts/` — licensed fonts auto-installed to `~/Library/Fonts/`
- `assets/config-logo.png` — repo logo

### Shell
- `.zshrc` — Oh My Zsh, robbyrussell theme, PATH, aliases
- `.zprofile` — brew shellenv
- `ZDOTDIR=$HOME/.config` set in `~/.zshenv` so zsh reads from here

### `requirements.txt`
Python deps for the scripts venv at `~/.config/config-venv/`.

---

## Manual Steps After Setup

- **App Store sign-in** — required for Tailscale to install via `mas`
- **Full Disk Access** — grant to your terminal for `imsg` to read Messages DB (System Settings → Privacy & Security → Full Disk Access)
- **Reboot** — required for `blackhole-2ch` audio driver
- **Neovim** — run `:PlugInstall` on first launch
- **Raycast / AltTab / Todoist / Chrome** — sign in, restore preferences

## Troubleshooting

- **`brew: command not found` mid-script** — open a new shell or run `eval "$(/opt/homebrew/bin/brew shellenv)"`
- **`mas install` fails silently** — you're not signed into the App Store, or the app isn't in your Apple ID's purchase history. Install it once via App Store GUI first
- **Shell changes don't apply** — `exec zsh` or open a new terminal
