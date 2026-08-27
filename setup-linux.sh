#!/bin/bash
# setup-linux.sh — Debian/Ubuntu setup mirroring setup-macos.sh
set -e

# Check for apt
if ! command -v apt &> /dev/null; then
  echo "This script is designed for Debian/Ubuntu-based distributions."
  exit 1
fi

# ZDOTDIR so zsh reads from ~/.config
echo "Checking zsh configuration..."
if [ ! -f "$HOME/.zshenv" ] || ! grep -q "ZDOTDIR=\$HOME/.config" "$HOME/.zshenv"; then
  echo 'export ZDOTDIR=$HOME/.config' >> "$HOME/.zshenv"
fi

echo "Updating package repositories..."
sudo apt update && sudo apt upgrade -y

# Install everything in one call (resolves deps once, parallel downloads)
echo "Installing packages..."
# Mirrors setup-macos.sh: tesseract-ocr, ocrmypdf and graphviz removed by request.
sudo apt install -y \
  imagemagick cmake gcc g++ ffmpeg curl wget \
  python3 python3-pip python3-venv python3-dev \
  fzf neovim vim tmux git zsh ripgrep fastfetch \
  ncdu fswatch \
  jq git-crypt tree rclone \
  i3 ulauncher

# vim-plug for neovim
curl -fLo ~/.local/share/nvim/site/autoload/plug.vim --create-dirs \
  https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

# GitHub CLI
if ! command -v gh &> /dev/null; then
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update && sudo apt install -y gh
fi

# yt-dlp, yq, atuin (binary installs)
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod a+x /usr/local/bin/yq
command -v atuin &>/dev/null || bash <(curl https://raw.githubusercontent.com/atuinsh/atuin/main/install.sh)

# uv (Python package/tool manager) and fnm (Node version manager) — neither is
# a stable apt package across Debian/Ubuntu releases, so use their official
# installers, matching the atuin/bun/deno pattern above. Both installers land
# under ~/.local, which only reaches PATH in a new shell — source uv's own env
# file and prepend ~/.local/bin so both are usable for the rest of this run.
# NOTE: install paths here are unverified against an actual Ubuntu/Debian box
# this session (no Linux machine available) — confirm on first real run.
command -v uv &>/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
command -v fnm &>/dev/null || curl -fsSL https://fnm.vercel.app/install | bash -s -- --skip-shell
export PATH="$HOME/.local/bin:$PATH"

# Node.js (NodeSource, current LTS)
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt install -y nodejs
fi

# Global npm CLIs (yarn removed by request — pnpm covers the same ground)
npm install -g wrangler vercel pnpm typescript tailwindcss eslint

# Bun removed by request: its only consumer was gstack, also removed.
# To restore: curl -fsSL https://bun.sh/install | bash

# Deno — kept: yt-dlp requires it (see setup-macos.sh for the detail)
command -v deno &>/dev/null || curl -fsSL https://deno.land/install.sh | sh

# Cloudflare WARP
if ! command -v warp-cli &>/dev/null; then
  curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
  sudo apt update && sudo apt install -y cloudflare-warp
fi

# Tailscale (official install script)
if ! command -v tailscale &>/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

# Ollama
command -v ollama &>/dev/null || curl -fsSL https://ollama.com/install.sh | sh

# Snap apps (VS Code, Chrome alt, etc.)
if ! command -v snap &> /dev/null; then
  sudo apt install -y snapd
  sudo systemctl enable --now snapd.socket
fi
sudo snap install code --classic
sudo snap install todoist
sudo snap install zoom-client
sudo snap install protonvpn-community

# Chrome
if ! command -v google-chrome &> /dev/null; then
  wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
  echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
  sudo apt update && sudo apt install -y google-chrome-stable
fi

# Oh My Zsh
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
fi

# Python venv for .config scripts. Skip creation if it already exists so a
# re-run doesn't discard installed packages.
echo "Setting up .config Python venv..."
if [ ! -x ~/.config/config-venv/bin/python3 ]; then
  python3 -m venv ~/.config/config-venv
fi
# uv (10-100x faster than pip, resolves the whole set at once) rather than pip.
# The venv itself stays a plain stdlib venv so non-uv tooling still understands it.
uv pip install --python ~/.config/config-venv/bin/python3 -r ~/.config/requirements.txt

# --- Git submodules: ws (workspace manager), parlai (AI chat history search) --
# Both are plain git submodules pinned to a specific commit in .gitmodules; this
# one call inits/clones every submodule the repo declares.
git -C ~/.config submodule update --init --recursive

# --- Standalone CLI tools (isolated envs, not in config-venv) ------------------
# End-user CLIs rather than libraries our scripts import, so they get their own
# isolated environment via `uv tool` (the pipx model) instead of config-venv,
# where their pins would fight our scripts' pins.
uv tool install --quiet subliminal || true   # movie-subs: subtitle fetching

# parlai: the `parlai` CLI backing agents/skills/parlai (AI chat history
# search). Editable install of the submodule checkout above.
uv tool install --quiet --editable ~/.config/parlai || true

# ws: workspace manager. `ws init` symlinks it into ~/.local/bin and seeds
# config.json. Idempotent.
[ -x ~/.config/ws/ws ] && ~/.config/ws/ws init || true

# fnm: shell integration. The installer above puts the binary on PATH; without
# this eval in .zshrc, fnm doesn't manage $PATH or auto-switch on
# .nvmrc/.node-version. Idempotent: skip if a fnm block is already there.
if ! grep -q 'fnm env' ~/.config/.zshrc 2>/dev/null; then
  cat >> ~/.config/.zshrc <<'EOF'

# --- Node version management (fnm) --------------------------------------------
if command -v fnm >/dev/null 2>&1; then
  eval "$(fnm env --use-on-cd --shell zsh)"
fi
EOF
fi

# Run per-skill setup scripts (skills own anything beyond pip, e.g. playwright browsers)
echo "Running per-skill setup scripts..."
for s in ~/.config/agents/skills/*/scripts/setup.sh; do
  [ -f "$s" ] || continue
  echo "  → $s"
  bash "$s"
done

# Workspace dir
mkdir -p ~/workspace

# Install licensed fonts from assets/fonts into ~/.local/share/fonts
if [ -d ~/.config/assets/fonts ]; then
  echo "Installing fonts..."
  mkdir -p ~/.local/share/fonts
  for font in ~/.config/assets/fonts/*.{otf,ttf}; do
    [ -f "$font" ] && cp -f "$font" ~/.local/share/fonts/
  done
  fc-cache -f ~/.local/share/fonts
fi

# Symlink scripts to PATH
mkdir -p ~/.local/bin
for script in ~/.config/scripts/*; do
  if [ -f "$script" ] && [ -x "$script" ]; then
    ln -sf "$script" ~/.local/bin/"$(basename "$script")"
  fi
done

# Agent harness wiring (Claude Code + Codex).
#
# All symlinking lives in agents/link.sh so there is exactly one place that
# knows the layout (plain bash, portable — same script macOS runs). It is
# idempotent, refuses to clobber real files, and handles the shared-vs-per-
# harness split:
#   agents/{skills,commands,memory,personas}  -> shared by every harness
#   agents/harness/<name>/                    -> that harness only
~/.config/agents/link.sh

# Claude Code CLI
if ! command -v claude &> /dev/null; then
  echo "Installing Claude Code..."
  curl -fsSL https://claude.ai/install.sh | bash
fi

# Verify the result: every CLI in scripts/ exposes a `smoke` self-check, and
# `doctor` runs all of them. Non-fatal here so a single broken tool does not
# abort setup, but it surfaces breakage immediately instead of weeks later.
~/.config/scripts/doctor || true

# Claude Code MCP servers — source of truth is ~/.config/agents/harness/claude/mcp-servers.json.
# ~/.claude.json holds mutable session state (OAuth, counters, project history) so we
# don't track it; instead, register each server at user scope via the CLI.
if command -v claude &>/dev/null && [ -f ~/.config/agents/harness/claude/mcp-servers.json ]; then
  echo "Syncing Claude Code MCP servers from mcp-servers.json..."
  jq -r 'keys[]' ~/.config/agents/harness/claude/mcp-servers.json | while read -r name; do
    cfg=$(jq -c --arg n "$name" '.[$n]' ~/.config/agents/harness/claude/mcp-servers.json)
    claude mcp remove "$name" -s user 2>/dev/null || true
    claude mcp add-json "$name" "$cfg" -s user >/dev/null && echo "  ✓ $name"
  done
fi

~/.local/bin/sync-docs || echo "Warning: sync-docs failed (may need 'requests' — install manually)"

# Set Zsh as default shell
if [ "$SHELL" != "$(which zsh)" ]; then
  chsh -s "$(which zsh)"
fi

# GNOME settings (only if GNOME)
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ]; then
  gsettings set org.gnome.desktop.interface enable-spell-checking false 2>/dev/null || true
  gsettings set org.gnome.nautilus.preferences show-hidden-files true 2>/dev/null || true
  gsettings set org.gnome.nautilus.preferences default-folder-viewer 'list-view' 2>/dev/null || true
  gsettings set org.gnome.desktop.peripherals.keyboard repeat-interval 30 2>/dev/null || true
  gsettings set org.gnome.desktop.peripherals.keyboard delay 250 2>/dev/null || true
  if gsettings list-schemas | grep -q "org.gnome.shell.extensions.dash-to-dock"; then
    gsettings set org.gnome.shell.extensions.dash-to-dock dock-position BOTTOM
    gsettings set org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 36
    gsettings set org.gnome.shell.extensions.dash-to-dock autohide true
  fi
fi

# Default browser
command -v google-chrome &>/dev/null && xdg-settings set default-web-browser google-chrome.desktop

# Verify critical tools are available
echo ""
echo "Verifying installation..."
for cmd in node python3 nvim tmux gh claude fastfetch uv fnm jq; do
  if command -v "$cmd" &>/dev/null; then
    echo "  ✓ $cmd"
  else
    echo "  ✗ $cmd (not in PATH — open a new shell)"
  fi
done

# git-crypt: warn if the encrypted files are still locked. Nothing here can
# unlock them — that needs the symmetric key, which by design isn't in the
# repo. Until then .env, agents/memory/**, and the monarch-money prefs are
# ciphertext: API tokens stay unset and agents can't read their memories.
if head -c 10 ~/.config/.env 2>/dev/null | grep -aq GITCRYPT; then
  echo ""
  echo "🔒 ~/.config is git-crypt locked — run 'cd ~/.config && git-crypt unlock /path/to/key'"
  echo "   to decrypt .env (API tokens) and agents/memory/."
fi

echo ""
echo "✅ Linux setup complete!"
echo "👉 Run 'exec zsh' or open a new terminal to pick up shell changes."
