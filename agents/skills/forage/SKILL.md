---
name: forage
description: "Cross-platform experiential search across YouTube, TikTok, and Reddit. Use when the user wants to research a topic across multiple platforms, find real human experiences and opinions, discover content about a topic, or needs a comprehensive search beyond Google. Triggers: 'forage', 'search everywhere', 'cross-platform search', 'research this topic', 'what are people saying about', 'find me info on', 'deep search', 'experiential search', 'search all platforms'."
---

# Forage

Cross-platform experiential search. Searches real human content across YouTube, TikTok, and Reddit — then synthesizes findings.

## When to use

Use forage for subjective, experience-based queries where real human perspectives matter more than SEO articles:
- "bay area hikes with waterfalls"
- "indian male chest hair grooming"
- "best mechanical keyboard for programming"
- "is mass gainer worth it"

## How it works

For each query, search the relevant platforms **in parallel** (use multiple tool calls), then synthesize.

### Platform selection

Not every query needs every platform. Pick based on query type:

| Query type | Best platforms | Example |
|---|---|---|
| Lifestyle / experiences | TikTok, Reddit, YouTube | "bay area hikes with waterfalls" |
| Product reviews / opinions | Reddit, YouTube, TikTok | "best wireless earbuds under $100" |
| How-to / tutorials | YouTube, Reddit | "chest hair grooming for men" |
| Trending / culture | TikTok, Reddit, YouTube | "what's viral right now in fitness" |
| Technical / niche | Reddit, YouTube | "rust vs go for backend 2026" |

**Default**: Reddit + YouTube + TikTok (all three, every query).

### Search commands

#### Reddit
```bash
reddit-browser search "QUERY" --subreddit SUB --sort relevance --time year --limit 10 --json
reddit-browser comments "<permalink-or-url>" --limit 8 --json   # pull a thread's top comments
```
Use **`reddit-browser`** (at `~/.config/scripts/reddit-browser`) — it returns real
Reddit JSON (`title, subreddit, score, num_comments, permalink, selftext, url`).
Drop `--json` for a human-readable listing. `--subreddit`/`-r` is optional (omit
for a site-wide search). To read a thread's discussion, pass its permalink to the
`comments` subcommand.

**Why this CLI and not `reddit`:** as of 2026-06 Reddit hard-403s every anonymous
`*.json` request, and the Redlib mirrors the old `reddit` CLI fell back to are now
**all dead** behind JS proof-of-work walls (header-spoofing and curl_cffi TLS
impersonation both still 403). `reddit-browser` works around it by driving headless
Chrome to clear the JS challenge and reuse the session cookie — **cold ~7s, warm
~1.3s** (cookie cached 30 min). Needs the `~/.config/config-venv` venv (playwright +
chromium). Run it with that venv active: `source ~/.config/config-venv/bin/activate`.

If you ever add `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` to `~/.config/.env`, the
lighter `reddit` CLI's OAuth path becomes viable again and is faster — but until
then `reddit-browser` is the reliable Reddit leg.

#### YouTube (search + optional transcript)
```bash
# Search
yt-dlp "ytsearch10:QUERY" --dump-json --flat-playlist --no-warnings 2>/dev/null \
  | jq -s 'sort_by(-.view_count) | .[:5][] | {title, url, channel, views: .view_count, date: .upload_date}'

# Get transcript for top result (optional — use when depth matters)
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "VIDEO_URL" && vtt2txt /tmp/VIDEO_ID.en.vtt
```

#### TikTok
```bash
source ~/.config/config-venv/bin/activate && python ~/.claude/skills/tiktok/scripts/tiktok.py "QUERY" -n 10 --details
```
Returns descriptions, stickers text, locations, engagement stats, and transcripts.

### Synthesis

After gathering results from 2-4 platforms, synthesize into a response that:

1. **Leads with the answer** — what did real people say?
2. **Groups by theme** — not by platform. If multiple platforms agree on something, that's a strong signal.
3. **Cites sources** — mention which subreddit, which YouTuber, which TikTok creator said what.
4. **Notes disagreements** — where platforms diverge, call it out.
5. **Ranks by signal strength** — high upvotes on Reddit + high views on YouTube + viral on TikTok = strong consensus.

### Example: "bay area hikes with waterfalls"

**Search plan:**
- Reddit: `r/bayarea`, `r/hiking` — real local recommendations with upvotes
- YouTube: video guides showing the actual trails
- TikTok: short clips of the hikes, tagged locations

**Parallel execution:**
```bash
# Reddit
reddit-browser search "bay area hikes waterfalls" --sort relevance --time year --limit 10 --json

# YouTube
yt-dlp "ytsearch10:bay area hikes waterfalls" --dump-json --flat-playlist --no-warnings 2>/dev/null \
  | jq -s 'sort_by(-.view_count) | .[:5][]'

# TikTok
source ~/.config/config-venv/bin/activate && python ~/.claude/skills/tiktok/scripts/tiktok.py "bay area hikes waterfalls" -n 10 --details
```

**Synthesize:** Combine Reddit's "Alamere Falls is the best but crowded" + YouTube's trail walkthrough + TikTok's location tags into a ranked recommendation list.

### Example: "indian male chest hair grooming"

**Search plan:**
- Reddit: grooming subreddits — real experiences, product recs
- YouTube: tutorial videos with view counts
- TikTok: short grooming tips, product demos

## Tips

- **Parallel is key** — launch Reddit + YouTube + TikTok searches simultaneously
- **Reddit first** — fastest, richest signal, best for gauging if a topic has community discussion
- **YouTube for depth** — grab transcripts when you need detailed how-to or review content
- **TikTok for recency** — most current trends and real-person demonstrations
