---
name: logseq
description: Logseq HTTP-API CLI (`logseq` on PATH) for querying and mutating a running Logseq graph from the shell. Use when the user asks about their Logseq graph, pages, blocks, journals, tags, backlinks, or wants to run Datalog over their notes. Mutations supported (create/update/delete pages and blocks, set properties) behind confirmations. Requires Logseq running with the HTTP APIs server enabled. Triggers on phrases "my logseq graph", "logseq search", "logseq pages", "logseq journals", "logseq tags", "logseq backlinks", "logseq today", "logseq block", "logseq stats", "logseq datalog", "logseq q", "logseq raw", "search my notes", "find in logseq", "blocks tagged with", "pages linking to".
---

# Logseq CLI

`logseq` is a single-binary shell wrapper over Logseq's HTTP API server (0.10.15+). Stdlib Python, no deps. All state lives in this skill folder.

## Anti-triggers

Do NOT use this skill for:
- Logseq plugin authoring — that's the `logseq-plugin` skill (separate concern).
- Logseq as a user — theme questions, keyboard shortcuts, workflow advice.
- Obsidian, Roam, Notion, or any non-Logseq knowledge graph.

## Quick start

```bash
logseq doctor                          # verify server + auth + graph
logseq today                           # today's journal (page metadata)
logseq today --tree                    # today's journal with block tree
logseq search "keyword"                # full-text search
logseq page "Reading List" --tree
logseq stats                           # block/page/tag/journal counts
logseq backlinks "Page X" --with-dates # linked refs w/ journal day on each block
logseq timeline "Page X" --text        # all text mentions, grouped by date
```

First-time setup if `doctor` complains:

```bash
logseq init                 # interactive: prompts for token, host, port
```

## Prerequisites

The user's Logseq must be running with the HTTP APIs server enabled:

1. Logseq → Settings → Features → **HTTP APIs server** (toggle on).
2. New toolbar icon appears top-right. Click it → **+ Add new token** (name + value, anything).
3. Click **▶ Start server**. Defaults: host `127.0.0.1`, port `12315`.

If the server is disabled or not running, `logseq doctor` emits:
> `Logseq HTTP API server is not running on 127.0.0.1:12315. Start it from the toolbar icon in Logseq.`

## Command index

Run `logseq <command> --help` for full option details on any command.

**Setup / meta**
- `init` — interactive: token, host, port → state/config.json
- `doctor` — diagnose server + auth + graph; `--fix` symlinks CLI into PATH; `--wait-for-server` auto-spawns `open -a Logseq` if the port is closed and polls up to 30s until the API answers (requires Auto-start in Logseq's server config for the HTTP server to come up)
- `version` — CLI + server versions
- `graph` / `graphs` — current graph / all configured graphs
- `use <name>` — soft-pin default graph (Logseq itself must be switched manually)
- `config-get [key]` — print config (token redacted)
- `config-set <key> <value>` — write config key

**Reads**
- `today [--tree]`, `yesterday [--tree]`, `tomorrow [--tree]`
- `journals --last N [--tree]` / `--since DATE [--until DATE]` / `--on DATE`
- `page <name> [--tree] [--resolve-embeds]` — `--resolve-embeds` inlines `((uuid))` placeholders with target content (recursive, cycle-safe)
- `pages [--filter REGEX] [--namespace NS] [--namespace-tree NS]`
- `block <uuid> [--children] [--resolve-embeds]`
- `props <uuid>` / `prop <uuid> <key>`
- `backlinks <page> [--with-dates] [--fields k1,k2,...]` — linked references; `--with-dates` injects `journal_day` (ISO) + `page_name`; `--fields` projects each block to only the listed keys (matches both `k` and `block/k`)
- `tag <name> [--with-dates]` — blocks referencing a tag/page
- `timeline <page> [--text] [--order asc|desc] [--fields k1,k2,...]` — refs grouped by journal date; `--order` controls date sort (default `desc`); `--text` = case-insensitive content match; `--fields` only applies to JSON output
- `search <query> [--limit N] [--with-dates] [--fields k1,k2,...]` — full-text (PFTS markers stripped); `--with-dates` enriches `blocks` only (not `pages-content`); `--fields` projects result lists
- `recent` / `favorites` / `templates`

**Stats, tags, properties**
- `stats` — graph summary (blocks, pages, tags, journals)
- `stats --broken-refs` — pages referenced but never opened (raw form)
- `stats --orphans` — name-only pseudopages with no content
- `stats --largest-pages [N]` — top pages by block count
- `tags [--sort freq|name] [--limit N]`
- `tag-freq <name>`
- `prop-keys` / `prop-values <key>` / `prop-search <key> [<value>]`

**Writes** (gated on `--yes` or interactive confirm; `--dry-run` prints without sending)
- `write page-create <name> [--content ...] [--properties JSON]`
- `write page-delete <name>` / `page-rename <old> <new>`
- `write block-insert <parent> <content> [--before UUID|--after UUID]`
- `write block-append <page> <content>` / `block-prepend <page> <content>`
- `write block-update <uuid> <content>` / `block-remove <uuid>`
- `write block-move <uuid> <new-parent>` / `block-batch <parent> <json-array>`
- `write prop-set <uuid> <key> <value>` / `prop-remove <uuid> <key>`
- `write template-apply|create|remove ...`

**Raw / escape hatches**
- `datalog '<query>'` — full Datalog via `datascript_query`
- `q '<expr>'` — Logseq simplified syntax: `(page "X")`, `(tag "X")`, `(task TODO)`
- `custom-query '<edn>'`
- `raw <method> [--args JSON]` — generic POST /api
- `raw --list [--grep PATTERN]` — enumerate all 123 known methods

## Global flags (work on any subcommand)

```
--token X         # overrides env + config
--host X          # default 127.0.0.1
--port N          # default 12315
--graph X         # soft-pin a graph name
--format FMT      # json|pretty|tree|md|table|plain|uuids
--pretty          # shortcut for --format pretty
--uuids-only      # shortcut for --format uuids (one per line)
--limit N / --offset N
--quiet / --verbose
--yes, -y         # auto-confirm writes
--dry-run         # print request without sending (writes only)
```

Default format: `pretty` when stdout is a TTY, `json` when piped. Override with `--format`.

## Config + auth

Resolution precedence: CLI flag → env → config file → default.

- `LOGSEQ_API_TOKEN` — token
- `LOGSEQ_HOST` — default 127.0.0.1
- `LOGSEQ_PORT` — default 12315
- `LOGSEQ_GRAPH` — soft-pin

Config file: `~/.config/claude/skills/logseq/state/config.json` (chmod 600). Written by `init` and `config-set`.

## Common pipelines

```bash
# Dump today's journal as markdown
logseq today --tree --format md

# Page tree as plain indented bullets (content only, no JSON)
logseq page "Reading List" --tree --format plain

# All blocks matching a search term, resolved one at a time
logseq search "keyword" --uuids-only | xargs -n1 logseq block --children

# Chronological story for a topic (catches un-indexed refs via text match)
logseq timeline "Person X" --text

# Backlinks enriched + field-projected to keep JSON small
logseq backlinks "Person X" --with-dates --fields content,journal_day --format json

# Page tree with embed blocks resolved inline (no more stray ((uuid)) placeholders)
logseq page "Person X" --tree --resolve-embeds --format plain

# Timeline in chronological (oldest-first) order
logseq timeline "Person X" --text --order asc

# Graph stats for cron
logseq stats --format json | jq '{blocks, pages, journals}'

# Pages I linked to but never opened
logseq stats --broken-refs --format table
```

More in `references/recipes.md`.

## Gotchas

1. **`getCurrentPage` returns null** on fresh journal mounts. The CLI doesn't hit this directly (uses today's date + `getPage` instead), but if you add a handler that needs the current page, read from the DOM title, not this endpoint.
2. **Response keys are bimodal**: top-level keys are camelCase (`journalDay`, `createdAt`), pull-query results are kebab-case (`block/uuid`, `block/created-at`, `path-refs`). The module handles this internally via defensive readers. See `references/shapes.md`.
3. **`search` snippets have PFTS markers** (`$pfts_2lqh>...<pfts_2lqh$`). The CLI strips them via `strip_pfts` before output.
3a. **`search` returns two kinds of UUIDs.** `blocks[].uuid` are block UUIDs — pass to `logseq block`. `pages-content[].uuid` are **page** UUIDs — passing them to `logseq block` fails (the CLI now reports "That UUID is the page 'X', not a block" and suggests `logseq page`). Use `pages` list for page titles.
4. **Deleting a page removes all refs to it** — Logseq's `deletePage` purges the `:block/name` entry, so `[[Deleted Page]]` references in other blocks become untracked text. The "broken refs" query can't find them anymore. Consequence: "broken ref" truly means "page referenced + pseudopage only", not "deleted page referenced".
5. **Nested blocks created via `insertBlock` don't always populate `:block/refs`.** Top-level blocks created via `appendBlockInPage` do. Use top-level blocks for seeds/tests that need reliable backlinks.
6. **Token auth is permissive if no tokens are configured.** If the user's Logseq server was started with no `:server/tokens` list, it accepts any bearer token. The CLI doesn't detect this.
7. **`list_files_of_current_graph` is declared but unwired** in 0.10.15 — `raw` call returns `MethodNotExist`. Documented in `references/api.md`.
8. **Multi-graph switching can't be done from the HTTP API.** `logseq use X` only writes a soft-pin to config. The user must switch graphs inside Logseq.

## Testing against a scratch graph

```bash
# Seed a fresh logseq-test graph (safety-checks current graph == 'logseq-test')
python3 ~/.config/claude/skills/logseq/scripts/tests/seed.py --reset

# Run the full test harness (73 assertions)
bash ~/.config/claude/skills/logseq/scripts/tests/run_tests.sh
```

## File map

- `SKILL.md` — this file.
- `scripts/logseq.py` — entry point; symlinked from `~/.config/scripts/logseq`.
- `scripts/_logseq_common.py` — HTTP client, config, formatters, datalog constants, error classifier.
- `scripts/commands/` — per-group handlers (reads, stats, writes, raw, meta).
- `scripts/tests/seed.py` — populates `logseq-test` with 15 pages / ~30 blocks.
- `scripts/tests/run_tests.sh` — 73 assertions against the seeded graph.
- `references/api.md` — full enumerated HTTP API surface.
- `references/datalog.md` — Datalog query cookbook.
- `references/shapes.md` — JSON response shapes.
- `references/recipes.md` — copy-pasteable pipelines.
- `state/config.json` — token + host + port + preferred date format.
