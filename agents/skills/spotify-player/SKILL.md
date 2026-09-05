---
name: spotify-player
description: Terminal Spotify playback/search via spogo (preferred) or spotify_player.
homepage: https://www.spotify.com
metadata: {"clawdbot":{"emoji":"🎵","requires":{"anyBins":["spogo","spotify_player"]},"install":[{"id":"brew","kind":"brew","formula":"spogo","tap":"steipete/tap","bins":["spogo"],"label":"Install spogo (brew)"},{"id":"brew","kind":"brew","formula":"spotify_player","bins":["spotify_player"],"label":"Install spotify_player (brew)"}]}}
upstream:
  repo: openclaw/openclaw
  path: skills/spotify-player/SKILL.md
  ref: main
  sha: 246adaa1191438b9e9e178384a026b4c123782f1
  checked: 2026-09-05
  content_hash: 4a7a735fe86c25c51c589f1c59890b8ae8d83ed6663bef57e8b0252e4ab0b1fc
---

# spogo / spotify_player

Use `spogo` **(preferred)** for Spotify playback/search. Fall back to `spotify_player` if needed.

Requirements
- Spotify Premium account.
- Either `spogo` or `spotify_player` installed.

spogo setup
- Import cookies: `spogo auth import --browser chrome`

Common CLI commands
- Search: `spogo search track "query"`
- Playback: `spogo play|pause|next|prev`
- Devices: `spogo device list`, `spogo device set "<name|id>"`
- Status: `spogo status`

spotify_player commands (fallback)
- Search: `spotify_player search "query"`
- Playback: `spotify_player playback play|pause|next|previous`
- Connect device: `spotify_player connect`
- Like track: `spotify_player like`

Notes
- Config folder: `~/.config/spotify-player` (e.g., `app.toml`).
- For Spotify Connect integration, set a user `client_id` in config.
- TUI shortcuts are available via `?` in the app.
