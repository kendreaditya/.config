---
name: substack
description: "Search Substack newsletters, read posts, browse categories, and get user profiles via the substack CLI. Triggers: 'substack', 'newsletter search', 'substack posts', 'browse newsletters', 'substack categories', 'read substack article', 'substack trending', 'newsletter recommendations'."
---

# Substack

Requires `substack` CLI (`uv tool install substack-api`). No API keys for public content. All output is JSON — pipe through `jq` to filter.

## Newsletter posts

```bash
# Recent posts
substack newsletter posts https://example.substack.com --limit 5

# Top posts by popularity
substack newsletter posts https://example.substack.com --sort top --limit 10

# Other sort options: new (default), top, pinned, community
```

## Search within a newsletter

```bash
substack newsletter search https://example.substack.com "machine learning" --limit 5
```

Search is per-newsletter only — no global cross-publication search.

## Read a post

```bash
# Metadata (title, date, reactions, restacks, description)
substack post metadata https://example.substack.com/p/post-slug --pretty

# Full HTML body
substack post content https://example.substack.com/p/post-slug

# Check if paywalled
substack post paywalled https://example.substack.com/p/post-slug
```

To convert HTML content to markdown: pipe through pandoc.

```bash
substack post content https://example.substack.com/p/post-slug | python3 -c "import json,sys; print(json.load(sys.stdin))" | pandoc -f html -t markdown
```

## Browse categories

```bash
# List all categories
substack categories

# Newsletters in a category
substack category newsletters --name Technology
substack category newsletters --name Technology --metadata  # full metadata

# Also by ID
substack category newsletters --id 5
```

## Podcast episodes

```bash
substack newsletter podcasts https://example.substack.com --limit 5
```

## Newsletter recommendations

```bash
substack newsletter recs https://example.substack.com
```

## Newsletter authors

```bash
substack newsletter authors https://example.substack.com
```

## User profiles

```bash
substack user info username
substack user subscriptions username

# Resolve renamed handles
substack resolve-handle oldusername
```

## Paywalled content

Requires session cookies exported from your browser:

```bash
substack --cookies ~/cookies.json post content https://example.substack.com/p/paid-post
substack --cookies ~/cookies.json newsletter posts https://example.substack.com --limit 5
```

## jq patterns

```bash
# Extract just titles and URLs from posts
substack newsletter posts https://example.substack.com --limit 10 \
  | jq '.[] | {title, slug, date: .post_date[:10], hearts: .reactions["❤"]}'

# Get newsletter URLs from a category
substack category newsletters --name Technology \
  | jq -r '.[].base_url'

# Search and get post URLs
substack newsletter search https://example.substack.com "AI" --limit 5 \
  | jq -r '.[] | .canonical_url'
```

## Limits

- 2-second built-in delay between API calls (polite rate limiting)
- Category listing maxes at ~21 pages
- Search is per-newsletter, not cross-publication
- `--pretty` flag for human-readable JSON output
