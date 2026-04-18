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
)
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
    if not blk:
        err(f"Block not found: {args.uuid}"); return 4
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
            flat[name] = pair[1] or []
    out(flat, session=session)
    return 0

def cmd_tag(args, session):
    """All blocks referencing a tag (page)."""
    out(call("logseq.DB.datascriptQuery", [Q["BLOCKS_BY_TAG"](args.name)]), session=session)
    return 0

def _strip_result_pfts(x):
    if isinstance(x, dict): return {k: _strip_result_pfts(v) for k, v in x.items()}
    if isinstance(x, list): return [_strip_result_pfts(v) for v in x]
    if isinstance(x, str): return strip_pfts(x)
    return x

def cmd_search(args, session):
    """Full-text search; strips PFTS markers and caps with --limit."""
    result = _strip_result_pfts(call("logseq.App.search", [args.query]))
    if args.limit and isinstance(result, dict):
        for key in ("blocks", "pages-content", "pages", "files"):
            if isinstance(result.get(key), list):
                result[key] = result[key][: args.limit]
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
    p.add_argument("name"); p.add_argument("--tree", action="store_true")

    p = sp("pages", "List pages", cmd_pages)
    p.add_argument("--filter", type=str, help="Regex on page name")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--namespace", type=str, help="Pages under a namespace prefix")
    g.add_argument("--namespace-tree", type=str, help="Namespace as a tree")

    p = sp("block", "Fetch a block by uuid", cmd_block)
    p.add_argument("uuid"); p.add_argument("--children", action="store_true")

    sp("props", "Get all properties on a block", cmd_props).add_argument("uuid")
    p = sp("prop", "Get one property on a block", cmd_prop)
    p.add_argument("uuid"); p.add_argument("key")

    sp("backlinks", "Linked references to a page", cmd_backlinks).add_argument("page")
    sp("tag", "All blocks referencing a tag (page)", cmd_tag).add_argument("name")

    p = sp("search", "Full-text search", cmd_search)
    p.add_argument("query"); p.add_argument("--limit", type=int)

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
