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
sudo apt install -y \
  imagemagick cmake gcc g++ ffmpeg curl wget \
  python3 python3-pip python3-venv python3-dev \
  fzf neovim vim tmux git zsh ripgrep fastfetch \
  tesseract-ocr ocrmypdf graphviz ncdu fswatch \
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

# Node.js (NodeSource, current LTS)
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt install -y nodejs
fi

# Global npm CLIs
npm install -g wrangler vercel pnpm typescript tailwindcss eslint yarn

# Bun
command -v bun &>/dev/null || curl -fsSL https://bun.sh/install | bash

# Deno
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

# Python venv for .config scripts
echo "Setting up .config Python venv..."
python3 -m venv ~/.config/config-venv
~/.config/config-venv/bin/pip install --upgrade pip
~/.config/config-venv/bin/pip install -r ~/.config/requirements.txt

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

# Claude Code behavioral files
mkdir -p ~/.claude ~/.config/claude/agents
# Guard: a prior `ln -s` (without -n) into an already-symlinked dir lands *inside* it,
# creating e.g. ~/.config/claude/agents/agents -> ~/.config/claude/agents. Clean any such loops.
for d in skills commands agents; do
  loop="$HOME/.config/claude/$d/$d"
  [ -L "$loop" ] && rm "$loop"
done
ln -sfn ~/.config/claude/skills ~/.claude/skills
ln -sfn ~/.config/claude/commands ~/.claude/commands
ln -sfn ~/.config/claude/agents ~/.claude/agents
ln -sfn ~/.config/claude/settings.json ~/.claude/settings.json
ln -sfn ~/.config/claude/CLAUDE.md ~/.claude/CLAUDE.md

# Claude Code CLI
if ! command -v claude &> /dev/null; then
  echo "Installing Claude Code..."
  curl -fsSL https://claude.ai/install.sh | bash
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
for cmd in node python3 nvim tmux gh claude fastfetch; do
  if command -v "$cmd" &>/dev/null; then
    echo "  ✓ $cmd"
  else
    echo "  ✗ $cmd (not in PATH — open a new shell)"
  fi
done

echo ""
echo "✅ Linux setup complete!"
echo "👉 Run 'exec zsh' or open a new terminal to pick up shell changes."
