---
name: youtube
description: "Search YouTube, list channel videos/shorts, get video metadata, and download subtitles via yt-dlp. Triggers: 'youtube search', 'find videos about', 'yt search', 'list channel videos', 'get subtitles', 'youtube transcript', 'yt-dlp', 'what does this channel post', 'video metadata', 'browse youtube shorts'."
---

# YouTube (yt-dlp)

Requires `yt-dlp` and `jq`. No API keys.

## Search

```bash
# Basic — adjust number after ytsearch for result count
yt-dlp "ytsearch10:query" --dump-json --flat-playlist --no-warnings 2>/dev/null \
  | jq -s '.[] | {title, url, channel, views: .view_count, duration: .duration_string, date: .upload_date}'

# Sort by views (fetch 20, take top 10)
yt-dlp "ytsearch20:query" --dump-json --flat-playlist --no-warnings 2>/dev/null \
  | jq -s 'sort_by(-.view_count) | .[:10][] | {title, url, channel, views: .view_count, date: .upload_date}'

# Sort by date (newest first)
... | jq -s 'sort_by(-.upload_date) | .[:10][] | ...'

# Filter by duration (>10min = 600s, <4min = 240s)
... | jq -s '[.[] | select(.duration >= 600)] | sort_by(-.view_count) | .[:10][]'

# Filter by recency (last 30 days)
CUTOFF=$(date -v-30d +%Y%m%d 2>/dev/null || date -d "30 days ago" +%Y%m%d)
yt-dlp "ytsearch20:query" --dump-json --flat-playlist --no-warnings 2>/dev/null \
  | jq -s --arg cutoff "$CUTOFF" '[.[] | select(.upload_date >= $cutoff)] | sort_by(-.view_count) | .[]'

# URLs only (for piping into other tools)
yt-dlp "ytsearch10:query" --dump-json --flat-playlist --no-warnings 2>/dev/null | jq -r '.url'
```

## Channel listing

```bash
# Videos
yt-dlp --dump-json --flat-playlist --no-warnings "https://www.youtube.com/@ChannelName/videos" 2>/dev/null \
  | jq '{id, title, url, views: .view_count, duration: .duration_string, date: .upload_date}'

# Shorts
yt-dlp --dump-json --flat-playlist --no-warnings "https://www.youtube.com/@ChannelName/shorts" 2>/dev/null \
  | jq '{id, title, url, views: .view_count, date: .upload_date}'

# Both combined, sorted by date
{ yt-dlp --dump-json --flat-playlist --no-warnings "https://www.youtube.com/@ChannelName/videos" 2>/dev/null; \
  yt-dlp --dump-json --flat-playlist --no-warnings "https://www.youtube.com/@ChannelName/shorts" 2>/dev/null; } \
  | jq -s 'sort_by(-.upload_date) | .[] | {id, title, url, views: .view_count, date: .upload_date}'
```

Works with `@handle`, full channel URLs, or `/c/ChannelName`.

## Playlist listing

```bash
yt-dlp --dump-json --flat-playlist --no-warnings "https://www.youtube.com/playlist?list=PLxxxxx" 2>/dev/null \
  | jq '{id, title, url, duration: .duration_string, views: .view_count}'
```

## Full video metadata

Drop `--flat-playlist` for rich metadata (slower, ~1-2s/video). Includes likes, comments, subscriber count, description.

```bash
# Single video
yt-dlp --dump-json --no-download --no-warnings "https://www.youtube.com/watch?v=VIDEO_ID" 2>/dev/null \
  | jq '{title, channel, views: .view_count, likes: .like_count, comments: .comment_count, subs: .channel_follower_count, duration: .duration_string, date: .upload_date, description: (.description // "" | .[0:300])}'

# From search (slow)
yt-dlp "ytsearch5:query" --dump-json --no-download --no-warnings 2>/dev/null \
  | jq '{title, url, channel, views: .view_count, likes: .like_count, subs: .channel_follower_count, date: .upload_date}'
```

## Subtitles

```bash
# Download auto-generated English subs
yt-dlp --write-auto-sub --sub-lang "en" --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL"

# Prefer manual subs, fall back to auto
yt-dlp --write-sub --write-auto-sub --sub-lang "en,en-US,en-GB" --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL"

# List available subtitle languages
yt-dlp --list-subs --no-warnings "URL" 2>/dev/null

# Get subtitle track info as JSON
yt-dlp --dump-json --no-download --no-warnings "URL" 2>/dev/null \
  | jq '{manual: (.subtitles | keys), auto: (.automatic_captions | keys)}'
```

VTT files saved to `/tmp/VIDEO_ID.LANG.vtt`. Clean with `vtt2txt` (from the `clean` skill):

```bash
# Download subs + clean to plain text
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL" && vtt2txt /tmp/VIDEO_ID.en.vtt

# Download subs + clean to markdown with metadata
vtt2txt /tmp/VIDEO_ID.en.vtt --md --title "Video Title" --id "VIDEO_ID" -o transcript.md

# Batch: multiple VTTs to one markdown
vtt2txt /tmp/*.vtt --md --heading "Research" -o combined.md
```

## Key fields reference

**Flat mode** (`--flat-playlist`): `title`, `id`, `url`, `channel`, `view_count`, `duration`, `duration_string`, `upload_date`, `description`

**Full mode** (no `--flat-playlist`): adds `like_count`, `comment_count`, `channel_follower_count`, `subtitles`, `automatic_captions`

Null fields are common — handle with jq `// ""` or `// 0`.

## Errors

| Error | Fix |
|-------|-----|
| No results | Broaden query |
| Empty JSON / timeout | Rate limited — wait, reduce count |
| 429 | Add delays, reduce batch size |
| `yt-dlp: command not found` | `uv tool install yt-dlp` or `pip install yt-dlp` |
