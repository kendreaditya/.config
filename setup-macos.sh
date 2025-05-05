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

# Install packages
brew install imagemagick
brew install cmake
brew install gcc
brew install ffmpeg
brew install gh
brew install wget
brew install curl
brew install python@3.12
brew install fzf
brew install neovim && sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'
brew install yt-dlp
brew install yq
brew install tmux
brew install atuin
brew install vim
brew install neofetch
brew install node
brew install git
brew install zsh
brew install rg

# Install applications
brew install --cask raycast
brew install --cask zed
brew install --cask todoist
brew install --cask tomatobar
brew install --cask zoom
brew install --cask alt-tab
brew install --cask bruno
brew install --cask hiddenbar
brew install --cask blackhole-2ch
brew install --cask ollama
brew install --cask amethyst
brew install --cask hammerspoon
brew install --cask karabiner-elements
brew install --cask visual-studio-code
brew install --cask google-chrome
brew install --cask warp
brew install --cask ghostty
brew install --cask logseq
brew install --cask obsidian 
brew install --cask postman

# Install oh-my-zsh
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  echo "Installing Oh My Zsh..."
  sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
  echo "Oh My Zsh installed successfully!"
else
  echo "Oh My Zsh is already installed, skipping..."
fi


# Set system defaults
echo "Configuring macOS settings..."

# Disable automatic spelling correction
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Menu Bar Settings
defaults write com.apple.controlcenter "NSStatusItem Visible Sound" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible Bluetooth" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible NowPlaying" -int 1

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
defaults write com.apple.finder FXPreferredViewStyle -string "clmv"
defaults write com.apple.finder AppleShowAllFiles YES
defaults write com.apple.finder ShowPathbar -bool true

# Keyboard settings
defaults write NSGlobalDomain InitialKeyRepeat -int 15
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write -g ApplePressAndHoldEnabled -bool false

# Disables "Displays have separate Spaces"
defaults write com.apple.spaces spans-displays -bool false


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

# Restart affected services
echo "Restarting services to apply changes..."
killall Dock
killall Finder
killall SystemUIServer

echo "macOS setup complete!"
