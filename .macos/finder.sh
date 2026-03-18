#!/bin/bash
# .macos/finder.sh — Finder configuration
# Run standalone or called from setup-macos.sh (set MACOS_SETUP_RUNNING=1 to skip killall)
set -euo pipefail

echo "Applying Finder settings..."

# General display
defaults write com.apple.finder AppleShowAllExtensions -bool true
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"
defaults write com.apple.finder AppleShowAllFiles YES
defaults write com.apple.finder ShowPathbar -bool true
defaults write com.apple.finder ShowStatusBar -bool true
defaults write com.apple.finder _FXShowPosixPathInTitle -bool true
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
defaults write com.apple.finder FXDefaultSearchScope -string "SCcf"

# Allow Cmd+Q to quit Finder
defaults write com.apple.finder QuitMenuItem -bool true

# Disable Trash warning
defaults write com.apple.finder WarnOnEmptyTrash -bool false

# Sidebar section visibility
defaults write com.apple.finder SidebarDevicesSectionDisclosedState -bool true
defaults write com.apple.finder SidebarPlacesSectionDisclosedState -bool true
defaults write com.apple.finder SidebarSharedSectionDisclosedState -bool false
defaults write com.apple.finder SidebarTagsSctionDisclosedState -bool true

if [[ -z "${MACOS_SETUP_RUNNING:-}" ]]; then
  killall Finder 2>/dev/null || true
fi

echo "Finder settings applied."
