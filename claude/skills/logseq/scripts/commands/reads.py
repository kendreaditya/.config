#!/usr/bin/env python3
"""Read-only commands for the logseq CLI.

Subcommands: today, yesterday, tomorrow, journals, page, pages, block, props,
prop, backlinks, tag, search, recent, favorites, templates.
Exports: HANDLERS dict + register(subparsers).
"""
from __future__ import annotations

import argparse, os, re, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from _logseq_common import (  # noqa: E402
    call, out, err, Session,
    format_date_for_logseq, parse_date, strip_pfts, Q,
    project_fields,
)


_EMBED_RE = re.compile(r'\(\(([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\)\)', re.I)


def _resolve_embeds_in_tree(tree, _cache=None, _seen=None):
    """Recursively resolve `((uuid))` embed placeholders inline within block content.

    - Pure embed content (`((uuid))` alone) → replaced by the target's content.
    - Inline embeds (`"See ((uuid)) for context"`) → substring substitution.
    - Missing targets render as `((uuid: not found))`.
    - Tracks a visited set to short-circuit circular refs (`((uuid: circular))`).

    Mutates the tree in place and returns it.
    """
    if _cache is None:
        _cache = {}
    if _seen is None:
        _seen = set()

    def _fetch(uuid: str) -> str:
        if uuid in _cache:
            return _cache[uuid]
        if uuid in _seen:
            _cache[uuid] = f"((uuid: circular))"
            return _cache[uuid]
        _seen.add(uuid)
        blk = call("logseq.Editor.getBlock", [uuid])
        if blk and blk.get("content"):
            resolved = _EMBED_RE.sub(lambda m: _fetch(m.group(1)), blk["content"])
            _cache[uuid] = resolved
        else:
            _cache[uuid] = f"((uuid: not found))"
        _seen.discard(uuid)
        return _cache[uuid]

    def _walk(node):
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if not isinstance(node, dict):
            return
        content = node.get("content")
        if isinstance(content, str) and _EMBED_RE.search(content):
            node["content"] = _EMBED_RE.sub(lambda m: _fetch(m.group(1)), content)
        for c in (node.get("children") or []):
            _walk(c)

    _walk(tree)
    return tree


# ---------------- Journal-day enrichment ----------------

_JOURNAL_DAY_CACHE: dict = {}


def _journal_day_map() -> dict:
    """Return {page_id: {"journal_day": int, "name": str}} for every journal page.

    Cached per process — one datalog round-trip enriches any number of blocks.
    """
    global _JOURNAL_DAY_CACHE
    if _JOURNAL_DAY_CACHE:
        return _JOURNAL_DAY_CACHE
    q = (
        "[:find ?p ?jd ?name"
        " :where"
        "   [?p :block/journal-day ?jd]"
        "   [?p :block/original-name ?name]]"
    )
    rows = call("logseq.DB.datascriptQuery", [q]) or []
    _JOURNAL_DAY_CACHE = {
        row[0]: {"journal_day": row[1], "name": row[2]}
        for row in rows if isinstance(row, list) and len(row) >= 3
    }
    return _JOURNAL_DAY_CACHE


def _iso_from_journal_day(jd) -> str:
    """20241231 -> '2024-12-31'. Returns '' on bad input."""
    try:
        n = int(jd)
        y, m, d = n // 10000, (n // 100) % 100, n % 100
        return f"{y:04d}-{m:02d}-{d:02d}"
    except (TypeError, ValueError):
        return ""


def _extract_page_id(block: dict):
    """Block shape is bimodal (camelCase from API, kebab from datalog). Return page id or None."""
    page = block.get("page") or block.get("block/page")
    if isinstance(page, dict):
        return page.get("id")
    if isinstance(page, int):
        return page
    return None


def _enrich_with_dates(blocks: list) -> list:
    """Add `journal_day` (ISO string) and `page_name` to each block-shaped dict."""
    if not isinstance(blocks, list):
        return blocks
    page_ids = {pid for b in blocks if isinstance(b, dict) and (pid := _extract_page_id(b))}
    if not page_ids:
        return blocks
    jmap = _journal_day_map()
    for b in blocks:
        if not isinstance(b, dict):
            continue
        pid = _extract_page_id(b)
        info = jmap.get(pid)
        if info:
            b["journal_day"] = _iso_from_journal_day(info["journal_day"])
            b["page_name"] = info["name"]
    return blocks
def _dump_journal_day(d: date, args, session: Session) -> int:
    """Fetch journal page (or tree if --tree) for `d` via preferred date format."""
    formatted = format_date_for_logseq(d, session)
    if getattr(args, "tree", False):
        tree = call("logseq.Editor.getPageBlocksTree", [formatted])
        if not tree:
            err(f"No journal page for {formatted}"); return 4
        out(tree, fmt=(session.fmt or "tree"), session=session)
    else:
        page = call("logseq.Editor.getPage", [formatted])
        if not page:
            err(f"No journal page for {formatted}"); return 4
        out(page, session=session)
    return 0

def cmd_today(args, session):
    """Today's journal page (or tree if --tree)."""
    return _dump_journal_day(date.today(), args, session)

def cmd_yesterday(args, session):
    """Yesterday's journal page (or tree if --tree)."""
    return _dump_journal_day(date.today() - timedelta(days=1), args, session)

def cmd_tomorrow(args, session):
    """Tomorrow's journal page (or tree if --tree)."""
    return _dump_journal_day(date.today() + timedelta(days=1), args, session)

def cmd_journals(args, session):
    """List journal pages by --last N, --since/--until, or --on DATE."""
    if args.last is not None:
        n = max(0, min(int(args.last), 365))
        dates = [date.today() - timedelta(days=i) for i in range(n)]
    elif args.on is not None:
        dates = [date.fromisoformat(parse_date(args.on)[0])]
    elif args.since is not None:
        start = date.fromisoformat(parse_date(args.since)[0])
        end = date.fromisoformat(parse_date(args.until)[0]) if args.until else date.today()
        if end < start: start, end = end, start
        span = min((end - start).days + 1, 365)
        dates = [start + timedelta(days=i) for i in range(span)]
    else:
        err("journals: one of --last, --since, or --on is required"); return 4

    results = []
    for d in dates:
        formatted = format_date_for_logseq(d, session)
        method = "logseq.Editor.getPageBlocksTree" if args.tree else "logseq.Editor.getPage"
        data = call(method, [formatted])
        if data:
            results.append({"date": formatted, "data": data})
    if not results:
        err("No journal pages found in range"); return 4
    if args.tree:
        flat = [{"content": f"== {r['date']} ==", "children": r["data"] or []} for r in results]
        out(flat, fmt=(session.fmt or "tree"), session=session)
    else:
        out([r["data"] for r in results], session=session)
    return 0
def cmd_page(args, session):
    """Fetch a page by name (optionally its block tree with --tree)."""
    page = call("logseq.Editor.getPage", [args.name])
    if not page:
        err(f"Page not found: {args.name}"); return 4
    if args.tree:
        tree = call("logseq.Editor.getPageBlocksTree", [args.name])
        if getattr(args, "resolve_embeds", False):
            _resolve_embeds_in_tree(tree)
        out(tree, fmt=(session.fmt or "tree"), session=session)
    else:
        out(page, session=session)
    return 0

def cmd_pages(args, session):
    """List pages (filter by regex, or scope to a namespace)."""
    if args.namespace_tree:
        result = call("logseq.Editor.getPagesTreeFromNamespace", [args.namespace_tree])
    elif args.namespace:
        result = call("logseq.Editor.getPagesFromNamespace", [args.namespace])
    else:
        result = call("logseq.Editor.getAllPages")
    if args.filter and isinstance(result, list):
        try:
            pat = re.compile(args.filter)
        except re.error as e:
            err(f"bad --filter regex: {e}"); return 4
        result = [p for p in result if isinstance(p, dict)
                  and pat.search(p.get("originalName") or p.get("name") or "")]
    out(result, session=session)
    return 0

def cmd_block(args, session):
    """Fetch a single block by uuid (optionally with children)."""
    blk = call("logseq.Editor.getBlock", [args.uuid, {"includeChildren": bool(args.children)}])
    if blk and getattr(args, "resolve_embeds", False):
        _resolve_embeds_in_tree(blk)
    if not blk:
        # Before bailing, check if the UUID belongs to a page — search's
        # `pages-content` array returns page UUIDs that look identical to block
        # UUIDs. Give an actionable hint.
        q = (
            '[:find ?name :where'
            f' [?e :block/uuid #uuid "{args.uuid}"]'
            ' [?e :block/original-name ?name]]'
        )
        try:
            rows = call("logseq.DB.datascriptQuery", [q]) or []
        except Exception:
            rows = []
        if rows and rows[0]:
            name = rows[0][0]
            err(f"That UUID is the page {name!r}, not a block. Try: logseq page {name!r}")
            return 4
        err(f"Block not found: {args.uuid}")
        return 4
    out(blk, fmt=session.fmt or ("tree" if args.children else None), session=session)
    return 0

def cmd_props(args, session):
    """Get all properties on a block."""
    out(call("logseq.Editor.getBlockProperties", [args.uuid]), session=session); return 0

def cmd_prop(args, session):
    """Get one property on a block."""
    out(call("logseq.Editor.getBlockProperty", [args.uuid, args.key]), session=session); return 0
def cmd_backlinks(args, session):
    """Linked references to a page, flattened to {page: [blocks]}."""
    raw = call("logseq.Editor.getPageLinkedReferences", [args.page])
    flat = {}
    if raw:
        for pair in raw:
            if not pair or len(pair) < 2:
                continue
            p = pair[0] or {}
            name = p.get("originalName") or p.get("name") or "?"
            blocks = pair[1] or []
            if getattr(args, "with_dates", False):
                _enrich_with_dates(blocks)
            flat[name] = blocks
    fields = getattr(args, "fields", None)
    if fields:
        flat = project_fields(flat, [f for f in fields.split(",") if f.strip()])
    out(flat, session=session)
    return 0

def cmd_tag(args, session):
    """All blocks referencing a tag (page)."""
    rows = call("logseq.DB.datascriptQuery", [Q["BLOCKS_BY_TAG"](args.name)]) or []
    # Datalog pull returns [[{block}], ...] — flatten to list of block dicts for enrichment.
    blocks = [row[0] for row in rows if isinstance(row, list) and row and isinstance(row[0], dict)]
    if getattr(args, "with_dates", False):
        _enrich_with_dates(blocks)
    out(blocks if getattr(args, "with_dates", False) else rows, session=session)
    return 0

def cmd_timeline(args, session):
    """All blocks referencing a page, grouped by journal date (most-recent first).

    Default: uses indexed refs (`getPageLinkedReferences`). Fast, but misses
    refs that didn't populate in `:block/refs` (per gotcha #5).
    With --text: content substring match via datalog. Slower, broader net.
    """
    all_blocks = []
    if getattr(args, "text", False):
        # Case-insensitive regex match via re-pattern. DataScript's reader-level
        # `#"..."` literal trips on backslashes in the embedded string; constructing
        # the pattern at runtime sidesteps that.
        needle = re.escape(args.page).replace('\\', '\\\\').replace('"', '\\"')
        q = (
            "[:find (pull ?b [:block/uuid :block/content :block/page])"
            " :where"
            "   [?b :block/content ?c]"
            f"   [(re-pattern \"(?i){needle}\") ?pat]"
            "   [(re-find ?pat ?c)]]"
        )
        rows = call("logseq.DB.datascriptQuery", [q]) or []
        all_blocks = [r[0] for r in rows if isinstance(r, list) and r and isinstance(r[0], dict)]
    else:
        raw = call("logseq.Editor.getPageLinkedReferences", [args.page])
        if raw:
            for pair in raw:
                if not pair or len(pair) < 2:
                    continue
                for b in (pair[1] or []):
                    if isinstance(b, dict):
                        all_blocks.append(b)
    if not all_blocks:
        err(f"No references to {args.page!r}"); return 4
    _enrich_with_dates(all_blocks)

    # Group by date. Non-journal refs bucket under "(undated)".
    groups: dict = {}
    for b in all_blocks:
        key = b.get("journal_day") or "(undated)"
        groups.setdefault(key, []).append(b)

    # Sort keys: real dates, "(undated)" always last regardless of order.
    desc = getattr(args, "order", "desc") != "asc"
    dated = sorted((k for k in groups if k != "(undated)"), reverse=desc)
    ordered = dated + (["(undated)"] if "(undated)" in groups else [])

    fields = getattr(args, "fields", None)
    field_list = [f for f in fields.split(",") if f.strip()] if fields else None

    fmt = session.fmt or ("pretty" if sys.stdout.isatty() else "plain")
    if fmt in ("json", "pretty"):
        payload = {k: groups[k] for k in ordered}
        if field_list:
            payload = project_fields(payload, field_list)
        out(payload, session=session)
        return 0
    # Plain / md / tree — render as date-headed outline.
    lines = []
    for k in ordered:
        lines.append(f"## {k}" if fmt == "md" else k)
        for b in groups[k]:
            content = (b.get("content") or "").strip()
            if content:
                lines.append(f"  - {content}")
        lines.append("")
    print("\n".join(lines).rstrip())
    return 0

def _strip_result_pfts(x):
    if isinstance(x, dict): return {k: _strip_result_pfts(v) for k, v in x.items()}
    if isinstance(x, list): return [_strip_result_pfts(v) for v in x]
    if isinstance(x, str): return strip_pfts(x)
    return x

def cmd_search(args, session):
    """Full-text search; strips PFTS markers and caps with --limit.

    Note: `blocks` entries are actual blocks (uuid → `logseq block <uuid>`).
    `pages-content` entries return PAGE uuids, not block uuids — use `logseq page <name>`.
    """
    result = _strip_result_pfts(call("logseq.App.search", [args.query]))
    if args.limit and isinstance(result, dict):
        for key in ("blocks", "pages-content", "pages", "files"):
            if isinstance(result.get(key), list):
                result[key] = result[key][: args.limit]
    if getattr(args, "with_dates", False) and isinstance(result, dict):
        blocks = result.get("blocks")
        if isinstance(blocks, list):
            # search returns kebab-case `block/page` ids; enricher handles both.
            _enrich_with_dates(blocks)
    fields = getattr(args, "fields", None)
    if fields:
        result = project_fields(result, [f for f in fields.split(",") if f.strip()])
    out(result, session=session)
    return 0
def cmd_recent(args, session):
    """Graph recent pages."""
    out(call("logseq.App.getCurrentGraphRecent"), session=session); return 0

def cmd_favorites(args, session):
    """Graph favorites."""
    out(call("logseq.App.getCurrentGraphFavorites"), session=session); return 0

def cmd_templates(args, session):
    """Graph templates."""
    out(call("logseq.App.getCurrentGraphTemplates"), session=session); return 0
HANDLERS = {
    "today": cmd_today, "yesterday": cmd_yesterday, "tomorrow": cmd_tomorrow,
    "journals": cmd_journals, "page": cmd_page, "pages": cmd_pages,
    "block": cmd_block, "props": cmd_props, "prop": cmd_prop,
    "backlinks": cmd_backlinks, "tag": cmd_tag, "search": cmd_search,
    "timeline": cmd_timeline,
    "recent": cmd_recent, "favorites": cmd_favorites, "templates": cmd_templates,
}

def register(subparsers):
    """Attach all reads.py subparsers to the CLI."""
    def sp(name, help_str, fn):
        p = subparsers.add_parser(name, help=help_str); p.set_defaults(func=fn); return p

    for name, fn in (("today", cmd_today), ("yesterday", cmd_yesterday), ("tomorrow", cmd_tomorrow)):
        sp(name, f"{name.capitalize()}'s journal", fn).add_argument("--tree", action="store_true")

    p = sp("journals", "Journal pages in a range", cmd_journals)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--last", type=int, help="Last N days (max 365)")
    g.add_argument("--since", type=str, help="Start date (inclusive)")
    g.add_argument("--on", type=str, help="Single date")
    p.add_argument("--until", type=str, help="End date (with --since)")
    p.add_argument("--tree", action="store_true")

    p = sp("page", "Fetch a page by name", cmd_page)
    p.add_argument("name")
    p.add_argument("--tree", action="store_true")
    p.add_argument("--resolve-embeds", action="store_true",
                   help="Replace ((uuid)) embed placeholders with target block content (requires --tree)")

    p = sp("pages", "List pages", cmd_pages)
    p.add_argument("--filter", type=str, help="Regex on page name")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--namespace", type=str, help="Pages under a namespace prefix")
    g.add_argument("--namespace-tree", type=str, help="Namespace as a tree")

    p = sp("block", "Fetch a block by uuid", cmd_block)
    p.add_argument("uuid")
    p.add_argument("--children", action="store_true")
    p.add_argument("--resolve-embeds", action="store_true",
                   help="Replace ((uuid)) embed placeholders with target block content")

    sp("props", "Get all properties on a block", cmd_props).add_argument("uuid")
    p = sp("prop", "Get one property on a block", cmd_prop)
    p.add_argument("uuid"); p.add_argument("key")

    p = sp("backlinks", "Linked references to a page", cmd_backlinks)
    p.add_argument("page")
    p.add_argument("--with-dates", action="store_true",
                   help="Inject journal_day (ISO) + page_name on each block")
    p.add_argument("--fields", type=str, metavar="k1,k2,...",
                   help="Comma-separated keys to keep on each block (e.g. 'content,journal_day')")

    p = sp("tag", "All blocks referencing a tag (page)", cmd_tag)
    p.add_argument("name")
    p.add_argument("--with-dates", action="store_true",
                   help="Inject journal_day (ISO) + page_name on each block")

    p = sp("timeline", "Chronological backlinks to a page (dated, grouped)", cmd_timeline)
    p.add_argument("page")
    p.add_argument("--text", action="store_true",
                   help="Match by content substring (broader; catches un-indexed refs)")
    p.add_argument("--order", choices=["asc", "desc"], default="desc",
                   help="Date ordering (default: desc, newest first)")
    p.add_argument("--fields", type=str, metavar="k1,k2,...",
                   help="JSON output only: comma-separated keys to keep on each block")

    p = sp("search", "Full-text search", cmd_search)
    p.add_argument("query")
    p.add_argument("--limit", type=int)
    p.add_argument("--with-dates", action="store_true",
                   help="Inject journal_day + page_name on each block result")
    p.add_argument("--fields", type=str, metavar="k1,k2,...",
                   help="Comma-separated keys to keep on each result (e.g. 'content,uuid')")

    for name, fn in (("recent", cmd_recent), ("favorites", cmd_favorites), ("templates", cmd_templates)):
        sp(name, f"Graph {name}", fn)
if __name__ == "__main__":
    import json as _json
    from _logseq_common import load_session, set_session
    _N = argparse.Namespace
    ns = _N(token="cc", host="127.0.0.1", port=12315, graph=None, fmt="json",
            limit=None, offset=None, yes=False, dry_run=False, verbose=False, quiet=False)
    s = load_session(ns); set_session(s)

    print("-- page 'Reading List' --"); cmd_page(_N(name="Reading List", tree=False), s)
    print("-- page 'Reading List' --tree --"); cmd_page(_N(name="Reading List", tree=True), s)
    print("-- pages (filter=Orphan) --"); cmd_pages(_N(filter="Orphan", namespace=None, namespace_tree=None), s)
    print("-- pages --namespace Notes --"); cmd_pages(_N(filter=None, namespace="Notes", namespace_tree=None), s)
    print("-- backlinks 'Tag One' --"); cmd_backlinks(_N(page="Tag One"), s)
    print("-- tag simple-tag --"); cmd_tag(_N(name="simple-tag"), s)
    print("-- search resurfacetestmagicword --"); cmd_search(_N(query="resurfacetestmagicword", limit=None), s)
    print("-- today --"); cmd_today(_N(tree=False), s)
    print("-- today --tree --"); cmd_today(_N(tree=True), s)
    print("-- journals --last 7 --"); cmd_journals(_N(last=7, since=None, on=None, until=None, tree=False), s)
    print("-- recent --"); cmd_recent(_N(), s)

    mf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "seed_manifest.json")
    if os.path.exists(mf_path) and (mf := _json.load(open(mf_path))).get("blocks"):
        uuid = mf["blocks"][0]["uuid"]
        print(f"-- block {uuid} --"); cmd_block(_N(uuid=uuid, children=True), s)
        print(f"-- props {uuid} --"); cmd_props(_N(uuid=uuid), s)
    print("All reads.py self-tests done.")
