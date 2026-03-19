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

echo "Installing packages and applications..."

# Avoid redundant API fetches since brew update already ran above
export HOMEBREW_NO_AUTO_UPDATE=1

# Install all formulae in one call (resolves deps once, downloads in parallel)
brew install imagemagick cmake gcc ffmpeg gh wget curl python@3.12 \
  fzf neovim yt-dlp yq tmux atuin vim neofetch node git zsh ripgrep \
  ocrmypdf tesseract graphviz fswatch nvm deno oven-sh/bun/bun ncdu

# Install vim-plug for neovim
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

# Install all casks in one call (--overwrite handles apps already installed outside brew)
brew install --cask --overwrite raycast zed todoist tomatobar zoom alt-tab bruno \
  hiddenbar blackhole-2ch ollama amethyst hammerspoon karabiner-elements \
  visual-studio-code google-chrome warp ghostty logseq obsidian postman \
  protonvpn cloudflare-warp finetune

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
python3 -m venv ~/.config/config-venv
~/.config/config-venv/bin/pip install --upgrade pip
~/.config/config-venv/bin/pip install -r ~/.config/requirements.txt

# Symlink scripts to PATH
mkdir -p ~/.local/bin
for script in ~/.config/scripts/*; do
  if [ -f "$script" ] && [ -x "$script" ]; then
    scriptname=$(basename "$script")
    ln -sf "$script" ~/.local/bin/"$scriptname"
  fi
done

# Claude Code behavioral files
mkdir -p ~/.claude ~/.config/claude/agents
ln -sf ~/.config/claude/skills ~/.claude/skills
ln -sf ~/.config/claude/commands ~/.claude/commands
ln -sf ~/.config/claude/agents ~/.claude/agents
ln -sf ~/.config/claude/settings.json ~/.claude/settings.json

# Download Claude Code docs locally
sync-docs


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

echo "macOS setup complete!"
