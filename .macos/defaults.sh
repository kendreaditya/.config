#!/bin/bash
# .macos/defaults.sh — System-wide macOS defaults
# Run standalone or called from setup-macos.sh (set MACOS_SETUP_RUNNING=1 to skip killall)
set -euo pipefail

echo "Applying system defaults..."

# Disable automatic spelling correction
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Expand save and print panels by default
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode2 -bool true
defaults write NSGlobalDomain PMPrintingExpandedStateForPrint -bool true
defaults write NSGlobalDomain PMPrintingExpandedStateForPrint2 -bool true

# Tap to click
defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true
defaults -currentHost write NSGlobalDomain com.apple.mouse.tapBehavior -int 1

# TextEdit: plain text mode by default
defaults write com.apple.TextEdit RichText -int 0

# Activity Monitor: show all processes
defaults write com.apple.ActivityMonitor ShowCategory -int 0

# Dark mode
defaults write NSGlobalDomain AppleInterfaceStyle -string "Dark"

# Keyboard settings
defaults write NSGlobalDomain InitialKeyRepeat -int 15
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write -g ApplePressAndHoldEnabled -bool false

# Disables "Displays have separate Spaces"
defaults write com.apple.spaces spans-displays -bool true

# Menu Bar Settings
defaults write com.apple.controlcenter "NSStatusItem Visible Sound" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible Bluetooth" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible NowPlaying" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible Battery" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible FocusModes" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible KeyboardBrightness" -int 1
defaults write com.apple.controlcenter BatteryShowPercentage -bool true

# Force "Always Show in Menu Bar" (18) for Control Center modules on Tahoe+
defaults -currentHost write com.apple.controlcenter Sound -int 18
defaults -currentHost write com.apple.controlcenter FocusModes -int 18
defaults -currentHost write com.apple.controlcenter KeyboardBrightness -int 18

# Set Chrome as default browser
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerContentType="public.html";LSHandlerRoleAll="com.google.chrome";}'
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerURLScheme="http";LSHandlerRoleAll="com.google.chrome";}'
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerURLScheme="https";LSHandlerRoleAll="com.google.chrome";}'

# Disable Spotlight command+space shortcut
defaults write com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add 64 "<dict><key>enabled</key><false/></dict>"

# Disable .DS_Store on external/network drives
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true

# Crash reporter as notification instead of dialog
defaults write com.apple.CrashReporter DialogType -string "notification"

# Enable TouchID for sudo
if ! grep -q "pam_tid.so" /etc/pam.d/sudo; then
  echo "Enabling TouchID for sudo..."
  sudo sed -i '' '2i\
auth       sufficient     pam_tid.so
' /etc/pam.d/sudo
fi

if [[ -z "${MACOS_SETUP_RUNNING:-}" ]]; then
  killall SystemUIServer 2>/dev/null || true
fi

echo "System defaults applied."
