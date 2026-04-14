#!/bin/bash
# install.sh — bootstrap script for kendreaditya/.config
# Usage: curl -sSL https://raw.githubusercontent.com/kendreaditya/.config/main/install.sh | bash

set -e

REPO="https://github.com/kendreaditya/.config.git"
DEST="$HOME/.config"

# Detect platform
UNAME="$(uname)"
case "$UNAME" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)
    echo "Error: unsupported platform '$UNAME'." >&2
    echo "On Windows, run the PowerShell bootstrap instead:" >&2
    echo "  irm https://raw.githubusercontent.com/kendreaditya/.config/main/install.ps1 | iex" >&2
    exit 1
    ;;
esac

echo "==> .config dotfiles bootstrap (platform: $PLATFORM)"

# Prerequisites per platform
if [ "$PLATFORM" = "macos" ]; then
  if ! xcode-select -p &>/dev/null; then
    echo "==> Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "    Re-run this script after the installer finishes."
    exit 0
  fi
elif [ "$PLATFORM" = "linux" ]; then
  if ! command -v git &>/dev/null; then
    echo "==> Installing git..."
    if command -v apt &>/dev/null; then
      sudo apt update && sudo apt install -y git curl
    elif command -v dnf &>/dev/null; then
      sudo dnf install -y git curl
    elif command -v pacman &>/dev/null; then
      sudo pacman -S --noconfirm git curl
    else
      echo "Error: no supported package manager found (apt/dnf/pacman)." >&2
      exit 1
    fi
  fi
fi

# Clone or update the repo
if [ -d "$DEST/.git" ]; then
  echo "==> Updating existing repo at $DEST"
  git -C "$DEST" pull --ff-only
else
  if [ -d "$DEST" ] && [ "$(ls -A "$DEST")" ]; then
    echo "==> $DEST exists but is not a git repo — backing up to ${DEST}.bak"
    mv "$DEST" "${DEST}.bak"
  fi
  echo "==> Cloning $REPO → $DEST"
  git clone "$REPO" "$DEST"
fi

# Hand off to the platform setup script
SCRIPT="$DEST/setup-${PLATFORM}.sh"
echo "==> Running $(basename "$SCRIPT")"
bash "$SCRIPT"
