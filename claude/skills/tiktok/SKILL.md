---
name: tiktok
description: Search TikTok videos/users, fetch user profiles and posted videos, get video details/comments/related, explore hashtags, browse trending/FYP, and look up sounds. Extracts descriptions, on-screen text (stickers), tagged locations, engagement stats, and spoken word transcripts (WebVTT). Use when working with TikTok data for any purpose including content research, creator analysis, trend discovery, or transcript extraction. Triggers on "tiktok", "search tiktok", "tiktok user", "tiktok video", "tiktok comments", "tiktok hashtag", "tiktok trending", "tiktok fyp", "tiktok sound", "tiktok music", "tiktok profile", "tiktok transcript".
---

# TikTok

No API key required. Uses Playwright browser sessions via `davidteather/TikTok-Api`.

## Setup

```bash
bash ~/.claude/skills/tiktok/scripts/setup.sh
```

## Invocation

Prefix all commands with venv activation:

```bash
source ~/.config/config-venv/bin/activate && python ~/.claude/skills/tiktok/scripts/<SCRIPT> <COMMAND> <ARGS> [OPTIONS]
```

## Scripts

### tiktok.py — Search videos or users

```bash
# Video search (default when no subcommand given)
tiktok.py "bay area hikes" -n 10 --json
tiktok.py videos "best restaurants SF" -n 20 --verbose --details
# User search
tiktok.py users "food blogger" -n 5 --json
```

### tiktok_user.py — User profile, videos, liked

```bash
tiktok_user.py info "charlidamelio" --json
tiktok_user.py videos "username" -n 20 --json
tiktok_user.py liked "username" -n 10 --json   # only if likes are public
```

Username without `@` prefix.

### tiktok_video.py — Video detail, comments, related

Accepts video ID or full TikTok URL.

```bash
tiktok_video.py info "7518987605573111054" --json
tiktok_video.py comments "https://www.tiktok.com/@user/video/7518987605573111054" -n 50 --json
tiktok_video.py related "7518987605573111054" -n 10 --json
```

### tiktok_hashtag.py — Hashtag stats and videos

```bash
tiktok_hashtag.py info "bayarea" --json
tiktok_hashtag.py videos "foodtok" -n 20 --json
```

Hashtag without `#` prefix.

### tiktok_trending.py — Trending/FYP feed

```bash
tiktok_trending.py -n 20 --json
```

No query needed.

### tiktok_sound.py — Sound info and videos by sound

Sound ID is in the `music.id` field of any video result.

```bash
tiktok_sound.py info "1234567890" --json
tiktok_sound.py videos "1234567890" -n 10 --json
```

## Common Options

| Flag | Effect |
|------|--------|
| `-n COUNT` | Number of results (default: 10) |
| `--json` | JSON output |
| `--verbose` | Full transcripts, untruncated |
| `-o FILE` | Save JSON to file |
| `--details` | Hit detail endpoint per video (slower, richer stickers/subtitles) |
| `--no-transcripts` | Skip WebVTT caption download |

## Important Behaviors

- Optional `ms_token` env var (from TikTok cookies) reduces rate limiting.
- Video results include: `stats`, `author`, `hashtags`, `music`, `stickers_text` (~40%), `location` (~20%), `transcript` (~30%).
- For full field reference and JSON schema, read [references/api_fields.md](references/api_fields.md).
