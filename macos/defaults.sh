#!/bin/bash
# macos/defaults.sh — System-wide macOS defaults
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

# Tap to click.
#
# Three domains, because each input device reads its own:
#   AppleMultitouchTrackpad            — BUILT-IN trackpad (MacBook). Was missing
#                                        here, so tap-to-click silently stayed off
#                                        on laptops no matter how often this ran.
#   AppleBluetoothMultitouch.trackpad  — external Magic Trackpad.
#   NSGlobalDomain com.apple.mouse.tapBehavior (-currentHost) — the global toggle
#                                        System Settings mirrors; per-machine, hence
#                                        -currentHost.
defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true
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

# Menu Bar Settings.
#
# Tahoe (macOS 26) renamed the Control Center visibility keys from
# "NSStatusItem Visible <mod>" to "NSStatusItem VisibleCC <mod>" and migrated
# existing values once (com.apple.controlcenter HasAttemptedMenuBarWorkflowMigration=1).
# The old names are inert for bento-box modules on Tahoe, so the four below were
# no-ops here for months. Both families are written: VisibleCC for Tahoe+, the
# legacy names as a pre-26 fallback. Writing a key the running OS ignores is
# harmless, so this stays correct in both directions.
#
# Bluetooth and NowPlaying are separate status items, NOT bento-box modules — they
# still read the legacy "Visible " name on Tahoe (verified in the live plist), so
# they intentionally get only that form.
for mod in Sound Battery FocusModes KeyboardBrightness; do
  defaults write com.apple.controlcenter "NSStatusItem VisibleCC $mod" -bool true
  defaults write com.apple.controlcenter "NSStatusItem Visible $mod" -int 1
done
defaults write com.apple.controlcenter "NSStatusItem Visible Bluetooth" -int 1
defaults write com.apple.controlcenter "NSStatusItem Visible NowPlaying" -int 1
defaults write com.apple.controlcenter BatteryShowPercentage -bool true

# Show seconds in the menu bar clock
defaults write com.apple.menuextra.clock ShowSeconds -bool true

# Hide the Spotlight (magnifying glass) menu bar icon.
# Equivalent to System Settings > Control Center > Spotlight > "Don't Show in Menu Bar".
# Spotlight.app owns this key and flushes its in-memory copy back to disk on exit, so it
# must be quit BEFORE the write or the new value is silently overwritten. Only hides the
# icon — the search UI itself is unaffected.
killall Spotlight 2>/dev/null || true
sleep 1
defaults write com.apple.Spotlight "NSStatusItem VisibleCC Item-0" -bool false
open -a /System/Library/CoreServices/Spotlight.app 2>/dev/null || true

# Force "Always Show in Menu Bar" (18) for Control Center modules on Tahoe+
defaults -currentHost write com.apple.controlcenter Sound -int 18
defaults -currentHost write com.apple.controlcenter FocusModes -int 18
defaults -currentHost write com.apple.controlcenter KeyboardBrightness -int 18

# Set Chrome as default browser.
#
# This previously used `defaults write com.apple.LaunchServices/... LSHandlers
# -array-add`, which never worked: lsd owns that array and rewrites the whole plist
# from its own database, discarding hand-injected entries. (It also wrote the bundle
# ID as "com.google.chrome" — the real one is "com.google.Chrome", case-sensitive.)
# duti goes through the LSSetDefaultHandlerForURLScheme API instead, so lsd records
# the change itself and it survives.
#
# Quirks worth knowing, both confirmed on macOS 26:
#   - `duti -s <id> http` sets BOTH http and https (they're one web-browser role).
#     Passing `https` explicitly always fails with error -54, so we never ask for it.
#   - Passing a role arg to a URL scheme fails with -50; roles apply only to UTIs,
#     hence the bare scheme here but `all` on public.html.
# Idempotent: re-running is a no-op that still exits 0.
if command -v duti &>/dev/null; then
  if [ -d "/Applications/Google Chrome.app" ] || [ -d "$HOME/Applications/Google Chrome.app" ]; then
    echo "Setting Chrome as default browser..."
    duti -s com.google.Chrome http >/dev/null || echo "  WARN: could not set http handler"
    duti -s com.google.Chrome public.html all >/dev/null || echo "  WARN: could not set public.html handler"
  else
    echo "  Chrome not installed — leaving default browser alone."
  fi
else
  echo "  WARN: duti not installed (brew install duti) — default browser not set."
fi

# Disable Spotlight command+space shortcut
defaults write com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add 64 "<dict><key>enabled</key><false/></dict>"

# Disable .DS_Store on external/network drives
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true

# Crash reporter as notification instead of dialog
defaults write com.apple.CrashReporter DialogType -string "notification"

# Enable TouchID for sudo.
#
# Two places matter, and we write both:
#
#  1. /etc/pam.d/sudo_local — Apple's supported hook. /etc/pam.d/sudo already ends
#     with `auth include sudo_local`, and sudo_local is NOT replaced by macOS
#     updates, so TouchID configured here survives an OS upgrade.
#  2. /etc/pam.d/sudo — kept for older macOS releases that predate the sudo_local
#     include. pam_tid is `sufficient`, so having it in both files is harmless:
#     the first match wins and the second is never consulted.
#
# Note this only affects sudo invoked from a real TTY. A GUI/non-TTY sudo falls back
# to macOS's graphical askpass panel, which collects a password directly and never
# runs the PAM stack — so it stays password-only no matter what's configured here.
if [ -f /etc/pam.d/sudo_local ] && grep -q "^auth.*pam_tid.so" /etc/pam.d/sudo_local; then
  : # already enabled in the update-safe location
else
  echo "Enabling TouchID for sudo (sudo_local)..."
  printf 'auth       sufficient     pam_tid.so\n' | sudo tee -a /etc/pam.d/sudo_local >/dev/null
fi

if ! grep -q "pam_tid.so" /etc/pam.d/sudo; then
  echo "Enabling TouchID for sudo (/etc/pam.d/sudo, legacy fallback)..."
  sudo sed -i '' '2i\
auth       sufficient     pam_tid.so
' /etc/pam.d/sudo
fi

if [[ -z "${MACOS_SETUP_RUNNING:-}" ]]; then
  killall SystemUIServer 2>/dev/null || true
fi

echo "System defaults applied."
