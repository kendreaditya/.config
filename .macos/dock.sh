#!/bin/bash
# .macos/dock.sh — Dock configuration
# Run standalone or called from setup-macos.sh (set MACOS_SETUP_RUNNING=1 to skip killall)
set -euo pipefail

echo "Applying Dock settings..."

defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-delay -float 0
defaults write com.apple.dock autohide-time-modifier -float 0.5
defaults write com.apple.dock orientation -string "bottom"
defaults write com.apple.dock tilesize -int 36
defaults write com.apple.dock mru-spaces -bool false
defaults write com.apple.dock persistent-apps -array
defaults write com.apple.dock show-recents -bool false

# Hidden app icons appear translucent in the Dock
defaults write com.apple.dock showhidden -bool true

# Minimize windows into their application's icon
defaults write com.apple.dock minimize-to-application -bool true

if [[ -z "${MACOS_SETUP_RUNNING:-}" ]]; then
  killall Dock 2>/dev/null || true
fi

echo "Dock settings applied."
