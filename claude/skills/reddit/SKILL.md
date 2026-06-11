---
name: reddit
description: "Search Reddit, browse subreddits, read posts and comments, and look up user activity. Use when the user wants to: search Reddit, find Reddit posts, browse a subreddit, read Reddit comments, check what's trending on Reddit, look up a Reddit user, research a topic on Reddit, get Reddit discussions, or any variation of 'reddit search', 'find posts about', 'what does r/X think about', 'reddit user', 'subreddit'."
---

# Reddit

Search and browse Reddit from the shell via the `reddit` CLI.

```bash
reddit search "<query>" [-r SUB] [--sort relevance|hot|new|top|comments] [--time hour|day|week|month|year|all] [--limit N] [--json] [-v]
reddit subreddit <name> [--sort hot|new|top|rising|controversial] [--time ...] [--limit N] [--json] [-v]
reddit comments <post-url-or-id> [--sort confidence|top|new|controversial|old|qa|best] [--limit N] [--json] [-v]
reddit user <name> [--limit N] [--json] [-v]
```

Exit codes: `0` ok, `1` error, `2` not found. Default `--limit` is 10.

## Why a CLI (and not `curl .../search.json | jq`)

Reddit's public unauthenticated `*.json` endpoints now return **HTTP 403** + an
HTML block page for **every** host (`www`, `old`, `np`, `api`, `reddit.com`,
even `oauth.reddit.com` without a token) and **every** User-Agent — including a
real desktop browser UA. This is a blanket IP/anon block, not transient rate
limiting, so the old `curl '…/search.json' | jq` recipe is dead (it pipes HTML
into jq → parse error). The `reddit` CLI works around it with two backends:

1. **OAuth (preferred, reliable)** — used automatically when credentials are in
   the environment. Gets a userless/application-only (or password-grant) bearer
   token from `https://www.reddit.com/api/v1/access_token`, then reads real JSON
   from `https://oauth.reddit.com/...`.
2. **Redlib HTML fallback (default today, flaky)** — when no creds are present,
   it scrapes a public [Redlib](https://github.com/redlib-org/redlib) instance
   (open-source Reddit frontend) and rotates through a list of instances on
   failure. Redlib renders HTML — it does **not** expose Reddit's `.json` API —
   so the CLI parses the page. **Instance availability is unreliable**: many are
   403/down/behind an anti-bot interstitial at any given moment, and the one
   live instance can rate-limit you under rapid-fire use. The CLI retries once
   on transient errors, then rotates; if everything fails it exits `1` with a
   clear message (never a jq-style crash). Add a `sleep` between rapid calls.

### Make it reliable: add OAuth creds (recommended)

There are currently **no** `REDDIT_*` keys in `~/.config/.env`. To switch to the
reliable OAuth path, register a Reddit app and add the creds:

1. Go to <https://www.reddit.com/prefs/apps> → **create another app...**
2. Choose type **script** (or **installed app** for userless-only). Set the
   redirect URI to `http://localhost:8080` (unused but required).
3. Note the **client id** (the string shown *under* the app name) and the
   **secret**.
4. Add to `~/.config/.env` (git-crypt-encrypted; re-source with
   `source ~/.config/.env`):

   ```bash
   export REDDIT_CLIENT_ID=...
   export REDDIT_CLIENT_SECRET=...
   # Optional — enables the full password grant (more endpoints, higher limits):
   export REDDIT_USERNAME=...
   export REDDIT_PASSWORD=...
   ```

When `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` are present the CLI uses OAuth
automatically — no flag needed. With `REDDIT_USERNAME`/`REDDIT_PASSWORD` it uses
the `password` grant; otherwise the userless `client_credentials` grant. Secrets
are never printed. Run any command with `-v` to confirm which backend/grant is
in use (`backend=oauth` vs `backend=redlib`).

To pin a specific Redlib instance (skip rotation): `export REDLIB_HOST=https://redlib.perennialte.ch`.

## Search all of Reddit

```bash
reddit search "rust vs go backend 2026" --sort relevance --time year --limit 10
```

Sort: `relevance` (default), `hot`, `new`, `top`, `comments`. Time window
(`--time`): `hour|day|week|month|year|all`.

### Search within a subreddit

```bash
reddit search "severance negotiation" -r cscareerquestions --sort new --limit 10
```

## Browse a subreddit

```bash
reddit subreddit cscareerquestions --sort hot --limit 10
reddit subreddit MechanicalKeyboards --sort top --time week --limit 10
```

Sort: `hot` (default), `new`, `top`, `rising`, `controversial`. For `top`, set
`--time`.

## Read a post + comments

Pass a full Reddit URL, a `/r/<sub>/comments/<id>/...` path, a `t3_<id>`, or a
bare post id. Comments come back as a nested tree.

```bash
reddit comments "https://reddit.com/r/csMajors/comments/1lu48je/the_trade_desk_2026_summer_swe/" --limit 20
reddit comments 1lu48je --sort top --limit 20
```

Comment sort: `confidence` (default), `top`, `new`, `controversial`, `old`,
`qa`, `best`.

## User activity

```bash
reddit user spez --limit 10
```

Returns the user's recent posts and comments interleaved.

## JSON output

Every command takes `--json` for structured, parseable output (use this when
piping into other tools or when you need exact fields). Post objects expose
`id, title, subreddit, author, score, num_comments, created_utc, url,
permalink, selftext, is_self`.

```bash
reddit search "trade desk codesignal" --json --limit 5
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `error: all Redlib instances failed` | Expected flakiness. Wait a few seconds and retry; the live instance may be briefly rate-limited. For reliability, add OAuth creds (above) or pin `REDLIB_HOST`. |
| Empty / `(no results)` | Query too narrow, or the live Redlib instance returned a partial page. Retry, or broaden the query. |
| Slow first call | Redlib rotation may try a couple of dead instances before reaching the live one. Pin `REDLIB_HOST` to skip rotation. |
| Want exact counts/scores reliably | Use OAuth — Redlib abbreviates large counts (e.g. `12k`) which the CLI un-abbreviates, but OAuth returns exact integers. |
| `backend=` shows redlib but you set creds | Re-source env: `source ~/.config/.env`, and confirm both `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are set. |

The CLI is a single stdlib-only Python file at
`~/.claude/skills/reddit/scripts/reddit.py`, symlinked onto `$PATH` as `reddit`.
