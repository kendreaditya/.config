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
  ocrmypdf tesseract graphviz fswatch nvm deno oven-sh/bun/bun

# Install vim-plug for neovim
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

# Install all casks in one call (--overwrite handles apps already installed outside brew)
brew install --cask --overwrite raycast zed todoist tomatobar zoom alt-tab bruno \
  hiddenbar blackhole-2ch ollama amethyst hammerspoon karabiner-elements \
  visual-studio-code google-chrome warp ghostty logseq obsidian postman \
  protonvpn cloudflare-warp

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


# Set system defaults
echo "Configuring macOS settings..."

# Disable automatic spelling correction
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Menu Bar Settings
defaults write com.apple.controlcenter "NSStatusItem Visible Sound" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible Bluetooth" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible NowPlaying" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible Battery" -int 1
defaults write com.apple.controlcenter BatteryShowPercentage -bool true

# Dock settings
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-delay -float 0
defaults write com.apple.dock autohide-time-modifier -float 0.5
defaults write com.apple.dock orientation -string "bottom"
defaults write com.apple.dock tilesize -int 36
defaults write com.apple.dock mru-spaces -bool false
defaults write com.apple.dock persistent-apps -array

# Finder settings
defaults write com.apple.finder AppleShowAllExtensions -bool true
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"
defaults write com.apple.finder AppleShowAllFiles YES
defaults write com.apple.finder ShowPathbar -bool true

# Keyboard settings
defaults write NSGlobalDomain InitialKeyRepeat -int 15
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write -g ApplePressAndHoldEnabled -bool false

# Disables "Displays have separate Spaces"
defaults write com.apple.spaces spans-displays -bool true


# Enable TouchID for sudo
if ! grep -q "pam_tid.so" /etc/pam.d/sudo; then
  echo "Enabling TouchID for sudo..."
  sudo sed -i '' '2i\
auth       sufficient     pam_tid.so
' /etc/pam.d/sudo
fi

# Set Chrome as default browser
echo "Setting Chrome as default browser..."
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerContentType="public.html";LSHandlerRoleAll="com.google.chrome";}'
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerURLScheme="http";LSHandlerRoleAll="com.google.chrome";}'
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerURLScheme="https";LSHandlerRoleAll="com.google.chrome";}'

# Disable Spotlight command+space shortcut
defaults write com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add 64 "<dict><key>enabled</key><false/></dict>"

# Disable .DS_Store on external drives
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true

# Dark mode
defaults write NSGlobalDomain AppleInterfaceStyle -string "Dark"

# Finder improvements
defaults write com.apple.finder ShowStatusBar -bool true
defaults write com.apple.finder _FXShowPosixPathInTitle -bool true
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
defaults write com.apple.finder FXDefaultSearchScope -string "SCcf"

# Dock: hide recent apps
defaults write com.apple.dock show-recents -bool false

# Crash reporter as notification
defaults write com.apple.CrashReporter DialogType -string "notification"

# Reclaim disk space from stale brew downloads
brew cleanup

# Clear pip download cache (packages already installed into venv)
pip3 cache purge

# Restart affected services
echo "Restarting services to apply changes..."
killall Dock
killall Finder
killall SystemUIServer

echo "macOS setup complete!"
