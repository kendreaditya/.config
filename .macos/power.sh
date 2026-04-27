#!/bin/bash
# .macos/power.sh — pmset power management profile
# Battery: aggressive display sleep + system sleep to save power
# AC: longer display sleep, never auto-sleep (keeps builds/SSH/downloads alive)
set -euo pipefail

echo "Applying power management settings..."

sudo pmset -b displaysleep 10 sleep 15 disksleep 10 powernap 0 lessbright 1
sudo pmset -c displaysleep 15 sleep 0  disksleep 10 powernap 1 womp 1

echo "Power settings applied."
