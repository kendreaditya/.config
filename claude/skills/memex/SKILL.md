---
name: memex
description: "Unified personal-life search across the user's own data: Logseq, Google Drive, Gmail, iMessage, and WhatsApp. Fans out a single query across all sources in parallel and presents results grouped by source with dates. Use when the user wants to search their own life/history across multiple platforms at once. Triggers: 'memex', 'search my life', 'search everywhere for X', 'find everything I wrote/said about X', 'what do I have on X', 'pull up anything mentioning X', 'search across my notes/drive/email/messages', 'cross-source search', 'find it in my stuff'. Named after Vannevar Bush's 1945 personal-memory concept."
---

# Memex

Single-query unified search across the user's personal data — Logseq, Drive, Gmail, iMessage, WhatsApp. This skill is a playbook: it tells you which CLI to invoke for each source, how to fan them out in parallel, and how to present the aggregated results. No dedicated CLI — the backing tools already exist.

## When to use

Use memex for questions about the user's own life/history/records:
- "what did I write about vraja?"
- "find everything mentioning the madhuri doc"
- "when did we first talk about the breakup"
- "pull up anything about my birthday"
- "search my life for 'kirtan'"

NOT for: the public internet (use `forage` for that), the user's code repos (use `Grep`/`github`), or the user's money (use `monarch-money`).

## How it works

For each query, search all available sources **in parallel** — issue one Bash call per source in a single message. Then synthesize into one grouped result.

### Source selection

Default: every available source. Narrow only if the user asks ("just my email", "only logseq").

| Source      | Backend                              | When it's the strongest signal                                          |
| ----------- | ------------------------------------ | ----------------------------------------------------------------------- |
| `logseq`    | `logseq search`                      | Thoughts, reflections, journals — the user's own written processing     |
| `drive`     | `gog drive search`                   | Long-form docs, planning notes, spreadsheets, media                     |
| `gmail`     | `gog gmail search`                   | Formal correspondence, receipts, calendar invites, shared Google Docs   |
| `imessage`  | direct `sqlite3` on chat.db          | Real-time conversations with family / close friends (iMessage + SMS)    |
| `whatsapp`  | `wacli messages search`              | Group chats, overseas contacts, anything not in iMessage                |

Availability check before running: `which logseq gog wacli; test -r ~/Library/Messages/chat.db && echo imsg-ok`.

### Search commands

Replace `QUERY` with the user's search term. Always request JSON so synthesis is structured.

#### logseq
```bash
logseq search "QUERY" --format json --limit 10
```
Returns `blocks`, `pages-content`, `pages`. Strip the PFTS `$pfts_2lqh>...<pfts_2lqh$` markers from snippets. No dates in raw results — follow up with `logseq backlinks "<page>" --with-dates` or `logseq block <uuid>` for journal day.

#### Google Drive
```bash
gog drive search "QUERY" --json --results-only
```
Fields: `name`, `modifiedTime`, `mimeType`, `webViewLink`, `id`. Use `modifiedTime[:10]` as the date.

#### Gmail
```bash
gog gmail search "QUERY" --json --results-only
# with date filter — use Gmail's native syntax (faster than client-side filtering):
gog gmail search "QUERY after:2025/08/01 before:2025/12/31" --json --results-only
```

#### iMessage
No built-in search in `imsg`. Query `chat.db` directly (read-only). Needs Full Disk Access for the invoking terminal.

```bash
sqlite3 -readonly ~/Library/Messages/chat.db <<'SQL'
SELECT
  datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS when_local,
  CASE WHEN m.is_from_me = 1 THEN 'me' ELSE COALESCE(h.id, '?') END AS who,
  REPLACE(m.text, CHAR(10), ' ') AS text
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
WHERE m.text LIKE '%QUERY%' COLLATE NOCASE
ORDER BY m.date DESC
LIMIT 10;
SQL
```
Notes: (1) Apple stores `m.date` as nanoseconds since 2001-01-01 — the `/1e9 + 978307200` converts to Unix epoch. (2) `m.text` is NULL for rich-content-only messages (stored in `attributedBody` BLOB) — those won't match. (3) Add `AND m.date > (strftime('%s','YYYY-MM-DD') - 978307200) * 1000000000` for date filtering.

#### WhatsApp
```bash
wacli messages search "QUERY" --limit 10
wacli messages search "QUERY" --after 2025-08-01 --before 2025-12-31 --limit 10
```
First-time setup: `wacli auth` (QR login + initial sync). If the user hasn't run this, the source will return empty — tell them to run it.

### Orchestration — parallel fan-out

Send a single assistant message with **multiple Bash tool calls in parallel** (one per available source). Example for query "madhuri":

```
[Bash: logseq search "madhuri" --format json --limit 10]
[Bash: gog drive search "madhuri" --json --results-only]
[Bash: gog gmail search "madhuri" --json --results-only]
[Bash: sqlite3 -readonly ~/Library/Messages/chat.db "SELECT ... WHERE text LIKE '%madhuri%' ..."]
[Bash: wacli messages search "madhuri" --limit 10]
```

Skip any source whose CLI isn't installed. Report which were skipped in the summary.

### Presentation

Group results by source. Within each source, sort by date descending. Format:

```
memex: madhuri  (18 hits across 4 sources)

── logseq (9)
  (no date)  [Page] Madhuri Sakhi
  (no date)  block content snippet…
  …

── drive (3)
  2026-04-18  Madhuri + Kendre [Google Doc]  https://docs.google.com/...
  …

── gmail (3)
  2026-03-24  [sender] subject / snippet  https://mail.google.com/...
  …

── imessage (3)
  2026-03-21  [me] i think madhuri said she is only coming on the way back
  …

skipped: whatsapp (wacli not authed)
```

Truncate long snippets to ~240 chars. Show `ref` links where available (Drive URL, Gmail thread URL, logseq block UUID).

## Follow-ups after a hit

When the user drills into a specific result, use the native follow-up for that source:

| Source     | Drill-down                                                                |
| ---------- | ------------------------------------------------------------------------- |
| logseq     | `logseq block <uuid> --children` or `logseq page "<name>" --tree --resolve-embeds` |
| drive      | `gog drive download <id> --format txt --out /tmp/<name>.txt` then `Read`  |
| gmail      | `gog gmail thread <threadId>` for the full thread                         |
| imessage   | `imsg chats` → find chat rowid → `imsg history --chat-id <id> --limit 50` around the timestamp |
| whatsapp   | `wacli messages --chat <jid>` around the timestamp                        |

## Gotchas

1. **iMessage needs Full Disk Access** for the invoking terminal / Claude Code app — otherwise `chat.db` reads fail silently. System Settings → Privacy & Security → Full Disk Access.
2. **iMessage `LIKE '%…%'` is a full table scan** — not indexed. Expect 1–3 seconds on large histories. Narrow with a date range if possible.
3. **Logseq `search` returns no dates.** Follow up with `logseq backlinks <page> --with-dates` or `logseq timeline <page>` when dates matter.
4. **`imsg` UUIDs vs page UUIDs vs block UUIDs.** When following up, logseq `blocks[].uuid` → `logseq block`; `pages[]` names → `logseq page`; `pages-content[].uuid` is a **page** UUID, not a block.
5. **Gmail query syntax leaks through.** `from:alice OR label:starred` works for gmail but other sources will treat the whole string as a literal — expect zero hits elsewhere. Strip Gmail operators before passing to other sources if the user's query uses them.
6. **Results are NOT deduplicated across sources** — a Drive doc shared via Gmail legitimately shows up in both. Different surfaces, same content.
7. **WhatsApp needs `wacli auth` one-time setup.** `which wacli` only confirms the binary, not auth state. If wacli returns no results for a query that plausibly should hit, suggest the user run `wacli doctor`.
8. **Logseq must be running** with HTTP APIs server enabled. `logseq doctor` diagnoses. If not running, the logseq source silently returns nothing.

## Extending to new sources

Easy additions later — each is a one-liner drop-in:

- **Apple Notes** → `memo search "QUERY" --json`
- **Apple Reminders** → `remindctl list --search "QUERY" --json`
- **Calendar** → `gog calendar search "QUERY" --json --results-only`
- **Todoist** → `todoist list --filter "search: QUERY"`
- **Monarch transactions** → `mm transactions --search "QUERY" --json`
- **Past Claude sessions** → via the `session-logs` skill
- **Slack / Discord** → via the respective skills
- **Twitter bookmarks / Reddit saved** → via `xurl` / `reddit`

When the user mentions a new source you should remember for next time, suggest adding a one-line entry to this skill's "Search commands" section.
