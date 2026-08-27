#!/usr/bin/env python3
"""Stats, tags, and property queries for the logseq CLI.

Subcommands:
  stats                        summary dict (graph, blocks, pages, journals, tags)
  stats --broken-refs          pages referenced but never opened
  stats --orphans              pages with no inbound refs and no blocks
  stats --largest-pages [N]    top N pages by block count
  stats --histogram blocks-per-page [--top N]
  tags [--sort freq|name] [--limit N]
  tag-freq <name>              count blocks referencing a tag/page
  prop-keys                    distinct property keys across the graph
  prop-values <key>            distinct values seen for a key
  prop-search <key> [<value>]  blocks with the key (optionally matching value)
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from _logseq_common import call, out, Q  # noqa: E402

# NEEDS IN _logseq_common: Q["PROP_KEYS"] uses `(keys ?props)` which Logseq's
# datascript build rejects ("Unknown function 'keys"). This module works around
# it by pulling :block/properties for every block-with-properties and unioning
# keys client-side. A server-friendly rewrite would be ideal.


# ---------- stats dispatch ----------

def cmd_stats(args: argparse.Namespace, session) -> int:
    """Default summary or sub-report based on flags."""
    if args.broken_refs:
        return _broken_refs(args, session)
    if args.orphans:
        return _orphans(args, session)
    if args.largest_pages is not None:
        return _largest_pages(args, session)
    if args.histogram == "blocks-per-page":
        return _histogram_blocks_per_page(args, session)
    return _stats_summary(session)


def _stats_summary(session) -> int:
    graph = call("logseq.App.getCurrentGraph") or {}
    blocks = call("logseq.DB.datascriptQuery", [Q["COUNT_BLOCKS"]])
    pages = call("logseq.DB.datascriptQuery", [Q["COUNT_PAGES"]])
    journals = call("logseq.DB.datascriptQuery", [Q["COUNT_JOURNALS"]])
    tag_rows = call("logseq.DB.datascriptQuery", [Q["TAG_FREQ"]]) or []
    tag_count = len({r[0] for r in tag_rows if r})
    out({
        "graph": graph.get("name") if isinstance(graph, dict) else None,
        "path": graph.get("path") if isinstance(graph, dict) else None,
        "blocks": blocks,
        "pages": pages,
        "journals": journals,
        "tags": tag_count,
    }, session=session)
    return 0


def _broken_refs(args, session) -> int:
    rows = call("logseq.DB.datascriptQuery", [Q["BROKEN_REFS"]]) or []
    items = sorted(
        [{"page": r[0], "inbound_count": r[1]} for r in rows if r],
        key=lambda x: (-x["inbound_count"], x["page"]),
    )
    if args.top:
        items = items[: args.top]
    out(items, session=session)
    return 0


def _orphans(args, session) -> int:
    rows = call("logseq.DB.datascriptQuery", [Q["ORPHAN_PAGES"]]) or []
    items = []
    for r in rows:
        p = r[0] if isinstance(r, list) else r
        if not isinstance(p, dict):
            continue
        # Server returns hyphenated pull keys (`original-name`) — accept both.
        display = (p.get("original-name") or p.get("originalName")
                   or p.get("name"))
        items.append({"name": display, "db_id": p.get("id") or p.get("db/id")})
    if args.top:
        items = items[: args.top]
    out(items, session=session)
    return 0


def _largest_pages(args, session) -> int:
    # Query joins :block/name with :block/original-name so we return the
    # display-case name the user actually sees in the UI, not the lowercased
    # :block/name. Fall back to lowercased name if original-name is missing.
    q = (
        '[:find ?name ?original (count ?b) '
        ':where '
        ' [?b :block/page ?p] '
        ' [?p :block/name ?name] '
        ' [(get-else $ ?p :block/original-name ?name) ?original]]'
    )
    rows = call("logseq.DB.datascriptQuery", [q]) or []
    items = [{"page": r[1], "blocks": r[2]} for r in rows if r and len(r) >= 3]
    items.sort(key=lambda x: (-x["blocks"], x["page"]))
    top = args.largest_pages or args.top or 20
    out(items[:top], session=session)
    return 0


def _histogram_blocks_per_page(args, session) -> int:
    rows = call("logseq.DB.datascriptQuery", [Q["LARGEST_PAGES"]]) or []
    pairs = sorted(
        [(r[0], r[1]) for r in rows if r],
        key=lambda kv: (-kv[1], kv[0]),
    )
    if args.top:
        pairs = pairs[: args.top]
    out(dict(pairs), session=session)
    return 0


# ---------- tags ----------

def cmd_tags(args, session) -> int:
    rows = call("logseq.DB.datascriptQuery", [Q["TAG_FREQ"]]) or []
    items = [{"name": r[0], "count": r[1]} for r in rows if r]
    if args.sort == "name":
        items.sort(key=lambda x: x["name"])
    else:
        items.sort(key=lambda x: (-x["count"], x["name"]))
    if args.limit:
        items = items[: args.limit]
    out(items, session=session)
    return 0


def cmd_tag_freq(args, session) -> int:
    name = str(args.name).lower().replace('"', '\\"')
    q = (
        '[:find (count ?b) . '
        ':where [?b :block/refs ?p] '
        f'[?p :block/name "{name}"]]'
    )
    count = call("logseq.DB.datascriptQuery", [q]) or 0
    out(count, session=session)
    return 0


# ---------- properties ----------

def _collect_prop_maps() -> list:
    """Pull every :block/properties map. Used by prop-keys/values workarounds."""
    q = ('[:find (pull ?b [:block/properties]) '
         ':where [?b :block/properties _]]')
    rows = call("logseq.DB.datascriptQuery", [q]) or []
    maps = []
    for r in rows:
        b = r[0] if isinstance(r, list) else r
        if isinstance(b, dict):
            p = b.get("properties")
            if isinstance(p, dict):
                maps.append(p)
    return maps


def cmd_prop_keys(args, session) -> int:
    """Logseq datascript rejects `(keys ?props)`; aggregate client-side."""
    keys = set()
    for p in _collect_prop_maps():
        for k in p.keys():
            keys.add(str(k).lstrip(":"))
    out(sorted(keys), session=session)
    return 0


def cmd_prop_values(args, session) -> int:
    key = args.key.lstrip(":")
    q = (
        '[:find ?v '
        ':where [?b :block/properties ?props] '
        f'[(get ?props :{key}) ?v]]'
    )
    rows = call("logseq.DB.datascriptQuery", [q]) or []
    values = set()
    for r in rows:
        v = r[0] if isinstance(r, list) else r
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for item in v:
                values.add(item)
        else:
            values.add(v)
    out(sorted(values, key=lambda x: str(x)), session=session)
    return 0


def cmd_prop_search(args, session) -> int:
    key = args.key.lstrip(":")
    pull = '[:block/uuid :block/content :block/properties :block/page]'
    if args.value is None:
        q = (
            f'[:find (pull ?b {pull}) '
            ':where [?b :block/properties ?props] '
            f'[(contains? ?props :{key})]]'
        )
    else:
        lit = str(args.value).replace('"', '\\"')
        q = (
            f'[:find (pull ?b {pull}) '
            ':where [?b :block/properties ?props] '
            f'[(get ?props :{key}) ?v] '
            f'[(= ?v "{lit}")]]'
        )
    rows = call("logseq.DB.datascriptQuery", [q]) or []
    blocks = [r[0] for r in rows if r and r[0]]
    out(blocks, session=session)
    return 0


# ---------- argparse registration ----------

HANDLERS = {
    "stats": cmd_stats,
    "tags": cmd_tags,
    "tag-freq": cmd_tag_freq,
    "prop-keys": cmd_prop_keys,
    "prop-values": cmd_prop_values,
    "prop-search": cmd_prop_search,
}


def register(subparsers) -> None:
    p = subparsers.add_parser("stats", help="Graph stats + sub-reports")
    p.add_argument("--broken-refs", action="store_true",
                   help="Pages referenced but never opened")
    p.add_argument("--orphans", action="store_true",
                   help="Pages with no inbound refs and no blocks")
    p.add_argument("--largest-pages", type=int, metavar="N", nargs="?", const=20,
                   help="Top N pages by block count (default 20)")
    p.add_argument("--histogram", choices=["blocks-per-page"],
                   help="Emit a histogram map")
    p.add_argument("--top", type=int, help="Cap any sub-report to top N entries")
    p.set_defaults(func=cmd_stats)

    p = subparsers.add_parser("tags", help="List tags with frequency")
    p.add_argument("--sort", choices=["freq", "name"], default="freq")
    p.add_argument("--limit", type=int, help="Cap results")
    p.set_defaults(func=cmd_tags)

    p = subparsers.add_parser("tag-freq", help="Count blocks referencing a tag/page")
    p.add_argument("name")
    p.set_defaults(func=cmd_tag_freq)

    p = subparsers.add_parser("prop-keys", help="All property keys in use")
    p.set_defaults(func=cmd_prop_keys)

    p = subparsers.add_parser("prop-values", help="Distinct values for a property key")
    p.add_argument("key")
    p.set_defaults(func=cmd_prop_values)

    p = subparsers.add_parser("prop-search",
                              help="Blocks matching a property (key [value])")
    p.add_argument("key")
    p.add_argument("value", nargs="?", default=None)
    p.set_defaults(func=cmd_prop_search)


# ---------- self-test ----------

if __name__ == "__main__":
    import argparse as _ap
    from _logseq_common import load_session, set_session  # noqa: E402

    ns = _ap.Namespace(token="cc", host="127.0.0.1", port=12315, graph=None,
                       fmt="json", limit=None, offset=None, yes=False,
                       dry_run=False, verbose=False, quiet=False,
                       uuids_only=False)
    s = load_session(ns)
    set_session(s)

    print("-- stats --")
    cmd_stats(_ap.Namespace(broken_refs=False, orphans=False,
                            largest_pages=None, histogram=None, top=None), s)
    print("-- stats --broken-refs --")
    cmd_stats(_ap.Namespace(broken_refs=True, orphans=False,
                            largest_pages=None, histogram=None, top=None), s)
    print("-- stats --orphans --")
    cmd_stats(_ap.Namespace(broken_refs=False, orphans=True,
                            largest_pages=None, histogram=None, top=None), s)
    print("-- stats --largest-pages 5 --")
    cmd_stats(_ap.Namespace(broken_refs=False, orphans=False,
                            largest_pages=5, histogram=None, top=None), s)
    print("-- stats --histogram blocks-per-page --top 5 --")
    cmd_stats(_ap.Namespace(broken_refs=False, orphans=False,
                            largest_pages=None, histogram="blocks-per-page",
                            top=5), s)
    print("-- tags --")
    cmd_tags(_ap.Namespace(sort="freq", limit=10), s)
    print("-- tag-freq simple-tag --")
    cmd_tag_freq(_ap.Namespace(name="simple-tag"), s)
    print("-- prop-keys --")
    cmd_prop_keys(_ap.Namespace(), s)
    print("-- prop-values status --")
    cmd_prop_values(_ap.Namespace(key="status"), s)
    print("-- prop-search status draft --")
    cmd_prop_search(_ap.Namespace(key="status", value="draft"), s)
    print("-- prop-search status (no value) --")
    cmd_prop_search(_ap.Namespace(key="status", value=None), s)
    print("All stats.py self-tests done.")
