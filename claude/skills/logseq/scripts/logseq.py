#!/usr/bin/env python3
"""logseq — HTTP-API CLI for querying and mutating a running Logseq graph.

Entry point. Wires argparse + subparsers from each commands/*.py module,
loads the session once, dispatches to the handler, and classifies errors.

See `logseq <command> --help` or read SKILL.md.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _logseq_common import (  # noqa: E402
    LogseqError,
    classify_error,
    err,
    load_session,
    set_session,
)
from commands import meta, raw, reads, stats, writes  # noqa: E402


CLI_VERSION = "0.1.0"


def _add_global_flags(parser: argparse.ArgumentParser) -> None:
    """Attach global flags to any parser/subparser.

    Called both on the main parser and recursively on every subparser so that
    users can place flags before OR after the subcommand (e.g. both
    `logseq --format json graph` and `logseq graph --format json` work).
    """
    g = parser.add_argument_group("global")
    g.add_argument("--token", help="API token (overrides env + config)")
    g.add_argument("--host", help="API host (default 127.0.0.1)")
    g.add_argument("--port", type=int, help="API port (default 12315)")
    g.add_argument("--graph", help="Soft-pin a graph name")
    g.add_argument(
        "--format", dest="fmt",
        choices=["json", "pretty", "tree", "md", "table", "plain", "uuids"],
        help="Output format (auto-picks based on TTY by default)",
    )
    g.add_argument("--pretty", action="store_const", const="pretty", dest="fmt",
                   help="Shortcut for --format pretty")
    g.add_argument("--uuids-only", action="store_const", const="uuids", dest="fmt",
                   help="Shortcut for --format uuids (one per line)")
    g.add_argument("--limit", type=int, help="Client-side cap on array results")
    g.add_argument("--offset", type=int, help="Client-side offset")
    g.add_argument("--quiet", action="store_true", help="Suppress informational stderr")
    g.add_argument("--verbose", action="store_true", help="Dump POST body + raw response")
    g.add_argument("--yes", "-y", dest="yes", action="store_true",
                   help="Auto-confirm write operations")
    g.add_argument("--dry-run", action="store_true",
                   help="Print the request without sending")


def _inject_globals_everywhere(parser: argparse.ArgumentParser) -> None:
    """Walk the subparser tree and add global flags to every leaf parser."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                try:
                    _add_global_flags(subparser)
                except argparse.ArgumentError:
                    # Already present (nested), skip.
                    pass
                _inject_globals_everywhere(subparser)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logseq",
        description="Logseq HTTP-API CLI. Query pages, blocks, tags, search, and mutate.",
        epilog="Run `logseq <command> --help` for per-subcommand options, or `logseq doctor` to verify setup.",
    )
    _add_global_flags(p)
    p.add_argument("--version", action="version", version=f"logseq-cli {CLI_VERSION}")

    subparsers = p.add_subparsers(dest="command", required=True, metavar="<command>")

    # Fixed registration order — meta first, then reads (most-used), stats, raw, writes.
    meta.register(subparsers)
    reads.register(subparsers)
    stats.register(subparsers)
    raw.register(subparsers)
    writes.register(subparsers)

    # Post-hoc: attach global flags to every subparser so they work on the right of the command too.
    _inject_globals_everywhere(p)

    return p


def _apply_defaults(ns: argparse.Namespace) -> argparse.Namespace:
    """Ensure every global flag field exists on Namespace, defaulting to None/False."""
    for attr, default in (
        ("token", None),
        ("host", None),
        ("port", None),
        ("graph", None),
        ("fmt", None),
        ("limit", None),
        ("offset", None),
        ("quiet", False),
        ("verbose", False),
        ("yes", False),
        ("dry_run", False),
    ):
        if not hasattr(ns, attr):
            setattr(ns, attr, default)
    return ns


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args = _apply_defaults(args)

    # For `init`, do NOT load the session first — init collects the token from
    # the user. All other commands need a live session.
    command = getattr(args, "command", None)
    if command != "init":
        try:
            s = load_session(args)
        except LogseqError as e:
            err(e.message)
            return e.exit_code
        set_session(s)
    else:
        # Create a minimal placeholder session; init will overwrite.
        from _logseq_common import Session  # noqa: E402
        s = Session(token="")
        set_session(s)

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 1

    # Dispatch
    try:
        rc = func(args, s) if "session" in func.__code__.co_varnames or func.__code__.co_argcount >= 2 else func(args)
        return int(rc or 0)
    except LogseqError as e:
        err(e.message)
        return e.exit_code
    except KeyboardInterrupt:
        err("interrupted")
        return 130
    except Exception as e:
        classified = classify_error(e)
        err(f"{classified.kind}: {classified.message}")
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return classified.exit_code


if __name__ == "__main__":
    sys.exit(main())
