---
name: tiktok-search
description: Search TikTok videos and extract rich data including descriptions, on-screen text (stickers), tagged locations (POI), engagement stats, and spoken word transcripts (WebVTT captions). Use when the user wants to search TikTok, find TikTok videos, get TikTok transcripts, extract TikTok content, or analyze TikTok search results. Triggers on "tiktok", "search tiktok", "tiktok videos", "tiktok transcript".
---

# TikTok Search

Search TikTok videos via the unofficial API (davidteather/TikTok-Api) and extract all available data sources per video.

## Setup

Run once to install dependencies into the shared config-venv:

```bash
bash ~/.config/claude/skills/tiktok-search/scripts/setup.sh
```

## Usage

Activate the venv, then run the search script:

```bash
source ~/.config/config-venv/bin/activate && python ~/.config/claude/skills/tiktok-search/scripts/tiktok_search.py "search query" [options]
```

### Options

| Flag | Description |
|------|-------------|
| `-n COUNT` | Number of results (default: 10) |
| `--json` | Output as JSON |
| `--verbose` | Show full transcripts (default truncates to 300 chars) |
| `--details` | Also hit the detail endpoint per video (slower, sometimes richer data) |
| `--no-transcripts` | Skip downloading WebVTT captions |
| `-o FILE` | Save JSON results to file |

### Examples

```bash
# Basic search
python scripts/tiktok_search.py "bay area hikes swimming holes"

# JSON output with 20 results
python scripts/tiktok_search.py "best restaurants SF" -n 20 --json

# Save to file for further processing
python scripts/tiktok_search.py "camping california" -n 15 -o results.json

# Full transcripts, richer data
python scripts/tiktok_search.py "cooking pasta" --verbose --details
```

## Data Sources Per Video

Each result extracts from four sources. See [references/api_fields.md](references/api_fields.md) for full field details.

| Source | Field | Availability | Content |
|--------|-------|-------------|---------|
| Description | `desc` | Always | Creator-typed caption + hashtags |
| On-screen text | `stickers_text` | ~40% of videos | Text overlays the creator placed on screen |
| Location | `location` | ~20% of videos | Tagged place name, address, city, category |
| Transcript | `transcript` | ~30% of videos | Full spoken words (WebVTT auto-captions via ASR) |

Additional fields always present: `stats` (views/likes/comments/shares/saves), `author`, `hashtags`, `music`, `duration_sec`, `url`.

## JSON Output Schema

```json
{
  "id": "7518987605573111054",
  "url": "https://www.tiktok.com/@user/video/7518987605573111054",
  "description": "Too good to gate keep...",
  "author": {"username": "user", "nickname": "Name", "verified": false, "followers": 1234},
  "stats": {"views": 61300, "likes": 1275, "comments": 42, "shares": 15, "saves": 200},
  "duration_sec": 25,
  "create_time": 1750650753,
  "hashtags": ["santacruz", "california"],
  "stickers_text": ["Santa Cruz swimming hole", "Garden of Eden"],
  "location": {"name": "Henry Cowell Redwoods", "address": "101 N Big Trees Park Rd", "city": "Scotts Valley", "category": "Outdoors", "type": "Nature Park"},
  "music": {"title": "hospital beach", "author": "Artist", "original": false},
  "caption_available": true,
  "transcript": "WEBVTT\n\n00:00:00.140 --> 00:00:03.220\nDay 4 proving...",
  "caption_language": "eng-US"
}
```

## Notes

- No API key or auth required. Uses Playwright browser sessions to bypass bot detection.
- Optional `ms_token` env var (from TikTok browser cookies) helps avoid rate limits.
- Caption URLs expire in ~24h. Transcripts are downloaded at search time.
- The search endpoint is the most reliable. The detail endpoint gets bot-detected more aggressively.
- For videos without captions, consider the `openai-whisper` skill as a fallback for local transcription.
