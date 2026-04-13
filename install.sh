#!/bin/bash
# install.sh — bootstrap script for kendreaditya/.config
# Usage: curl -sSL https://raw.githubusercontent.com/kendreaditya/.config/main/install.sh | bash

set -e

REPO="https://github.com/kendreaditya/.config.git"
DEST="$HOME/.config"

echo "==> macOS dotfiles bootstrap"

# Verify macOS
if [[ "$(uname)" != "Darwin" ]]; then
  echo "Error: this script is macOS-only." >&2
  exit 1
fi

# Ensure Xcode Command Line Tools are present (provides git, cc, etc.)
if ! xcode-select -p &>/dev/null; then
  echo "==> Installing Xcode Command Line Tools..."
  xcode-select --install
  echo "    Re-run this script after the installer finishes."
  exit 0
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

# Hand off to the main setup script
echo "==> Running setup-macos.sh"
bash "$DEST/setup-macos.sh"
