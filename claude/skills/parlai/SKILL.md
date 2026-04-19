---
name: parlai
description: Search, list, fetch, and sync the user's personal AI chat history across ChatGPT, Claude.ai, Gemini, AI Studio, Perplexity, Codex (CLI + Desktop), and Claude Code via the local `parlai` CLI. Use when the user wants to find a past AI conversation ("that thing I asked ChatGPT about X", "find the Claude chat where I worked on Y"), pull the full body of a known conversation, fan out a query across all their AI tools at once, or back up their history locally. Triggers on phrases like "find my chat about", "search my AI history", "pull up the conversation about", "what did I ask ChatGPT/Claude/Gemini about", "back up my chats", "parlai".
---

# parlai

Local CLI wrapping the user's personal AI chat history across 8 providers. Lives at `~/workspace/parlai`, installed on PATH as `parlai`.

## Providers

`chatgpt` · `claude` · `claude-code` · `codex-cli` · `codex-desktop` · `gemini` · `aistudio` · `perplexity`

## Commands

```bash
parlai status                              # which providers are authed + counts
parlai list <provider> [-n N]              # recent conversations (uses local DB by default)
parlai list <provider> --remote            # hit the live API
parlai search "<query>"                    # remote-by-default fan-out across all providers
parlai search -p <provider> "<query>"      # one provider's native search
parlai search "<query>" --local            # cached FTS5 (faster, may be stale)
parlai search "<query>" --content          # also fetch full conversation bodies (caches them too)
parlai search "<query>" --json             # JSONL output for piping
parlai get <provider> <id> [-f md|json]    # full conversation as Markdown
parlai sync [provider] [--full]            # pull conversations into local SQLite (--full = no cap)
parlai stats                               # storage stats
parlai open <provider> <id>                # open in browser
parlai login <provider>                    # interactive cookie capture (when Chrome auto-detect fails)
parlai --verbose <cmd>                     # print warnings to stderr
```

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

`--content` deduplicates by conversation, fetches each, and caches results to the local DB so subsequent `--local` searches hit them.

### Bulk archive everything

```bash
parlai sync claude --full                  # pull every claude.ai conversation
parlai sync --full                         # pull from every authed provider
```

After a `--full` sync, `parlai search "<x>" --local` becomes the fastest path and works offline.

## Output format

Default: fzf-style — `[provider] id  title` then indented snippet (FTS5 highlights wrapped in bold yellow). For machine consumption (piping to other tools, feeding to an LLM), always pass `--json` for one JSON object per line.

## Auth

Most web providers (ChatGPT, Claude, Gemini, Perplexity) read cookies live from Chrome via `browser_cookie3` — no setup needed if the user is logged in. AI Studio uses Drive OAuth via the `gog` CLI. Local providers (claude-code, codex-*) need no auth.

If `parlai status` shows ✗ for a provider, run `parlai login <provider>` for an interactive cookie-paste fallback.

## Notes

- Default search is **remote** (live API) — no need to sync first. `--local` opts into the cached index.
- `--full` truly means full: ignores both watermark and `--limit` cap.
- `~/.parlai/db.sqlite` is the local store; `~/.parlai/raw/<provider>/<id>.json` mirrors raw payloads.
- Source repo: `~/workspace/parlai`. To rebuild after changes: `cd ~/workspace/parlai && uv sync`.
