#!/usr/bin/env python3
"""Shared helpers for the logseq CLI. HTTP client, config, formatters, datalog queries.

All state lives inside the skill folder — nothing in $HOME outside ~/.config/claude/.

Importable symbols are listed at the bottom in __all__.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------- Paths ----------------

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
STATE_DIR = SKILL_DIR / "state"
CONFIG_FILE = STATE_DIR / "config.json"

# ---------------- KNOWN_METHODS ----------------
# Embedded from scripts/_known_methods.txt (123 methods, one per line).
# Used for levenshtein suggestions when a method 404s, and for `raw --list`.

KNOWN_METHODS = [
    "__install_plugin",
    "append_block_in_page",
    "built_in_open",
    "check_editing",
    "check_slot_valid",
    "clear_plugin_storage_files",
    "clear_right_sidebar_blocks",
    "close_msg",
    "create_page",
    "create_template",
    "custom_query",
    "datascript_query",
    "delete_page",
    "download_graph_db",
    "download_graph_pages",
    "edit_block",
    "exec_command",
    "exec_git_command",
    "exist_plugin_storage_file",
    "exist_template",
    "exit_editing_mode",
    "exper_load_scripts",
    "exper_register_extensions_enhancer",
    "exper_register_fenced_code_renderer",
    "exper_request",
    "force_save_graph",
    "get_all_pages",
    "get_app_info",
    "get_block",
    "get_block_properties",
    "get_block_property",
    "get_current_block",
    "get_current_graph",
    "get_current_graph_configs",
    "get_current_graph_favorites",
    "get_current_graph_recent",
    "get_current_graph_templates",
    "get_current_page",
    "get_current_page_blocks_tree",
    "get_editing_block_content",
    "get_editing_cursor_position",
    "get_external_plugin",
    "get_next_sibling_block",
    "get_page",
    "get_page_blocks_tree",
    "get_page_linked_references",
    "get_pages_from_namespace",
    "get_pages_tree_from_namespace",
    "get_previous_sibling_block",
    "get_selected_blocks",
    "get_state_from_store",
    "get_template",
    "get_user_configs",
    "http_request_abort",
    "insert_at_editing_cursor",
    "insert_batch_block",
    "insert_block",
    "insert_template",
    "install-plugin-hook",
    "invoke_external_command",
    "invoke_external_plugin_cmd",
    "list_files_of_current_graph",
    "list_plugin_storage_files",
    "load_ignore_file",
    "load_plugin_config",
    "load_plugin_readme",
    "load_plugin_user_settings",
    "load_user_preferences",
    "log_app_state",
    "make_asset_url",
    "make_url",
    "move_block",
    "new_block_uuid",
    "open_external_link",
    "open_in_right_sidebar",
    "prepend_block_in_page",
    "push_state",
    "q",
    "query_element_by_id",
    "query_element_rect",
    "quit",
    "read_plugin_storage_file",
    "register_plugin_simple_command",
    "register_plugin_slash_command",
    "register_plugin_ui_item",
    "register_search_service",
    "relaunch",
    "remove_block",
    "remove_block_property",
    "remove_template",
    "rename_page",
    "replace_state",
    "resolve_theme_css_props_vals",
    "restore_editing_cursor",
    "save_focused_code_editor_content",
    "save_ignore_file",
    "save_plugin_config",
    "save_plugin_user_settings",
    "save_user_preferences",
    "search",
    "select_block",
    "set_block_collapsed",
    "set_blocks_id",
    "set_current_graph_configs",
    "set_focused_settings",
    "set_left_sidebar_visible",
    "set_right_sidebar_visible",
    "set_state_from_store",
    "set_theme_mode",
    "should-exec-plugin-hook",
    "show_msg",
    "show_themes",
    "uninstall-plugin-hook",
    "unlink_plugin_storage_file",
    "unlink_plugin_user_settings",
    "unregister_plugin_simple_command",
    "unregister_search_services",
    "update_block",
    "upsert_block_property",
    "validate_external_plugins",
    "version",
    "write_plugin_storage_file",
    "write_user_tmp_file",
]


# ---------------- Datalog query constants ----------------
# Named queries for common patterns. Parameterized ones are lambdas that
# return a datalog string given a user argument.

Q = {
    # Total block count (uuid present on every block).
    "COUNT_BLOCKS": '[:find (count ?b) . :where [?b :block/uuid _]]',

    # Total named pages (includes journals).
    "COUNT_PAGES": '[:find (count ?p) . :where [?p :block/name _]]',

    # Total journal pages.
    "COUNT_JOURNALS": '[:find (count ?p) . :where [?p :block/journal-day _]]',

    # Orphan pages: pages with no inbound refs/page-owner and not a journal.
    "ORPHAN_PAGES": (
        "[:find (pull ?p [:block/name :block/original-name])"
        " :where"
        "   [?p :block/name _]"
        "   (not [?p :block/journal-day])"
        "   (not-join [?p] [?any :block/page ?p])"
        "   (not-join [?p] [?any :block/refs ?p])]"
    ),

    # Broken refs: pages referenced from blocks but never opened (no file, not a
    # journal, and no blocks live on them). Returns (name, ref-count) rows.
    "BROKEN_REFS": (
        "[:find ?name (count ?b)"
        " :where"
        "   [?b :block/refs ?p]"
        "   [?p :block/name ?name]"
        "   (not [?p :block/file])"
        "   (not [?p :block/journal-day])"
        "   (not-join [?p] [?any :block/page ?p])]"
    ),

    # Tag frequency: pages grouped by how many blocks reference them.
    "TAG_FREQ": (
        "[:find ?name (count ?b)"
        " :where [?b :block/refs ?p] [?p :block/name ?name]]"
    ),

    # Distinct block-property keys across the graph.
    "PROP_KEYS": (
        "[:find [?k ...]"
        " :where [?b :block/properties ?props] [(keys ?props) [?k ...]]]"
    ),

    # Pages ranked by block count, descending (datomic doesn't sort — caller sorts).
    "LARGEST_PAGES": (
        "[:find ?name (count ?b)"
        " :where [?b :block/page ?p] [?p :block/name ?name]]"
    ),

    # Parameterized: blocks whose refs include a given page name.
    "BLOCKS_BY_TAG": lambda name: (
        "[:find (pull ?b [:block/uuid :block/content :block/page])"
        " :where"
        "   [?b :block/refs ?p]"
        "   [?p :block/name \"" + str(name).lower().replace('"', '\\"') + "\"]]"
    ),

    # Parameterized: pages whose name starts with a namespace prefix.
    "PAGES_IN_NAMESPACE": lambda ns: (
        "[:find (pull ?p [*])"
        " :where"
        "   [?p :block/name ?n]"
        "   [(clojure.string/starts-with? ?n \""
        + str(ns).lower().replace('"', '\\"')
        + "/\")]]"
    ),
}


# ---------------- Session + config ----------------

@dataclass
class Session:
    """Runtime configuration for the logseq CLI. Populated by load_session()."""
    token: str = ""
    host: str = "127.0.0.1"
    port: int = 12315
    graph: Optional[str] = None
    fmt: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    yes: bool = False
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    preferred_date_format: str = "MMM do, yyyy"


_SESSION: Optional[Session] = None


def set_session(s: Session) -> None:
    """Install `s` as the module-level session used by `call()`."""
    global _SESSION
    _SESSION = s


def _read_config_file() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(updates: dict) -> None:
    """Merge `updates` into ~/.config/.../state/config.json and chmod 600 it."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    existing = _read_config_file()
    existing.update(updates)
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(existing, f, indent=2, default=str)
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG_FILE)
    os.chmod(CONFIG_FILE, 0o600)


def _cli_get(ns: argparse.Namespace, name: str) -> Any:
    return getattr(ns, name, None) if ns is not None else None


def _refresh_date_format(s: Session) -> None:
    """Query `get_user_configs` to refresh the cached preferred_date_format.

    Silent if the server is unreachable — we keep whatever default/cached value.
    """
    try:
        data = call("logseq.App.getUserConfigs")
    except LogseqError:
        return
    if not isinstance(data, dict):
        return
    fmt = data.get("preferredDateFormat")
    if not fmt:
        return
    s.preferred_date_format = fmt
    save_config({
        "preferred_date_format": fmt,
        "preferred_date_format_cached_at": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def load_session(cli_args: argparse.Namespace) -> Session:
    """Build a Session from CLI flags, env vars, config file, and defaults.

    Precedence for each field: CLI → env → config file → built-in default.
    Also refreshes `preferred_date_format` from the server if stale (>7 days).
    """
    cfg = _read_config_file()
    env = os.environ

    def pick(cli_name: str, env_name: Optional[str], cfg_name: str, default: Any) -> Any:
        v = _cli_get(cli_args, cli_name)
        if v is not None:
            return v
        if env_name and env.get(env_name):
            return env[env_name]
        if cfg_name in cfg and cfg[cfg_name] is not None:
            return cfg[cfg_name]
        return default

    port_raw = pick("port", "LOGSEQ_PORT", "port", 12315)
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 12315

    s = Session(
        token=pick("token", "LOGSEQ_API_TOKEN", "token", "") or "",
        host=pick("host", "LOGSEQ_HOST", "host", "127.0.0.1"),
        port=port,
        graph=pick("graph", "LOGSEQ_GRAPH", "graph", None),
        fmt=_cli_get(cli_args, "fmt") or _cli_get(cli_args, "format"),
        limit=_cli_get(cli_args, "limit"),
        offset=_cli_get(cli_args, "offset"),
        yes=bool(_cli_get(cli_args, "yes")) or False,
        dry_run=bool(_cli_get(cli_args, "dry_run")) or False,
        verbose=bool(_cli_get(cli_args, "verbose")) or False,
        quiet=bool(_cli_get(cli_args, "quiet")) or False,
        preferred_date_format=cfg.get("preferred_date_format", "MMM do, yyyy"),
    )

    # Uuid-only is an alias for --format uuids on list results.
    if _cli_get(cli_args, "uuids_only"):
        s.fmt = "uuids"

    # Install for `call()` before we possibly re-hit the server.
    set_session(s)

    # Refresh preferred_date_format if missing or older than 7 days.
    cached_at = cfg.get("preferred_date_format_cached_at")
    stale = True
    if cached_at:
        try:
            dt = datetime.strptime(cached_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            stale = (datetime.now(timezone.utc) - dt) > timedelta(days=7)
        except ValueError:
            stale = True
    if stale and s.token:
        _refresh_date_format(s)

    return s


# ---------------- Errors ----------------

class LogseqError(Exception):
    """CLI-facing error with a stable kind + exit code + one-line message."""

    def __init__(
        self,
        kind: str,
        message: str,
        exit_code: int,
        detail: Optional[dict] = None,
    ):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.exit_code = exit_code
        self.detail = detail or {}


def _levenshtein(a: str, b: str) -> int:
    """Iterative DP edit distance. Pure Python, O(len(a)*len(b))."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(
                cur[j - 1] + 1,
                prev[j] + 1,
                prev[j - 1] + cost,
            )
        prev = cur
    return prev[-1]


def suggest_methods(wrong: str, n: int = 3) -> list:
    """Return the `n` closest KNOWN_METHODS names to `wrong` by Levenshtein."""
    w = (wrong or "").lower().replace(".", "_").replace("-", "_")
    # The server strips the namespace ("logseq.App.getPage" -> "get_page" via
    # snake_case). Mirror that by also trying a camelCase-to-snake collapse.
    w = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", wrong or "").lower()
    ranked = sorted(
        ((name, _levenshtein(w, name)) for name in KNOWN_METHODS),
        key=lambda kv: (kv[1], kv[0]),
    )
    return [name for name, _ in ranked[:max(0, n)]]


def classify_error(exc: BaseException) -> LogseqError:
    """Convert any exception into a LogseqError with kind + exit code."""
    if isinstance(exc, LogseqError):
        return exc
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 401:
            return LogseqError(
                "auth",
                "Invalid or missing token. Run `logseq init` to set one, "
                "or export `LOGSEQ_API_TOKEN`.",
                2,
                {"http_status": exc.code},
            )
        return LogseqError("other", f"HTTP {exc.code}: {exc.reason}", 1,
                           {"http_status": exc.code})
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", exc)
        host = _SESSION.host if _SESSION else "127.0.0.1"
        port = _SESSION.port if _SESSION else 12315
        msg = (
            f"Logseq HTTP API server is not running on {host}:{port}. "
            "Start it from the toolbar icon in Logseq, or run `logseq doctor`."
        )
        return LogseqError("refused", msg, 3, {"reason": str(reason)})
    return LogseqError("other", str(exc) or exc.__class__.__name__, 1)


# ---------------- HTTP client ----------------

def call(method: str, args: Optional[list] = None) -> Any:
    """POST /api on the configured host/port. Raises LogseqError on failure."""
    if _SESSION is None:
        raise LogseqError(
            "other",
            "No session loaded. Call load_session() before call().",
            1,
        )
    url = f"http://{_SESSION.host}:{_SESSION.port}/api"
    body = json.dumps({"method": method, "args": args or []}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_SESSION.token}" if _SESSION.token else "",
    }
    if _SESSION.verbose:
        err(f"POST {url} {json.dumps({'method': method, 'args': args or []})}")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise LogseqError(
                "auth",
                "Invalid or missing token. Run `logseq init` to set one, "
                "or export `LOGSEQ_API_TOKEN`.",
                2,
                {"http_status": e.code},
            )
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = ""
        raise LogseqError(
            "other",
            f"HTTP {e.code} {e.reason}: {detail}".strip(),
            1,
            {"http_status": e.code},
        )
    except urllib.error.URLError as e:
        raise classify_error(e)
    except (TimeoutError, OSError) as e:
        raise classify_error(e)

    if _SESSION.verbose:
        err(f"<< {raw[:500]}")

    # Empty body → None.
    if not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Some scalar returns come back as naked strings (possible in quirky
        # edge cases); treat raw text as the value.
        return raw

    if isinstance(data, dict) and "error" in data and len(data) == 1:
        msg = str(data["error"])
        low = msg.lower()
        if low.startswith("methodnotexist"):
            suggestions = suggest_methods(method, 3)
            friendly = (
                f"MethodNotExist: {method}. "
                f"Did you mean: {', '.join(suggestions)}?"
            )
            raise LogseqError(
                "method", friendly, 5,
                {"server_error": msg, "suggestions": suggestions},
            )
        if "unauthor" in low or "token" in low:
            raise LogseqError(
                "auth",
                "Invalid or missing token. Run `logseq init` to set one, "
                "or export `LOGSEQ_API_TOKEN`.",
                2,
                {"server_error": msg},
            )
        if "argument" in low or "arity" in low or "expected" in low:
            raise LogseqError(
                "args", f"Bad arguments for {method}: {msg}", 4,
                {"server_error": msg},
            )
        raise LogseqError("other", msg, 1, {"server_error": msg})
    return data


# ---------------- Formatters ----------------

def _trunc(s: str, n: int = 200) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "\u2026"


def as_json(data: Any) -> str:
    """Compact one-line JSON."""
    return json.dumps(data, separators=(",", ":"), default=str)


def as_pretty(data: Any) -> str:
    """Indented JSON for humans."""
    return json.dumps(data, indent=2, default=str)


def _render_block(b: dict, depth: int, lines: list, use_md: bool) -> None:
    bullet_indent = "  " * depth if use_md else "  " * depth
    content = b.get("content") or b.get("title") or ""
    if not use_md:
        content = _trunc(content, 200)
    prefix = "- " if True else ""
    if content:
        lines.append(f"{bullet_indent}{prefix}{content}")
    else:
        lines.append(f"{bullet_indent}{prefix}")
    props = b.get("properties") or {}
    if isinstance(props, dict):
        for k, v in props.items():
            lines.append(f"{bullet_indent}  {k}:: {v}")
    children = b.get("children") or []
    if isinstance(children, list):
        for c in children:
            if isinstance(c, dict):
                _render_block(c, depth + 1, lines, use_md)


def as_tree(data: Any) -> str:
    """Indented bullet outline for block-tree data. Content truncated to 200."""
    if data is None:
        return ""
    lines: list = []
    if isinstance(data, list):
        for b in data:
            if isinstance(b, dict):
                _render_block(b, 0, lines, use_md=False)
            else:
                lines.append(f"- {b}")
    elif isinstance(data, dict):
        _render_block(data, 0, lines, use_md=False)
    else:
        lines.append(str(data))
    return "\n".join(lines)


def as_md(data: Any) -> str:
    """Reconstruct Logseq-style markdown from a block tree (no truncation)."""
    if data is None:
        return ""
    lines: list = []
    if isinstance(data, list):
        for b in data:
            if isinstance(b, dict):
                _render_block(b, 0, lines, use_md=True)
            else:
                lines.append(f"- {b}")
    elif isinstance(data, dict):
        _render_block(data, 0, lines, use_md=True)
    else:
        lines.append(str(data))
    return "\n".join(lines)


def _cell(v: Any, width: int = 40) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return "..."
    s = str(v)
    if len(s) > width:
        s = s[: width - 1] + "\u2026"
    return s


def as_table(data: Any) -> str:
    """Fixed-width table for lists of homogeneous dicts (or scalars)."""
    if data is None:
        return ""
    if not isinstance(data, list):
        data = [data]
    if not data:
        return ""
    if all(not isinstance(x, (dict, list)) for x in data):
        return "\n".join(str(x) for x in data)
    # Pick columns from the first dict.
    first = next((x for x in data if isinstance(x, dict)), None)
    if first is None:
        return "\n".join(_cell(x) for x in data)
    cols = list(first.keys())
    rows = []
    for row in data:
        if not isinstance(row, dict):
            rows.append([_cell(row)] + [""] * (len(cols) - 1))
            continue
        rows.append([_cell(row.get(c)) for c in cols])
    widths = [len(c) for c in cols]
    for r in rows:
        for i, cell in enumerate(r):
            if len(cell) > widths[i]:
                widths[i] = len(cell)
    widths = [min(w, 40) for w in widths]

    def fmt_row(r: list) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(r))

    out_lines = [fmt_row(cols), fmt_row(["-" * w for w in widths])]
    for r in rows:
        out_lines.append(fmt_row(r))
    return "\n".join(out_lines)


def as_plain(data: Any) -> str:
    """One value per line. Dicts as `k=v`, lists flattened, scalars as str."""
    if data is None:
        return ""
    if isinstance(data, dict):
        return "\n".join(f"{k}={v}" for k, v in data.items())
    if isinstance(data, list):
        parts = []
        for x in data:
            if isinstance(x, (dict, list)):
                parts.append(json.dumps(x, default=str, separators=(",", ":")))
            else:
                parts.append(str(x) if x is not None else "")
        return "\n".join(parts)
    return str(data)


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def as_uuids(data: Any) -> str:
    """Filter down to block uuids, one per line.

    Walks nested structures (search results have `{blocks: [...], pages-content: [...]}`,
    each containing uuid-bearing dicts). Dedupes and preserves order. Handles both
    camelCase `uuid` and kebab-case `block/uuid` forms.
    """
    seen: list[str] = []
    seen_set: set[str] = set()

    def _record(u) -> None:
        s = str(u)
        if s and _UUID_RE.match(s) and s not in seen_set:
            seen.append(s)
            seen_set.add(s)

    def _walk(x) -> None:
        if x is None:
            return
        if isinstance(x, str):
            if _UUID_RE.match(x):
                _record(x)
            return
        if isinstance(x, dict):
            u = x.get("uuid") or x.get("block/uuid")
            if u:
                _record(u)
                return  # stop descending once we've recorded this block's uuid
            for v in x.values():
                _walk(v)
            return
        if isinstance(x, list):
            for v in x:
                _walk(v)
            return

    _walk(data)
    return "\n".join(seen)


# ---------------- Output dispatch ----------------

def is_tty() -> bool:
    """Whether stdout is attached to a terminal."""
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def err(msg: str) -> None:
    """Print one line to stderr (never to stdout)."""
    print(msg, file=sys.stderr, flush=True)


def _pick_default_fmt(data: Any, session: Optional[Session]) -> str:
    if isinstance(data, (str, int, float, bool)) or data is None:
        return "plain"
    return "pretty" if is_tty() else "json"


_FORMATTERS = {
    "json": as_json,
    "pretty": as_pretty,
    "tree": as_tree,
    "md": as_md,
    "table": as_table,
    "plain": as_plain,
    "uuids": as_uuids,
}


def out(data: Any, fmt: Optional[str] = None, session: Optional[Session] = None) -> None:
    """Render `data` to stdout using fmt → session.fmt → default (by type/TTY)."""
    chosen = fmt or (session.fmt if session else None)
    if chosen is None and _SESSION is not None and session is None:
        chosen = _SESSION.fmt
    if chosen is None:
        chosen = _pick_default_fmt(data, session or _SESSION)
    formatter = _FORMATTERS.get(chosen, as_pretty)
    text = formatter(data)
    if text is None:
        text = ""
    print(text)


# ---------------- Helpers: pfts, dates, confirm ----------------

_PFTS_RE = re.compile(r"\$pfts_[a-z0-9]+>\$|\$<pfts_[a-z0-9]+\$", re.I)


def strip_pfts(s: str) -> str:
    """Remove Logseq full-text-search `$pfts_xxx>$ ... $<pfts_xxx$` markers."""
    if not isinstance(s, str):
        return s
    return _PFTS_RE.sub("", s)


_REL_RE = re.compile(r"^-(\d+)(d|w|mo|y)$", re.I)
_ISO_RE = re.compile(r"^(\d{4})[-_](\d{1,2})[-_](\d{1,2})$")
_PRETTY_RE = re.compile(
    r"^(?P<mon>[A-Za-z]+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{4})$"
)


def _journal_day(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def parse_date(s: str) -> tuple:
    """Parse today/yesterday/-7d/ISO/pretty. Return (iso_string, journal_day)."""
    if not isinstance(s, str):
        raise LogseqError("args", f"parse_date: not a string: {s!r}", 4)
    t = s.strip()
    today = date.today()

    if t.lower() == "today":
        d = today
    elif t.lower() == "yesterday":
        d = today - timedelta(days=1)
    elif t.lower() == "tomorrow":
        d = today + timedelta(days=1)
    else:
        m = _REL_RE.match(t)
        if m:
            n, unit = int(m.group(1)), m.group(2).lower()
            if unit == "d":
                d = today - timedelta(days=n)
            elif unit == "w":
                d = today - timedelta(weeks=n)
            elif unit == "mo":
                # Approximate months as 30 days for v1 — precise month math is
                # out of scope and the caller can pass an ISO date for exact.
                d = today - timedelta(days=30 * n)
            elif unit == "y":
                try:
                    d = today.replace(year=today.year - n)
                except ValueError:
                    d = today - timedelta(days=365 * n)
            else:
                raise LogseqError("args", f"bad relative unit: {unit}", 4)
        else:
            m = _ISO_RE.match(t)
            if m:
                y, mo, dy = int(m.group(1)), int(m.group(2)), int(m.group(3))
                d = date(y, mo, dy)
            else:
                m = _PRETTY_RE.match(t)
                if m:
                    mon_raw = m.group("mon")
                    d = _parse_pretty(mon_raw, int(m.group("day")), int(m.group("year")))
                else:
                    raise LogseqError(
                        "args",
                        f"unrecognized date: {s!r}. "
                        "Try 'today', 'yesterday', '-7d', 'YYYY-MM-DD', "
                        "or 'Apr 17th, 2026'.",
                        4,
                    )
    return d.isoformat(), _journal_day(d)


_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _parse_pretty(mon_raw: str, day: int, year: int) -> date:
    key = mon_raw.strip().lower()
    if key not in _MONTHS:
        raise LogseqError("args", f"unknown month: {mon_raw!r}", 4)
    return date(year, _MONTHS[key], day)


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def format_date_for_logseq(d: date, session: Optional[Session] = None) -> str:
    """Render a `date` per the session's preferred_date_format."""
    fmt = (session.preferred_date_format if session else None) or (
        _SESSION.preferred_date_format if _SESSION else "MMM do, yyyy"
    )
    # Expand tokens in order of longest-first to avoid MM clashing with M, etc.
    out_parts: list = []
    i = 0
    while i < len(fmt):
        matched = False
        for token, value in (
            ("MMMM", d.strftime("%B")),
            ("MMM", d.strftime("%b")),
            ("MM", f"{d.month:02d}"),
            ("yyyy", f"{d.year:04d}"),
            ("yy", f"{d.year % 100:02d}"),
            ("dd", f"{d.day:02d}"),
            ("do", _ordinal(d.day)),
            ("d", str(d.day)),
            ("M", str(d.month)),
        ):
            if fmt.startswith(token, i):
                out_parts.append(value)
                i += len(token)
                matched = True
                break
        if not matched:
            out_parts.append(fmt[i])
            i += 1
    return "".join(out_parts)


def confirm(prompt: str, yes_flag: bool) -> bool:
    """Interactive yes/no gate. Returns False on non-interactive sessions."""
    if yes_flag:
        return True
    if not is_tty():
        return False
    try:
        reply = input(f"{prompt} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return reply in ("y", "yes")


# ---------------- Exports ----------------

__all__ = [
    "call", "LogseqError", "classify_error",
    "Session", "load_session", "save_config", "set_session", "CONFIG_FILE",
    "out", "err", "is_tty",
    "as_json", "as_pretty", "as_tree", "as_md", "as_table", "as_plain", "as_uuids",
    "KNOWN_METHODS", "Q",
    "strip_pfts", "parse_date", "format_date_for_logseq", "suggest_methods",
    "confirm",
]


# ---------------- Self-test ----------------

if __name__ == "__main__":
    ns = argparse.Namespace(
        token="cc", host="127.0.0.1", port=12315, graph=None,
        fmt=None, limit=None, offset=None, yes=False, dry_run=False,
        verbose=False, quiet=False, uuids_only=False,
    )
    s = load_session(ns)
    set_session(s)

    print("call(get_app_info):", call("logseq.App.getAppInfo"))
    print("parse_date(today):", parse_date("today"))
    print("parse_date(-7d):", parse_date("-7d"))
    print("parse_date(Apr 17th, 2026):", parse_date("Apr 17th, 2026"))
    print("parse_date(2026-04-17):", parse_date("2026-04-17"))
    print("format today:", format_date_for_logseq(date.today(), s))
    print("strip_pfts:", repr(strip_pfts("$pfts_2lqh>$ amazon $<pfts_2lqh$ foo")))
    print("suggest_methods(get_pag):", suggest_methods("get_pag"))
    print("suggest_methods(listfile):", suggest_methods("listfile"))
    print("Q.COUNT_BLOCKS result:", call("logseq.DB.datascriptQuery", [Q["COUNT_BLOCKS"]]))
    print("Q.TAG_FREQ (first 3):",
          (call("logseq.DB.datascriptQuery", [Q["TAG_FREQ"]]) or [])[:3])

    try:
        call("logseq.NoSuchThing.bogus")
    except LogseqError as e:
        print("method err classified:", e.kind, e.exit_code, "| msg:", e.message)

    # Format round-trips.
    sample_blocks = [{
        "uuid": "11111111-2222-3333-4444-555555555555",
        "content": "hello **world** [[foo]]",
        "properties": {"tags": "demo"},
        "children": [{"uuid": "22222222-2222-2222-2222-222222222222",
                      "content": "child block"}],
    }]
    print("-- as_tree --")
    print(as_tree(sample_blocks))
    print("-- as_md --")
    print(as_md(sample_blocks))
    print("-- as_table --")
    print(as_table([{"name": "a", "count": 3}, {"name": "bb", "count": 7}]))
    print("-- as_uuids --")
    print(as_uuids(sample_blocks))
    print("-- as_plain (dict) --")
    print(as_plain({"a": 1, "b": "two"}))

    print(f"__all__ exports: {len(__all__)}")
    print("All self-tests done.")
