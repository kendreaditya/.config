#!/bin/bash
# setup-macos.sh

# Script description: Setup script for macOS development environment
# Author: Aditya Kendre (aditya@semant.co)

# Check if ZDOTDIR is set in .zshenv
echo "Checking zsh configuration..."
if [ -f "$HOME/.zshenv" ]; then
  if ! grep -q "ZDOTDIR=\$HOME/.config" "$HOME/.zshenv"; then
    echo "Setting ZDOTDIR in .zshenv..."
    echo 'export ZDOTDIR=$HOME/.config' >> "$HOME/.zshenv"
    echo "ZDOTDIR has been set to \$HOME/.config"
  else
    echo "ZDOTDIR is already set in .zshenv"
  fi
else
  echo "Creating .zshenv and setting ZDOTDIR..."
  echo 'export ZDOTDIR=$HOME/.config' > "$HOME/.zshenv"
  echo ".zshenv created with ZDOTDIR set to \$HOME/.config"
fi

# Install Homebrew if not already installed
if ! command -v brew &> /dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Ensure brew is in PATH for this script (works on fresh installs and re-runs)
[ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"

echo "Installing packages and applications..."

# Avoid redundant API fetches since brew update already ran above
export HOMEBREW_NO_AUTO_UPDATE=1

# Install all formulae in one call (resolves deps once, downloads in parallel)
brew tap steipete/tap
brew tap assemblyai/assemblyai
brew install mas imagemagick cmake gcc ffmpeg gh wget curl python@3.12 \
  fzf neovim yt-dlp yq tmux atuin vim fastfetch node git zsh ripgrep tree rclone \
  ocrmypdf tesseract graphviz fswatch nvm deno oven-sh/bun/bun ncdu himalaya \
  steipete/tap/gogcli steipete/tap/imsg assemblyai gemini-cli

# wacli: brew tap is stale (pins v0.2.0, which WhatsApp rejects as "client outdated").
# Fetch the latest prebuilt universal binary directly from GitHub releases.
WACLI_TAG=$(curl -s https://api.github.com/repos/steipete/wacli/releases/latest | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p')
curl -sL "https://github.com/steipete/wacli/releases/download/${WACLI_TAG}/wacli-macos-universal.tar.gz" | tar -xzf - -C /tmp
mv /tmp/wacli /opt/homebrew/bin/wacli
chmod +x /opt/homebrew/bin/wacli

# Install global npm CLIs
npm install -g wrangler vercel pnpm typescript tailwindcss eslint yarn

# Install vim-plug for neovim
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

# Install all casks in one call (--force handles apps already installed outside brew)
# NOTE: tomatobar handled separately below — the cask is deprecated (disabled 2026-09-01)
# because the app isn't Apple-notarized and fails Gatekeeper with
# "cannot be verified free of malware".
brew install --cask --force raycast zed todoist zoom alt-tab bruno \
  hiddenbar blackhole-2ch ollama hammerspoon karabiner-elements \
  visual-studio-code google-chrome warp ghostty logseq obsidian postman \
  claude claude-code codex codex-app whatsapp \
  protonvpn cloudflare-warp finetune

# TomatoBar: unnotarized open-source pomodoro timer (MIT, github.com/ivoronin/TomatoBar).
# Brew's --no-quarantine flag was removed, so install then strip the quarantine xattr
# ourselves. Falls back to a direct GitHub download once the cask is disabled.
if brew info --cask tomatobar &>/dev/null; then
  brew install --cask --force tomatobar || true
else
  echo "tomatobar cask unavailable — fetching latest release directly..."
  TB_TAG=$(curl -s https://api.github.com/repos/ivoronin/TomatoBar/releases/latest | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p')
  curl -sL "https://github.com/ivoronin/TomatoBar/releases/download/${TB_TAG}/TomatoBar-${TB_TAG}.zip" -o /tmp/tomatobar.zip
  rm -rf /Applications/TomatoBar.app
  unzip -q -o /tmp/tomatobar.zip -d /Applications/
  rm /tmp/tomatobar.zip
fi
[ -d /Applications/TomatoBar.app ] && sudo xattr -dr com.apple.quarantine /Applications/TomatoBar.app

# Install Mac App Store apps (requires App Store sign-in)
mas install 1475387142  # Tailscale

# Install oh-my-zsh
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  echo "Installing Oh My Zsh..."
  sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
  echo "Oh My Zsh installed successfully!"
else
  echo "Oh My Zsh is already installed, skipping..."
fi

# Create .config Python venv and install dependencies
echo "Setting up .config Python venv..."
/opt/homebrew/bin/python3.12 -m venv ~/.config/config-venv
~/.config/config-venv/bin/pip install --upgrade pip
~/.config/config-venv/bin/pip install -r ~/.config/requirements.txt

# Run per-skill setup scripts (skills own anything beyond pip, e.g. playwright browsers)
echo "Running per-skill setup scripts..."
for s in ~/.config/claude/skills/*/scripts/setup.sh; do
  [ -f "$s" ] || continue
  echo "  → $s"
  bash "$s"
done

# Create workspace directory
mkdir -p ~/workspace

# Install licensed fonts from assets/fonts into ~/Library/Fonts
if [ -d ~/.config/assets/fonts ]; then
  echo "Installing fonts..."
  mkdir -p ~/Library/Fonts
  for font in ~/.config/assets/fonts/*.{otf,ttf}; do
    [ -f "$font" ] && cp -f "$font" ~/Library/Fonts/
  done
fi

# Symlink scripts to PATH
mkdir -p ~/.local/bin
for script in ~/.config/scripts/*; do
  if [ -f "$script" ] && [ -x "$script" ]; then
    scriptname=$(basename "$script")
    ln -sf "$script" ~/.local/bin/"$scriptname"
  fi
done

# LaunchAgents (symlinked from ~/.config so edits land in one place)
mkdir -p ~/Library/LaunchAgents
for plist in ~/.config/scripts/*/*.plist; do
  [ -f "$plist" ] || continue
  label=$(basename "$plist")
  target="$HOME/Library/LaunchAgents/$label"
  ln -sfn "$plist" "$target"
  launchctl unload "$target" 2>/dev/null || true
  launchctl load "$target"
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

# Codex (CLI + desktop app) reads ~/.codex/skills/**/SKILL.md recursively.
# Expose Claude skills as a subdirectory so Codex's built-ins (.system, codex-primary-runtime) are preserved.
mkdir -p ~/.codex/skills
ln -sfn ~/.config/claude/skills ~/.codex/skills/user

# Download Claude Code docs locally (scripts symlinked above)
~/.local/bin/sync-docs || echo "Warning: sync-docs failed (may need 'requests' — install manually)"


# Apply macOS configuration
echo "Applying macOS settings..."
MACOS_DIR="$(dirname "$0")/.macos"
chmod +x "$MACOS_DIR"/*.sh
export MACOS_SETUP_RUNNING=1

bash "$MACOS_DIR/defaults.sh"
bash "$MACOS_DIR/dock.sh"
bash "$MACOS_DIR/finder.sh"
bash "$MACOS_DIR/sidebar.sh"

# Restart affected services
echo "Restarting services to apply changes..."
killall Dock Finder SystemUIServer

# Reclaim disk space from stale brew downloads
brew cleanup

# Clear pip download cache (packages already installed into venv)
pip3 cache purge

# Verify critical tools are available
echo ""
echo "Verifying installation..."
for cmd in brew node python3 nvim tmux gh claude; do
  if command -v "$cmd" &>/dev/null; then
    echo "  ✓ $cmd"
  else
    echo "  ✗ $cmd (not in PATH — open a new shell)"
  fi
done

echo ""
echo "✅ macOS setup complete!"
echo "👉 Run 'exec zsh' or open a new terminal to pick up shell changes."
