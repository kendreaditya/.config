---
name: lcsearch
description: Search and read content from leetcode.com — problem catalog, daily challenge, full problem statements with hints and starter code, the Discuss forum (interview experiences, comp posts, layoff threads), and company question-list metadata. Read-only, no auth, no API key. Use when the user wants to look up a LeetCode problem by name/number/slug, see today's daily challenge, search Discuss for interview write-ups at a specific company (Google, Waymo, Meta, Amazon, etc.), browse a tag-filtered discuss feed, read a Discuss post + comments, or check what a LeetCode company list covers. Triggers — "lcsearch", "leetcode search", "search leetcode", "leetcode discuss", "leetcode problem", "daily leetcode", "interview discuss", "what's the leetcode for X", URLs containing leetcode.com/problems/, leetcode.com/discuss/, or leetcode.com/company/. Pair with the `interviewcoder` skill (structured leetcode-style writeups from 1point3acres) and `blind` (anonymous workplace chatter) for the same companies.
---

# lcsearch — LeetCode search & read

Read-only CLI for leetcode.com. Wraps `scripts/lcsearch.py`, a
single-file Python tool that hits LeetCode's REST problem catalog and
a small whitelist of public GraphQL operations. No login, no cookies,
no API key.

## Invocation

The script is on `$PATH` as `lcsearch` (symlinked from
`~/.config/scripts/`). Use that short form in examples. Falls back to
`python3 scripts/lcsearch.py` from a fresh environment. Standard
library only — no `pip install` step.

```
lcsearch --help
```

The first `search` or `list` call populates a 24h disk cache at
`~/.cache/leetcode/problems.json` (~3MB) — the full problem catalog
from `/api/problems/all/`. Subsequent searches are instant.

## Commands

### daily — today's daily coding challenge

```
lcsearch daily [--json]
```

Returns the problem id, title, difficulty, and URL for today's daily.

### problem — full problem statement

```
lcsearch problem <slug-or-id-or-url> [--json]
```

Accepts any of:
- Title slug: `two-sum`
- Frontend problem number: `1`
- Full URL: `https://leetcode.com/problems/two-sum/`

Renders the full HTML problem statement (converted to plain
text/markdown), tags, like/dislike counts, AC rate, hints, example
test cases, available code-snippet languages, and similar-question
links.

```
lcsearch problem two-sum
lcsearch problem 56
lcsearch problem https://leetcode.com/problems/merge-intervals/
```

### search — search the problem catalog

```
lcsearch search "<query>" [--difficulty Easy|Medium|Hard] [--paid|--free] [--limit N] [--json]
```

Substring-matches on title and slug across the full catalog (~3,900
problems). Order is the LeetCode REST default (newest first). Also
accepts a bare frontend id as the query.

```
lcsearch search "two sum"
lcsearch search "binary tree" --difficulty Hard --free
lcsearch search 56
```

Note: server-side filtered search (`problemsetQuestionListV2`) is
auth-walled by LeetCode. This skill matches client-side over the
public REST catalog, which is enough for most lookups but doesn't
support filtering by tag.

### list — browse the catalog with filters

```
lcsearch list [--difficulty Easy|Medium|Hard] [--paid|--free] [--limit N] [--json]
```

Same shape as `search` but without a keyword. Useful for skimming
newest-added problems.

### discuss — search the Discuss forum

```
lcsearch discuss "<query>" [--tag SLUG ...] [--order hot|recent|votes] [--limit N] [--json]
```

Searches the LeetCode Discuss forum (`ugcArticleDiscussionArticles`)
by keyword. Each post lists title, author, topicId, ♥ upvotes, 💬 top-
level comment count, 👁 hit count, tags (with `*` marking COMPANY
tags), the canonical URL, and a wrapped summary.

```
lcsearch discuss "waymo interview"
lcsearch discuss "system design" --tag google
lcsearch discuss "compensation" --order recent --limit 10
```

`--order` accepts `hot` (default), `recent`, or `votes`.

### feed — browse the Discuss feed by tag

```
lcsearch feed [tag-slug] [--order hot|recent|votes] [--limit N] [--json]
```

Like `discuss` with no keyword. Without `[tag-slug]` returns the
global hot/recent/votes feed (3000 posts total per LeetCode). Pass a
tag slug to filter — e.g. `google`, `amazon`, `interview`, `career`,
`compensation`. Find available tags via `lcsearch tags`.

```
lcsearch feed google --order recent --limit 5
lcsearch feed compensation --order hot
lcsearch feed                              # global feed
```

### read — full discuss post + comments

```
lcsearch read <topic-id-or-url> [--order best|hot|recent|votes] [--limit N] [--json]
```

Accepts a bare numeric `topicId` or a `/discuss/topic/<id>` URL.
Renders the title, metadata, full body, and the top `--limit`
comments. Post-slug URLs (`/discuss/post/<slug>/`) do NOT carry a
numeric id — find the topicId via `lcsearch discuss "<title fragment>"` first.

```
lcsearch read 7949696
lcsearch read https://leetcode.com/discuss/topic/7949696/
```

Comment ordering vocabulary differs from the feed (`best` is the
LeetCode default; `recent` maps to `newest_to_oldest`, `votes` maps
to `most_votes`). The `--order` flag handles the translation.

### comments — just the comments

```
lcsearch comments <topic-id-or-url> [--order ...] [--limit N] [--json]
```

Same as `read` but skips the post body — useful for re-checking
replies on a thread you've already read.

### company — company list metadata

```
lcsearch company <slug> [--json]
```

Returns metadata for a `/company/<slug>/` page: name, total question
count, collect count, the sub-list slugs (`<slug>-thirty-days`,
`<slug>-three-months`, etc.), curated roles, and a clear note that
the actual problem list is paywalled by LeetCode Premium.

```
lcsearch company waymo
lcsearch company google
lcsearch company meta
```

The actual question list for a company (`favoriteQuestionList`) is
premium-only — anonymous calls return an empty list. This skill
deliberately surfaces only the public metadata.

### tags — hot discussion tags

```
lcsearch tags [--json]
```

Lists currently-trending Discuss tags with sample posts. Use this to
find a valid `--tag` value for `feed`.

### export — dump a discuss post to md or json

```
lcsearch export <topic-id-or-url> [--format md|json] [--limit N]
```

Writes a self-contained Markdown (default) or JSON document to
stdout. `--limit` caps comment count. Useful for archiving
interview-experience threads you want to keep around.

```
lcsearch export 7949696 --format md > waymo-interview.md
lcsearch export 7949696 --format json > waymo-interview.json
```

### export-problem — dump a problem to md or json

```
lcsearch export-problem <slug-or-id> [--format md|json]
```

Writes the full problem (statement, hints, similar questions, all
code snippets) to stdout.

```
lcsearch export-problem two-sum > two-sum.md
lcsearch export-problem 1 --format json > two-sum.json
```

## Common flags (work on every command)

- `--json` — emit structured JSON instead of pretty text. Pipe into
  `jq` or load into Python.
- `--limit N` — cap output to N items (problems, posts, or comments).
- `-v` / `--verbose` — log fetched URLs to stderr for debugging.

Common flags must appear **after** the subcommand name, e.g.
`lcsearch discuss "google" --limit 5`.

## How to choose the right command

| User intent | Command |
|---|---|
| "What's today's LeetCode daily?" | `daily` |
| "Show me LeetCode {problem name/number}" | `problem {name}` |
| "Find LeetCode problems about {topic}" | `search "{topic}"` |
| "What are Hard problems on tree-DP?" | `search "tree" --difficulty Hard` (then filter mentally — tag filter is auth-walled) |
| "What's been posted on LeetCode discuss about {company}?" | `discuss "{company}"` or `feed {company-slug}` |
| "Show me the {company} discuss feed" | `feed {slug}` (slug from `tags`) |
| "Read the LeetCode post at {url}" | `read {url}` |
| "What's hot on LeetCode discuss right now?" | `feed --order hot` |
| "Recent interview experiences at Google" | `feed google --order recent` |
| "Save this discuss thread" | `export {topic-id} --format md > file.md` |
| "Save this problem with starter code" | `export-problem {slug} --format md > file.md` |
| "What companies has LeetCode curated lists for?" | `company {slug}` (try common slugs: google, meta, amazon, microsoft, apple, nvidia, waymo, openai, anthropic) |

When the user gives a `leetcode.com/problems/...` URL → `problem`.
When they give a `leetcode.com/discuss/topic/<id>` URL → `read`.
When they describe a topic → `search` (problems) or `discuss` (forum).
When they name a company → `feed <slug>` (forum) or `company <slug>` (curated list).

## Cross-skill pairings

- **`interviewcoder`** — structured leetcode-style question writeups
  sourced from 1point3acres, tagged by company/stage/period. Use it
  for the question text, then `lcsearch discuss "{company}"` for
  candidate-side commentary.
- **`blind`** — anonymous Blind chatter on the same companies.
  Layoffs, severance, comp data points. Pair both when a user is
  prepping for a specific employer.
- **`forage` / `reddit`** — broader experiential search if neither of
  the above has hits.

## Data schema (JSON output)

**Problem** (from `search`, `list`, `daily`):
`id`, `frontend_id`, `title`, `title_slug`, `difficulty`, `paid_only`,
`ac_rate`, `total_accepted`, `total_submitted`, `url`, `tags[]`.

**ProblemDetail** (from `problem`, `export-problem`): wraps `Problem`
plus `content_html`, `content_text`, `hints[]`, `likes`, `dislikes`,
`similar_questions[]`, `example_testcases`, `code_snippets[]` (each
with `lang`, `lang_slug`, `code`).

**DiscussPost** (from `discuss`, `feed`):
`topic_id`, `uuid`, `title`, `slug`, `summary`, `author`,
`author_slug`, `created_at` (ISO8601), `hit_count`, `upvotes`,
`comment_count`, `tags[]` (each `{name, slug, type}` — type is
`COMPANY` for company tags, else null), `url`.

**Article** (from `read`, `export`): `post` (DiscussPost without
inlined body), `content` (full body), `comments[]`,
`total_comment_count`. Each `Comment` has `id`, `author`, `content`,
`created_at`, `vote_count`, `num_children`, `pinned`.

**CompanyInfo** (from `company`): `slug`, `name`, `description`,
`question_count`, `collect_count`, `is_public`, `favorite_type`,
`last_modified`, `creator`, `generated_slugs[]`,
`position_role_tags[]`, `url`.

## Limitations

- **No login.** LeetCode auth-walls a lot — `problemsetQuestionListV2`
  (filtered problem search by tag), `favoriteQuestionList` for company
  slugs (the actual problems on a company page), submissions, your
  own progress, and anything personalized. This skill deliberately
  exposes only what works anonymously.
- **Problem-list filtering** is client-side over the cached REST
  catalog. Difficulty and paid/free filters work; tag filtering does
  not (the tag list isn't in the REST payload).
- **First page only** for `discuss` and `feed` per call (50 max per
  LeetCode's first-page cap). Pagination beyond `skip=0` is not
  exposed.
- **No write operations.** No posting, no commenting, no voting, no
  bookmarking, no submissions.
- **No replies.** `read` returns top-level comments only. The reply
  count (`num_children`) is shown, but to read the replies the user
  has to open the URL.
- **No reactions detail.** Only upvote count is surfaced; LeetCode's
  full reaction palette (downvotes etc.) is in the raw payload but
  filtered out.

## Error handling

The script exits with:
- `0` on success
- `1` on errors (network, GraphQL error, parse failure)
- `2` on "not found" — bad problem slug, bad topic id, empty search

GraphQL operations that turn out to require auth will fail with a
clear `error: requires authentication` message naming the operation.
