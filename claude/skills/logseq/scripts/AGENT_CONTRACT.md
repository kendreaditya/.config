# Agent Contract — `logseq` CLI

Every command-handler agent must respect this contract exactly. Violations cause Phase 3 assembly to fail.

## Import surface (from `_logseq_common`)

```python
from _logseq_common import (
    # HTTP client
    call,                 # call(method: str, args: list|None = None) -> Any
    LogseqError,          # exc with .kind in {"refused","auth","method","args","other"}
    classify_error,       # classify_error(exc) -> LogseqError

    # Config
    Session,              # dataclass: token, host, port, graph, preferred_date_format
    load_session,         # load_session(cli_args) -> Session
    save_config,          # save_config(dict) -> None
    CONFIG_FILE,          # abs path to ~/.config/claude/skills/logseq/state/config.json

    # Output
    out,                  # out(data, fmt=None, session=None) -> None (prints to stdout)
    err,                  # err(msg: str) -> None (prints to stderr)
    is_tty,               # is_tty() -> bool

    # Formatters (advanced — out() dispatches; call directly only if needed)
    as_json, as_pretty, as_tree, as_md, as_table, as_plain, as_uuids,

    # Datalog + helpers
    KNOWN_METHODS,        # list[str] — all 123 method names
    Q,                    # dict of named datalog query strings (see below)
    strip_pfts,           # strip_pfts(s: str) -> str
    parse_date,           # parse_date(s: str) -> (iso_str, journal_day_int)
    format_date_for_logseq,  # format_date_for_logseq(date, session) -> str (uses preferred_date_format)
    suggest_methods,      # suggest_methods(wrong: str, n=3) -> list[str]

    # Confirmation (write ops)
    confirm,              # confirm(prompt: str, yes_flag: bool) -> bool
)
```

## `call()` semantics

```python
data = call("logseq.App.getCurrentGraph")
data = call("logseq.Editor.getPage", ["Apr 17th, 2026"])
data = call("logseq.DB.datascriptQuery", ["[:find (count ?b) . :where [?b :block/uuid _]]"])
```

- Uses the global session (loaded once at `main()`).
- Returns parsed JSON (dict / list / scalar). Raw `None` is a valid API return.
- On HTTP error or `{"error": "..."}` body, raises `LogseqError`.
- The caller should let `LogseqError` propagate — `main()` catches it and calls `classify_error` + exits.

## `out()` semantics

```python
out(data)                          # default format based on TTY + type
out(data, fmt="tree")              # force a format
out(blocks, fmt="md")              # reconstruct markdown from a block tree
```

Valid `fmt`: `"json"`, `"pretty"`, `"tree"`, `"md"`, `"table"`, `"plain"`, `"uuids"`.
Default when `session.fmt` is None:
- TTY + dict/list → `pretty`
- TTY + scalar → `plain`
- non-TTY → `json`

## Every command handler signature

```python
def cmd_<name>(args: argparse.Namespace, session: Session) -> int:
    """Returns exit code. 0 = ok."""
    data = call(...)
    out(data, session=session)
    return 0
```

Do NOT catch `LogseqError` inside a handler — let it bubble to `main()`.

## Exit codes

- `0` — success
- `1` — generic failure
- `2` — unauthorized (401)
- `3` — unreachable (connection refused)
- `4` — bad arguments (400 or local validation)
- `5` — method doesn't exist

## Namespace convention for the `method` string

Per `src/electron/electron/server.cljs:62`, the namespace is stripped for everything except `ui`, `git`, `assets`. So these all hit the same method:
- `logseq.App.getPage`
- `logseq.Editor.getPage`
- `logseq.DB.getPage`

Use whichever reads best (Editor for page ops, App for app-level, DB for queries). The server converts to snake_case and routes to `window.logseq.api[name]`.

## `KNOWN_METHODS`

Imported from `_logseq_common.py`. Used for:
- `raw --list` output
- Levenshtein suggestion when a user-supplied method 404s
- Validating that `raw` was given a real method name (soft-warn, still attempt)

## Datalog query constants (`Q`)

```python
Q["COUNT_BLOCKS"]               # [:find (count ?b) . :where [?b :block/uuid _]]
Q["COUNT_PAGES"]                # [:find (count ?p) . :where [?p :block/name _]]
Q["COUNT_JOURNALS"]             # [:find (count ?p) . :where [?p :block/journal-day _]]
Q["ORPHAN_PAGES"]               # pages with no inbound refs and no blocks
Q["BROKEN_REFS"]                # pages referenced but never opened (no :block/file, no :block/journal-day, no :block/page pointing at them)
Q["TAG_FREQ"]                   # [:find ?name (count ?b) :where [?b :block/refs ?p] [?p :block/name ?name]]
Q["PROP_KEYS"]                  # distinct property keys across all blocks
Q["LARGEST_PAGES"]              # pages by block count, descending
Q["BLOCKS_BY_TAG"](name)        # parameterized: blocks referencing a page
Q["PAGES_IN_NAMESPACE"](ns)     # pages under a namespace prefix
```

Use these constants. Don't build queries inline.

## Global argparse flags (already on `args` in every handler)

```
--token <str>                 (or $LOGSEQ_API_TOKEN; or config.token)
--host <str>                  (or $LOGSEQ_HOST; or config.host; default 127.0.0.1)
--port <int>                  (or $LOGSEQ_PORT; or config.port; default 12315)
--graph <name>                (soft-pin; warns if running graph differs)
--format <fmt>                (json|pretty|tree|md|table|plain|uuids)
--pretty                      (alias for --format pretty)
--limit <n>                   (client-side cap on array results)
--offset <n>                  (client-side offset)
--quiet                       (suppress informational stderr)
--verbose                     (dump the POST body + raw response)
--uuids-only                  (alias for --format uuids; filters to uuids)
--yes, -y                     (auto-confirm for write ops)
--dry-run                     (print the call without sending; write ops only)
```

These are applied on the main parser and passed to every subparser. Your handler reads from `args` freely.

## Write-op pattern

```python
def cmd_write_page_create(args, session):
    method = "logseq.Editor.createPage"
    call_args = [args.name, args.properties or {}]
    if args.dry_run:
        err(f"[dry-run] POST /api {{method: {method!r}, args: {call_args!r}}}")
        return 0
    if not confirm(f"Create page {args.name!r}?", args.yes):
        err("aborted")
        return 1
    result = call(method, call_args)
    out(result, session=session)
    return 0
```

## Graph safety (for seeder + destructive tests)

Before any mutation, the seeder + tests check:
```python
if call("logseq.App.getCurrentGraph")["name"] != "logseq-test":
    err("ABORT: current graph is not logseq-test"); sys.exit(1)
```

Skip this check in the production `write` commands — that's user-driven and they should be in the right graph.

## Style

- Match `mm.py` structure (one `cmd_*` per subcommand, no classes, no inheritance).
- System Python 3 with stdlib only (no `requests`, no `rich`).
- Type hints encouraged but not enforced.
- Module docstring at the top listing this file's commands.
- Short functions — no command handler over ~40 lines. Push logic into `_logseq_common.py` helpers if repeated.

## Non-goals for your agent

- Do not modify `_logseq_common.py`. If you need a helper, drop a comment at the top of your file like:
  ```python
  # NEEDS IN _logseq_common: helper_name(args) -> ReturnType — for <reason>
  ```
  The coordinator will resolve in Phase 3.
- Do not write your own argparse parser. The coordinator builds the main parser in `logseq.py` and wires subparsers to your module.
- Do not symlink or chmod anything. The coordinator handles install in Phase 3.

## Module export contract

Every `commands/*.py` exports:

```python
HANDLERS = {
    "subcommand-name": cmd_subcommand_name,
    ...
}

def register(subparsers):
    """Called by logseq.py during argparse setup.
    Attach your subparsers here. Each should set handler via `.set_defaults(func=cmd_X)`.
    """
```

The coordinator calls `register(subparsers)` in a fixed order.
