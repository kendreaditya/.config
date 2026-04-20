---
name: parlai
description: Search, list, and fetch the user's personal AI chat history across ChatGPT, Claude.ai, Gemini, AI Studio, Perplexity, Codex (CLI + Desktop), and Claude Code via the local `parlai` CLI. Stateless — every command hits the provider's web API live or reads local JSONL files directly. Supports date filtering (--since / --until). Use when the user wants to find a past AI conversation ("that thing I asked ChatGPT about X", "find the Claude chat where I worked on Y"), pull the full body of a known conversation, fan out a query across all their AI tools at once, or filter by date ("conversations from last week", "what did I ask Gemini in March"). Triggers on phrases like "find my chat about", "search my AI history", "pull up the conversation about", "what did I ask ChatGPT/Claude/Gemini about", "show me convos from a date or time period", "parlai".
---

# parlai

Local CLI wrapping the user's personal AI chat history across 8 providers. Lives at `~/workspace/parlai`, installed on PATH as `parlai`.

## Providers

`chatgpt` · `claude` · `claude-code` · `codex-cli` · `codex-desktop` · `gemini` · `aistudio` · `perplexity`

## Commands

```bash
parlai status                              # which providers are authed
parlai list <provider> [-n N]              # recent conversations (live API or local files)
parlai get <provider> <id> [-f md|json]    # full conversation as Markdown
parlai search "<query>"                    # fan out across every authed provider
parlai search -p <provider> "<query>"      # one provider
parlai search "<query>" --content          # also fetch full conversation bodies (deduped)
parlai search "<query>" --json             # JSONL output for piping to LLMs/scripts
parlai open <provider> <id>                # open in browser
parlai login <provider>                    # interactive cookie paste (Chrome auto-detect fallback)
parlai --verbose <cmd>                     # print warnings to stderr
```

**Stateless.** No `sync`, no local cache, no DB. Every `list` and `search` hits the provider's web API live, or for local providers (claude-code, codex-*) reads their JSONL files directly. Trade-off: repeated queries re-hit the API each time — but no staleness, no cache invalidation, nothing to forget to sync.

### Date filtering with `--since` / `--until`

Every list/search/sync command accepts `--since` and `--until`. Format options:

- ISO: `2026-04-19`, `2026-04` (year-month), `2026-04-19T16:30:00`
- Relative: `7d`, `2w`, `3mo`, `1y`, `24h`, `90m`
- Special: `today`, `yesterday`

```bash
parlai list claude --since 7d              # last week
parlai list claude --since 14d             # walks the API's pagination back 2 weeks
parlai search "india" --since 2026-04-01 --until 2026-04-30
parlai search "taxes" --since 2025-04-17 --until 2025-04-21   # a year ago ± 2 days
```

For remote queries, `--since` walks the provider's pagination back (newest-first) and stops once it crosses the boundary — effectively server-side filtering even though no provider's API exposes a date parameter. `--until` is best paired with `--since` (otherwise we still walk all of history).

## Workflows

### Find a past conversation by topic

```bash
parlai search "<topic>" --json | head -20
```

Returns one JSONL object per match: `{provider, id, title, url, snippet, updated_at}`. For local-only providers (claude-code, codex-*, gemini), the search auto-falls-back to the local FTS5 index.

### Get the full conversation body

```bash
parlai get <provider> <id>                 # Markdown
parlai get <provider> <id> -f json         # structured JSON
```

### Search and read in one shot

```bash
parlai search "<topic>" --content --json   # each line includes the messages array
parlai search "<topic>" -p claude -c       # human-readable, full convo bodies
```

`--content` deduplicates hits by conversation and fetches each one's full body. Not cached — fresh every call.

## Output format

Default: fzf-style — `[provider] id  title` then indented snippet (FTS5 highlights wrapped in bold yellow). For machine consumption (piping to other tools, feeding to an LLM), always pass `--json` for one JSON object per line.

## Auth

Most web providers (ChatGPT, Claude, Gemini, Perplexity) read cookies live from Chrome via `browser_cookie3` — no setup needed if the user is logged in. AI Studio uses Drive OAuth via the `gog` CLI. Local providers (claude-code, codex-*) need no auth.

If `parlai status` shows ✗ for a provider, run `parlai login <provider>` for an interactive cookie-paste fallback.

## Notes

- No persistence. No DB, no cache file. Only `~/.parlai/credentials.json` (manual cookie fallback) is ever written.
- Source repo: `~/workspace/parlai`. To rebuild after changes: `cd ~/workspace/parlai && uv sync`.
- Local providers (`claude-code`, `codex-cli`, `codex-desktop`) search by scanning their JSONL files directly (case-insensitive substring).
