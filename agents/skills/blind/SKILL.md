---
name: blind
description: Search and read posts from Blind (teamblind.com), the anonymous professional network. Use when the user wants to find what tech workers are saying about a topic, company, layoff, severance negotiation, compensation, interview experience, or any workplace gossip — or to fetch a specific Blind article + its comment thread, browse a Blind channel like Layoffs or Tech Industry, or browse a company page like Meta. Triggers: "Blind", "teamblind", "what does Blind say about", "any Blind threads on", "Blind layoffs channel", "Meta page on Blind", URLs containing teamblind.com. Read-only, no auth, no API key. Returns titles, snippets, engagement counts, threaded comments. Note: full post bodies are lazy-loaded by Blind and only available as ~150-char excerpts in this skill; feed listings include up to 300 chars per post.
---

# Blind

Read-only CLI for teamblind.com. Wraps `scripts/blind.py`, a single-file
Python tool that hits Blind's public Next.js RSC payloads — no login,
no cookies, no encryption.

## When to invoke

Reach for this skill whenever the user wants real anonymous tech-worker
discussion on a topic. Blind is the source of truth for layoff rumors,
severance negotiation tactics, comp data points, interview leaks, and
internal-feel gossip about specific companies. If the question is
"what's the chatter on X", "any Blind threads about Y", or contains a
`teamblind.com` URL, use this.

## Setup

Run the script directly with `python3`. No dependencies — stdlib only.
The script is at `scripts/blind.py` relative to this skill's directory.

```
python3 scripts/blind.py --help
```

## Commands

### search — find posts by query

```
python3 scripts/blind.py search "<query>" [--limit N] [--json]
```

Returns first page of search results (typically ~20 posts) with title,
author company tag, like/comment/view counts, ~300-char snippet, and
canonical article URL.

```
python3 scripts/blind.py search "severance negotiation" --limit 5
```

### read — fetch an article + comments

```
python3 scripts/blind.py read <url-or-alias> [--json]
```

Accepts a full Blind URL (`https://www.teamblind.com/article/4dzzibmq`,
`/post/4dzzibmq`, or `/company/<co>/posts/<slug>`) OR a bare alias
(`4dzzibmq`). Renders title, channel, author, body excerpt (~150 chars
— see "Body limitation" below), and the full threaded comment tree
with company tags, OP markers, like counts, and reply nesting.

```
python3 scripts/blind.py read m58k2r2o
python3 scripts/blind.py read https://www.teamblind.com/article/4dzzibmq
```

### feed — browse a channel feed (or home)

```
python3 scripts/blind.py feed [channel] [--since DURATION] [--limit N] [--json]
```

Channel names go after `feed` (e.g. `Layoffs`, `Tech-Industry`, `India`).
Omitting the channel returns the home feed. `--since` filters
client-side to posts written within a duration like `10m`, `6h`, `2d`,
`1w`. First page only — pagination is not supported.

```
python3 scripts/blind.py feed Layoffs --since 24h
python3 scripts/blind.py feed                    # home
```

If the user gives a channel name that doesn't exist, the script errors
with "no such channel" rather than silently returning the home feed.

### company — browse a company page

```
python3 scripts/blind.py company <Name> [--since DURATION] [--limit N] [--json]
```

Lists posts on a specific company's page. Use the company's URL alias
as Blind has it (e.g. `Meta`, `Google`, `Amazon`, `Salesforce`).

```
python3 scripts/blind.py company Meta --limit 10
python3 scripts/blind.py company Salesforce --since 7d
```

### export — dump article + comments to a file

```
python3 scripts/blind.py export <url-or-alias> [--format md|json]
```

Writes a self-contained Markdown (default) or JSON document to stdout.
Useful for archiving threads the user wants to keep around — Blind
posts get buried fast and accounts can vanish.

```
python3 scripts/blind.py export 4dzzibmq --format md > thread.md
python3 scripts/blind.py export m58k2r2o --format json > thread.json
```

## Common flags (work on every command)

- `--json` — emit structured JSON instead of pretty text. Pipe into `jq`
  or other tooling. Schema is the `Post` / `Article` dataclass.
- `--limit N` — cap output to N items.
- `-v` / `--verbose` — print fetched URLs to stderr for debugging.

Common flags must appear **after** the subcommand name, e.g.
`blind.py feed Layoffs --limit 5` (not `blind.py --limit 5 feed Layoffs`).

## How to choose the right command

| User intent | Command |
|---|---|
| "What's Blind saying about X?" / "Find Blind threads about Y" | `search "<X>"` |
| "What are people on Blind saying about Meta/Google/etc?" | `company <Name>` |
| "Show me the Layoffs channel" / "Tech Industry feed" | `feed <Channel>` |
| "What's hot on Blind right now?" | `feed` (no channel = home) |
| "Read this Blind post: <url>" | `read <url>` |
| "Save/export this Blind thread" | `export <url> --format md` |
| "Show me last 24h of layoffs posts" | `feed Layoffs --since 24h` |

When the user gives a teamblind.com URL, use `read`. When they describe
a topic, start with `search`. When they name a specific company, use
`company`. When they reference a channel/forum, use `feed`.

## Body limitation (important — communicate this to the user)

Blind lazy-loads the full text of long article bodies via a Server
Action that runs after page render. The skill cannot replicate that
without reverse-engineering action hashes (which change every Blind
deploy). Implications:

- **`read` shows ~150 chars of body** (the SEO meta description) plus
  the full comment thread. The output includes a clear warning when
  this happens.
- **Feed/search/company listings show up to 300 chars per post** (Blind
  truncates `content` at 300 in listings, with `contentLength` reporting
  the real total). The renderer appends `[…+N chars]` when truncated.
- **Comments are NOT truncated** — full threaded discussion is always
  available, including like counts, company tags, and reply nesting.
- For the FULL body of a long post, the user has to open the URL in a
  browser. The skill always prints the URL.

In practice this is fine for most Blind use cases because the high-value
content is the comment discussion, and most Blind posts are short
questions or rants under 300 chars anyway. But it's worth telling the
user "I can show you the title, ~150 chars of the post, and all 67
comments — open the URL for the full body" rather than silently
truncating.

## Other limitations

- **First page only** on `search`, `feed`, `company`. No "load more".
- **Default sort only** — `?sort=...` query params don't work on feeds
  (sort is a Server Action). They DO work on a topic-aggregation page
  but not on `/article/<alias>`, so the skill doesn't expose a `--sort`
  flag.
- **Read-only.** No login, no posting, no commenting, no voting, no DMs.
  Those would require defeating Blind's SJCL+RSA encrypted `/api/*`
  endpoints, which is out of scope.
- **Engagement counts** (likes/comments/views) are present in feed
  listings but rendered as compact icons (♥, 💬, 👁).

## Output handling tips

- Default text output is human-readable with tree-indented comments;
  pipe to `less -R` if it's long.
- For programmatic use (counting threads, filtering by company, sorting
  by engagement), always use `--json` and process with `jq` or load
  into Python.
- The JSON `Post` schema has: `alias`, `title`, `content`,
  `content_length`, `author_nickname`, `author_company`, `channel_name`,
  `created_at` (relative, e.g. "4d"), `written_at` (ISO 8601 absolute),
  `like_count`, `comment_count`, `view_count`, `url`.
- The JSON `Article` schema adds: `body`, `body_is_excerpt`, `pinned`
  comment list, `comments` comment tree, `total_comment_count`. Each
  `Comment` has `id`, `parent_id`, `author_nickname`, `author_company`,
  `content`, `like_count`, `is_op`, `replies[]`.

## Error handling

The script exits with:
- `0` on success
- `1` on errors (network, parse failure, etc.)
- `2` on "not found" — bad article alias, nonexistent channel, or
  unknown company page. Blind silently redirects unknown topic names
  to the home feed; the skill detects this via `og:url` and reports
  "no such channel" rather than returning home posts.
