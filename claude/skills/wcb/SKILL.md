---
name: wcb
description: "Web Context Builder — async web scraper that converts websites (docs sites, blogs, API references) into LLM-optimized Markdown. Crawls a domain, extracts content with BeautifulSoup, converts to clean Markdown, and merges pages into a single consumable file. Supports subdomain control, depth limits, include/exclude regex filters, concurrency tuning, and optional headless browser for JS-heavy sites. Use when the user asks to: 'build docs for this site', 'scrape this documentation', 'convert a website to markdown', 'make an LLM reference from a URL', 'download and flatten docs'. Also use when Claude needs to feed an external docs site into its own context. Triggers: 'wcb', 'scrape site', 'build docs from URL', 'crawl website to markdown', 'web to LLM', 'download docs site'."
---

# wcb (Web Context Builder)

Async crawler that scrapes a website and emits LLM-optimized Markdown. Outputs one file per page plus a merged `<domain>.md` for easy ingestion.

## Usage

```bash
wcb https://docs.example.com                       # crawl, merged output in CWD
wcb https://docs.example.com -o ./my-docs          # custom output dir
wcb https://docs.example.com -d 3                  # max depth 3
wcb https://js-heavy-site.com --browser            # headless browser for SPAs
wcb https://docs.example.com -i '/api/' -e '/old/' # include/exclude patterns
wcb https://docs.example.com --cross-subdomain     # allow subdomain crawl
```

## Flags that matter

- `-o PATH` — output dir
- `-d N` — max crawl depth (default: unlimited)
- `-c N` — concurrent requests (default 5; raise for fast hosts, lower to be polite)
- `--delay SEC` — per-request delay (default 0.1)
- `--cross-subdomain` — follow into subdomains (default: stay on exact subdomain)
- `--browser` — use Playwright for JS-rendered pages (slower but needed for SPAs)
- `-i REGEX` / `-e REGEX` — URL include/exclude filters (repeatable)
- `--no-merge` — skip the merged `<domain>.md` file
- `-m NAME` — custom merged filename

## When to use

- Harvesting a docs site (Anthropic, Stripe, etc.) for LLM context.
- Pulling an API reference to feed to Claude without hitting the live site repeatedly.
- Archiving a blog/wiki as a single searchable Markdown file.

## When NOT to use

- Logged-in or paywalled sites (no auth support built in).
- Sites with aggressive anti-bot (Cloudflare challenge pages). `--browser` helps some but not all.
- One-off single-page grabs — faster to use `curl | html2markdown` or the browser "Save as".

## Tips

- For big sites, pair with `shortn` afterwards: `wcb ... -o out && shortn out/site.md -t 50000`.
- `--browser` requires `playwright install chromium` first.
- Regex filters use Python syntax against the URL path+query.
- Output is idempotent-ish: re-running skips already-downloaded pages.
