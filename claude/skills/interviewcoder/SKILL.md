---
name: interviewcoder
description: Search and read posts from interviewcoder.co — a Next.js-fronted aggregator of technical-interview writeups (largely sourced from 1point3acres) tagged by company, position, stage (Phone Screen / OA / Onsite / etc.), period, job type, and structured leetcode-style questions. Use when the user wants real interview questions for a specific company, recent writeups from a hiring loop, leetcode-style problems with tags and difficulty, or to look up a specific interviewcoder.co URL. Read-only, no auth, no API key. Triggers — "interviewcoder", "interviewcoder.co", "interview questions at [company]", "what's been asked at [company] recently", "interview writeup", and URLs containing interviewcoder.co.
---

# Interview Coder

Read-only CLI for interviewcoder.co. Wraps `scripts/interviewcoder.py`,
a single-file Python tool that scrapes the React Server Components
(Flight) payload embedded in each page. No login, no cookies, no
encryption.

Pair with the `blind` skill for opinion/chatter on the same company —
this skill is the structured-question source.

## Invocation

The script is on `$PATH` as `interviewcoder` (symlinked from
`~/.config/scripts/`). Use that short form in examples. Falls back to
`python3 scripts/interviewcoder.py` if invoking from a fresh
environment.

Standard library only — no `pip install` step.

```
interviewcoder --help
```

## Commands

### list — page of questions (filterable)

```
interviewcoder list \
    [--company NAME] [--job-type TYPE] [--stage STAGE] \
    [--outcome OUT] [--sort SORT] [--page N] [--limit N] [--json]
```

Return one page of posts. Each post carries title, company, position,
period, job type, interview stage, author, engagement counts, a
content snippet, and the structured questions (with difficulty and
tags).

Examples:

```
interviewcoder list --company Apple --limit 5
interviewcoder list --company Amazon --sort most-bookmarked
interviewcoder list --job-type Intern --limit 5
interviewcoder list --company ByteDance --page 2
```

Known filter values seen in the wild:

- `--job-type`: `Fulltime`, `Intern`
- `--stage`: `Phone Screen`, `OA`, `Onsite`, `Technical Interview`, `HR`
- `--sort`: `oldest`, `most-bookmarked` (default is newest)
- `--company`: use the value as it appears on the site (e.g. `Apple`,
  `Amazon`, `ByteDance`, `Capital One`, `Capitalone`, `Applied-Intuition`,
  `Boston-Consulting-Group`). Run `companies` first if unsure of the
  exact spelling — some companies appear under multiple aliases.

The output header shows `page X/Y` so paginate with `--page`.

### read — fetch one post + its structured questions

```
interviewcoder read <id-or-url> [--json]
```

Accept a bare UUID or any URL containing one (the `/questions/{uuid}`
path). Render the full post body (markdown), metadata, and each
structured question with difficulty, tags, and `leetcode_ref`.

```
interviewcoder read c2e84e3e-a0ee-415e-ae9f-db56988b85fb
interviewcoder read https://www.interviewcoder.co/questions/c2e84e3e-a0ee-415e-ae9f-db56988b85fb
```

If `hasAccess` is false (the site paywalls some features for
logged-out users) the script prints a note. The post body is still
returned in full — only UI features like bookmarking are gated.

### companies — company directory with counts

```
interviewcoder companies [--limit N] [--json]
```

List every company with at least one post, ordered by count
descending. Run this before `list --company` if uncertain of the exact
spelling.

### search — client-side search across recent pages

```
interviewcoder search "<query>" [--company NAME] [--pages N] [--limit N] [--json]
```

No server-side full-text search exists, so this fetches the first
`--pages` pages (default 3) and substring-matches against title,
content snippet, question titles, and tags. Combine with `--company`
to narrow before searching.

```
interviewcoder search "system design" --company Amazon --pages 2
interviewcoder search "binary search" --pages 5 --limit 10
```

Slow for wide scans — each page is one HTTP fetch.

### export — dump one post to md or json

```
interviewcoder export <id-or-url> [--format md|json]
```

Write a self-contained Markdown (default) or JSON document to stdout.

```
interviewcoder export c2e84e3e-... --format md > apple-phone.md
interviewcoder export c2e84e3e-... --format json > apple-phone.json
```

## Common flags (work on every command except `export`)

- `--json` — structured JSON instead of pretty text. The post schema
  is the `Post` dataclass (see below). Pipe into `jq`.
- `--limit N` — cap output to N items.
- `-v` / `--verbose` — log fetched URLs to stderr.

Common flags must appear **after** the subcommand name, e.g.
`interviewcoder list --company Apple --limit 5`.

## How to choose the right command

| User intent | Command |
|---|---|
| "What questions have been asked at {company}?" | `list --company {Name}` |
| "Show me {company}'s top bookmarked writeups" | `list --company {Name} --sort most-bookmarked` |
| "Most recent intern interviews" | `list --job-type Intern` |
| "Show me the full writeup at {url}" | `read {url}` |
| "Which companies are covered? How many posts each?" | `companies` |
| "Find writeups mentioning system design / binary search / etc." | `search "{query}"` |
| "Save this writeup for later" | `export {url} --format md > file.md` |

## Data schema

**Post** (returned by `list`, `search`, and as `.post` from `read`):
`id`, `title`, `author`, `company`, `position`, `period`, `job_type`,
`user_type`, `interview_stage`, `outcome`, `content`,
`posted_at_original`, `created_at`, `url` (canonical
interviewcoder.co URL), `source_url` (1point3acres etc.), `category`,
`views_count`, `likes_count`, `bookmarks_count`, `comments_count`,
`questions[]`.

**Question** (inside `Post.questions`): `id`, `question_number`,
`title`, `description`, `difficulty` (Easy / Medium / Hard / null),
`leetcode_ref`, `tags[]`, `created_at`.

**Article** (returned by `read`): `post` (Post), `markdown` (the
formatted long-form body), `has_access` (bool), `is_authenticated`
(bool).

## Limitations

- **First page only** on `list` per call — use `--page N` to paginate.
- **No server-side search** — `search` fans out across pages
  client-side. Slow for wide scans.
- **No write operations.** No login, no posting, no bookmarking.
  Logged-in features (`hasAccess=true` posts, personal bookmarks)
  would require defeating the auth flow — out of scope.
- **Posts are scraped from 1point3acres.** The `source_url` field
  on each post points at the original thread; the interview text
  is often translated and reformatted.

## Error handling

The script exits with:
- `0` on success
- `1` on errors (network, parse failure, etc.)
- `2` on "not found" — bad post id or 404
