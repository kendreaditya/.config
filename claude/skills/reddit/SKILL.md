---
name: reddit
description: "Search Reddit, browse subreddits, read posts and comments, and look up user activity using the public JSON API. Use when the user wants to: search Reddit, find Reddit posts, browse a subreddit, read Reddit comments, check what's trending on Reddit, look up a Reddit user, research a topic on Reddit, get Reddit discussions, or any variation of 'reddit search', 'find posts about', 'what does r/X think about', 'reddit user', 'subreddit'."
---

# Reddit

Search and browse Reddit via the public JSON API. No API key needed — just curl + jq.

## Prerequisites

```bash
which curl jq
```

## Common Header

All requests need a User-Agent header. Use this throughout:

```
-H "User-Agent: claude-reddit-skill/1.0"
```

Rate limiting: Reddit throttles aggressively. Add `sleep 2` between sequential requests. If you get HTTP 429 or empty responses, back off 5-10 seconds.

## Search All of Reddit

```bash
curl -s 'https://www.reddit.com/search.json?q=QUERY&limit=10&sort=relevance' \
  -H "User-Agent: claude-reddit-skill/1.0" \
  | jq -r '.data.children[] | .data | "\(.title)\n  r/\(.subreddit) | \(.score) pts | \(.num_comments) comments | u/\(.author)\n  https://reddit.com\(.permalink)\n"'
```

### Parameters

| Param | Values | Default |
|-------|--------|---------|
| `q` | search query (URL-encoded) | required |
| `sort` | `relevance`, `hot`, `new`, `top`, `comments` | `relevance` |
| `t` | `hour`, `day`, `week`, `month`, `year`, `all` | `all` |
| `limit` | 1-100 | 25 |
| `after` | pagination token from response | — |

### Search within a subreddit

```bash
curl -s 'https://www.reddit.com/r/SUBREDDIT/search.json?q=QUERY&restrict_sr=on&sort=new&limit=10' \
  -H "User-Agent: claude-reddit-skill/1.0" \
  | jq -r '.data.children[] | .data | "\(.title) [\(.score) pts, \(.num_comments) comments]\n  https://reddit.com\(.permalink)\n"'
```

`restrict_sr=on` limits results to that subreddit.

## Browse a Subreddit

```bash
curl -s 'https://www.reddit.com/r/SUBREDDIT/hot.json?limit=10' \
  -H "User-Agent: claude-reddit-skill/1.0" \
  | jq -r '.data.children[] | .data | "\(.title)\n  \(.score) pts | \(.num_comments) comments | u/\(.author) | id: \(.id)\n"'
```

Replace `hot` with `new`, `top`, `rising`, or `controversial`. For `top`, add `&t=day` (or `week`, `month`, `year`, `all`).

### JSON output for further processing

```bash
curl -s 'https://www.reddit.com/r/SUBREDDIT/top.json?t=week&limit=10' \
  -H "User-Agent: claude-reddit-skill/1.0" \
  | jq '[.data.children[] | .data | {title, score, num_comments, author, id, url, created: (.created_utc | todate), selftext: .selftext[0:200]}]'
```

## Read a Post + Comments

The response is a JSON array: `[0]` is the post, `[1]` is the comment tree.

```bash
curl -s 'https://www.reddit.com/r/SUBREDDIT/comments/POST_ID.json?limit=20&sort=top' \
  -H "User-Agent: claude-reddit-skill/1.0" -o /tmp/reddit_thread.json

# Post details
jq '.[0].data.children[0].data | {title, score, author, selftext, url, num_comments, created: (.created_utc | todate)}' /tmp/reddit_thread.json

# Top comments
jq -r '.[1].data.children[] | select(.kind == "t1") | .data | "u/\(.author) (\(.score) pts):\n  \(.body[0:300])\n"' /tmp/reddit_thread.json
```

### Comment sort options

Set `sort` param: `top`, `best`, `new`, `controversial`, `old`, `qa`.

### If you only have a full Reddit URL

Append `.json` to any Reddit URL:

```bash
curl -s 'https://www.reddit.com/r/python/comments/abc123/some_title/.json?limit=20' \
  -H "User-Agent: claude-reddit-skill/1.0"
```

## User Activity

```bash
curl -s 'https://www.reddit.com/user/USERNAME.json?limit=10' \
  -H "User-Agent: claude-reddit-skill/1.0" \
  | jq -r '.data.children[] | .data | "\(if .title then .title else "Comment in r/\(.subreddit)" end)\n  \(.score) pts | r/\(.subreddit) | https://reddit.com\(.permalink)\n"'
```

### Filter to posts only or comments only

```bash
# Posts only
curl -s 'https://www.reddit.com/user/USERNAME/submitted.json?limit=10' \
  -H "User-Agent: claude-reddit-skill/1.0" | jq '...'

# Comments only
curl -s 'https://www.reddit.com/user/USERNAME/comments.json?limit=10' \
  -H "User-Agent: claude-reddit-skill/1.0" | jq '...'
```

## Pagination

Every listing response includes `data.after` — pass it as `&after=TOKEN` to get the next page:

```bash
curl -s 'https://www.reddit.com/r/SUBREDDIT/new.json?limit=25&after=t3_abc123' \
  -H "User-Agent: claude-reddit-skill/1.0"
```

Extract the token: `jq -r '.data.after' response.json`

## Tips

- Always single-quote URLs in curl to avoid shell interpretation of `&`
- Use `-o /tmp/file.json` for large responses, then parse with jq separately
- `.selftext` contains the post body (empty for link posts)
- `.url` is the linked URL (for link posts) or the permalink (for self posts)
- Timestamps: `.created_utc | todate` converts to ISO 8601
- For subreddit info/rules: `https://www.reddit.com/r/SUBREDDIT/about.json`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Empty response / 0 bytes | Rate limited — wait 5s and retry |
| HTTP 429 | Back off 10-15s |
| HTML instead of JSON | Add `-L` flag to follow redirects, or use `old.reddit.com` |
| 403 Forbidden | Change User-Agent to a browser-like string |
