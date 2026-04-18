#!/usr/bin/env python3
"""Raw / escape-hatch commands for the logseq CLI.

Subcommands:
  datalog '<query>'      -> logseq.DB.datascriptQuery
  q '<expr>'             -> logseq.DB.q (simplified syntax)
  custom-query '<edn>'   -> logseq.DB.customQuery
  raw <method> [--args JSON]    -> arbitrary method invocation
  raw --list [--grep PAT]       -> list KNOWN_METHODS

Exports: HANDLERS dict + register(subparsers).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from _logseq_common import (  # noqa: E402
    KNOWN_METHODS,
    Session,
    call,
    err,
    out,
)


# ---------- datalog / q / custom-query ----------

def cmd_datalog(args: argparse.Namespace, session: Session) -> int:
    """Pass-through: raw Datalog query via datascript_query."""
    result = call("logseq.DB.datascriptQuery", [args.query])
    out(result, session=session)
    return 0


def cmd_q(args: argparse.Namespace, session: Session) -> int:
    """Logseq simplified query syntax — e.g. (page "X"), (tag "X"), (task TODO)."""
    result = call("logseq.DB.q", [args.expr])
    out(result, session=session)
    return 0


def cmd_custom_query(args: argparse.Namespace, session: Session) -> int:
    """Logseq custom-query EDN structure (as a single string)."""
    result = call("logseq.DB.customQuery", [args.edn])
    out(result, session=session)
    return 0


# ---------- raw method invocation ----------

def _is_known(method: str) -> bool:
    """KNOWN_METHODS stores bare snake_case names. Match either dotted or bare."""
    if not method:
        return False
    if method in KNOWN_METHODS:
        return True
    tail = method.split(".")[-1]
    # Convert camelCase tail to snake_case for comparison.
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", tail).lower()
    return snake in KNOWN_METHODS or tail in KNOWN_METHODS


def cmd_raw(args: argparse.Namespace, session: Session) -> int:
    """Generic method invocation, or --list to dump KNOWN_METHODS."""
    if args.list:
        methods = sorted(KNOWN_METHODS)
        if args.grep:
            try:
                rx = re.compile(args.grep, re.IGNORECASE)
            except re.error as e:
                err(f"raw --grep: bad regex: {e}")
                return 4
            methods = [m for m in methods if rx.search(m)]
        # A flat list of names reads best as one-per-line. Honor an explicit
        # --format override; otherwise force "plain".
        fmt = session.fmt or "plain"
        out(methods, fmt=fmt, session=session)
        return 0

    if not args.method:
        err("raw: method required (or pass --list)")
        return 4

    if not _is_known(args.method):
        err(f"warning: {args.method!r} not in KNOWN_METHODS — attempting anyway")

    if args.args:
        try:
            call_args = json.loads(args.args)
        except json.JSONDecodeError as e:
            err(f"--args: invalid JSON: {e}")
            return 4
        if not isinstance(call_args, list):
            err("--args must be a JSON array")
            return 4
    else:
        call_args = []

    result = call(args.method, call_args)
    out(result, session=session)
    return 0


# ---------- module exports ----------

HANDLERS = {
    "datalog": cmd_datalog,
    "q": cmd_q,
    "custom-query": cmd_custom_query,
    "raw": cmd_raw,
}


def register(subparsers) -> None:
    """Attach raw-family subparsers. Coordinator calls this during argparse setup."""
    p = subparsers.add_parser("datalog", help="Raw Datalog query")
    p.add_argument("query", help="Datalog expression, e.g. [:find ?b :where [?b :block/uuid _]]")
    p.set_defaults(func=cmd_datalog)

    p = subparsers.add_parser("q", help="Logseq simplified query syntax")
    p.add_argument("expr", help='e.g. (page "Reading List"), (tag "book"), (task TODO)')
    p.set_defaults(func=cmd_q)

    p = subparsers.add_parser("custom-query", help="Logseq custom-query EDN")
    p.add_argument("edn", help="EDN custom-query string")
    p.set_defaults(func=cmd_custom_query)

    p = subparsers.add_parser("raw", help="Generic method invocation or --list")
    p.add_argument("method", nargs="?", help="e.g. logseq.Editor.getPage or get_page")
    p.add_argument("--args", type=str, help="JSON array of arguments")
    p.add_argument("--list", action="store_true", help="Print all KNOWN_METHODS")
    p.add_argument("--grep", type=str, help="Filter --list by regex (case-insensitive)")
    p.set_defaults(func=cmd_raw)


# ---------- self-test ----------

if __name__ == "__main__":
    import argparse as _ap
    from _logseq_common import load_session, set_session

    ns = _ap.Namespace(
        token="cc", host="127.0.0.1", port=12315, graph=None,
        fmt="json", limit=None, offset=None, yes=False, dry_run=False,
        verbose=False, quiet=False, uuids_only=False,
    )
    s = load_session(ns)
    set_session(s)

    print("-- datalog count --")
    cmd_datalog(_ap.Namespace(query='[:find (count ?b) . :where [?b :block/uuid _]]'), s)
    print("-- q (page Reading List) --")
    cmd_q(_ap.Namespace(expr='(page "Reading List")'), s)
    print("-- raw --list --grep block --")
    cmd_raw(_ap.Namespace(list=True, grep="block", method=None, args=None), s)
    print("-- raw get_app_info --")
    cmd_raw(_ap.Namespace(list=False, grep=None, method="get_app_info", args=None), s)
    print("-- raw dotted form logseq.App.getCurrentGraph --")
    cmd_raw(_ap.Namespace(list=False, grep=None,
                          method="logseq.App.getCurrentGraph", args=None), s)
    print("-- raw unknown method (should warn) --")
    try:
        cmd_raw(_ap.Namespace(list=False, grep=None,
                              method="totally_made_up_method", args=None), s)
    except Exception as e:
        print(f"(expected) error: {type(e).__name__}: {e}")
    print("All raw.py self-tests done.")
