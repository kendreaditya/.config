#!/bin/bash
# Install TikTok skill dependencies into the shared config-venv
set -e

VENV_DIR="$HOME/.config/config-venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: config-venv not found at $VENV_DIR"
    exit 1
fi

source "$VENV_DIR/bin/activate"
pip install -q TikTokApi httpx playwright 2>&1 | tail -3
python -m playwright install chromium 2>&1 | tail -1

echo "Setup complete. Dependencies installed into $VENV_DIR"
