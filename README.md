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
- **Runtimes** — Node, Python, Bun, Deno
- **Apps** — VS Code, Chrome, Obsidian, Postman, Raycast/Ulauncher, Zoom, Tailscale
- **Claude Code CLI**, Oh My Zsh, npm globals, Python venv, vim-plug
- **Fonts** from `assets/fonts/` → installed to the OS font directory
- **System defaults** — dock/finder/sidebar (macOS), GNOME settings (Linux), PowerToys + PSReadLine (Windows)
- **Symlinks** — scripts to `~/.local/bin`, Claude config to `~/.claude/`
