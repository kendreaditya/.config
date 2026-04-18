#!/usr/bin/env python3
"""Write/mutate commands for the logseq CLI.

All handlers gate on `--yes` or `confirm()`, and all support `--dry-run`.
Subcommands: page-create, page-delete, page-rename, block-insert, block-append,
block-prepend, block-update, block-remove, block-move, block-batch, prop-set,
prop-remove, template-apply, template-create, template-remove.
Exports: HANDLERS dict + register(subparsers).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from _logseq_common import (  # noqa: E402
    call, out, err, Session, confirm, LogseqError,
)


def _preview(method: str, call_args: list) -> None:
    err(f"[dry-run] POST /api {{method: {method!r}, args: {call_args!r}}}")


def _gate(args, method: str, call_args: list, prompt: str) -> bool:
    """Handle --dry-run and confirm(). Returns True if caller should proceed."""
    if args.dry_run:
        _preview(method, call_args)
        return False
    if not confirm(prompt, args.yes):
        err("aborted")
        return False
    return True


# ---------- page ops ----------

def cmd_write_page_create(args, session: Session) -> int:
    """Create a page. Optional --properties JSON dict and --content first block."""
    props = json.loads(args.properties) if args.properties else {}
    method, call_args = "logseq.Editor.createPage", [args.name, props, {"redirect": False}]
    if args.dry_run:
        _preview(method, call_args)
        if args.content:
            _preview("logseq.Editor.appendBlockInPage", [args.name, args.content])
        return 0
    if not confirm(f"Create page {args.name!r}?", args.yes):
        err("aborted"); return 1
    result = call(method, call_args)
    if args.content:
        call("logseq.Editor.appendBlockInPage", [args.name, args.content])
    out(result, session=session)
    return 0


def cmd_write_page_delete(args, session: Session) -> int:
    """Delete a page by name."""
    m, a = "logseq.Editor.deletePage", [args.name]
    if not _gate(args, m, a, f"Delete page {args.name!r}? This cannot be undone."):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else {"ok": True, "name": args.name}, session=session)
    return 0


def cmd_write_page_rename(args, session: Session) -> int:
    """Rename a page (preserves links)."""
    m, a = "logseq.Editor.renamePage", [args.old, args.new]
    if not _gate(args, m, a, f"Rename page {args.old!r} -> {args.new!r}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else {"ok": True, "old": args.old, "new": args.new},
        session=session)
    return 0


# ---------- block ops ----------

def cmd_write_block_insert(args, session: Session) -> int:
    """Insert a block as a child of a parent or as a sibling of --before/--after."""
    if args.before:
        parent, opts, rel = args.before, {"sibling": True, "before": True}, "before"
    elif args.after:
        parent, opts, rel = args.after, {"sibling": True, "before": False}, "after"
    else:
        parent, opts, rel = args.parent, {"sibling": False}, "under"
    m, a = "logseq.Editor.insertBlock", [parent, args.content, opts]
    if not _gate(args, m, a, f"Insert block {rel} {parent!r}?"):
        return 0 if args.dry_run else 1
    out(call(m, a), session=session)
    return 0


def cmd_write_block_append(args, session: Session) -> int:
    """Append a block to the end of a page."""
    m, a = "logseq.Editor.appendBlockInPage", [args.page, args.content]
    if not _gate(args, m, a, f"Append block to page {args.page!r}?"):
        return 0 if args.dry_run else 1
    out(call(m, a), session=session)
    return 0


def cmd_write_block_prepend(args, session: Session) -> int:
    """Prepend a block to the top of a page."""
    m, a = "logseq.Editor.prependBlockInPage", [args.page, args.content]
    if not _gate(args, m, a, f"Prepend block to page {args.page!r}?"):
        return 0 if args.dry_run else 1
    out(call(m, a), session=session)
    return 0


def cmd_write_block_update(args, session: Session) -> int:
    """Replace a block's content (may contain `key:: value` lines)."""
    m, a = "logseq.Editor.updateBlock", [args.uuid, args.content]
    if not _gate(args, m, a, f"Update block {args.uuid}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else {"ok": True, "uuid": args.uuid}, session=session)
    return 0


def cmd_write_block_remove(args, session: Session) -> int:
    """Remove a block by UUID."""
    m, a = "logseq.Editor.removeBlock", [args.uuid]
    if not _gate(args, m, a, f"Remove block {args.uuid!r}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else {"ok": True, "uuid": args.uuid}, session=session)
    return 0


def cmd_write_block_move(args, session: Session) -> int:
    """Move a block under a new parent."""
    m, a = "logseq.Editor.moveBlock", [args.uuid, args.new_parent]
    if not _gate(args, m, a, f"Move block {args.uuid} under {args.new_parent}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else
        {"ok": True, "uuid": args.uuid, "new_parent": args.new_parent}, session=session)
    return 0


def cmd_write_block_batch(args, session: Session) -> int:
    """Insert a nested batch of blocks under a parent. blocks_json = JSON array."""
    try:
        blocks = json.loads(args.blocks_json)
    except json.JSONDecodeError as e:
        raise LogseqError("args", f"invalid JSON for blocks_json: {e}", 4)
    if not isinstance(blocks, list):
        raise LogseqError("args", "blocks_json must be a JSON array", 4)
    m, a = "logseq.Editor.insertBatchBlock", [args.parent, blocks, {"sibling": False}]
    if not _gate(args, m, a, f"Insert {len(blocks)} block(s) under {args.parent!r}?"):
        return 0 if args.dry_run else 1
    out(call(m, a), session=session)
    return 0


# ---------- property ops ----------

def _benign_dom_error(e: LogseqError) -> bool:
    """The `setSelectionRange is not a function` quirk — write succeeded anyway."""
    return "setSelectionRange" in e.message or "is not a function" in e.message


def cmd_write_prop_set(args, session: Session) -> int:
    """Upsert a block property. Tolerates the setSelectionRange DOM quirk."""
    m, a = "logseq.Editor.upsertBlockProperty", [args.uuid, args.key, args.value]
    if not _gate(args, m, a, f"Set {args.key}={args.value!r} on block {args.uuid}?"):
        return 0 if args.dry_run else 1
    try:
        call(m, a)
    except LogseqError as e:
        if not _benign_dom_error(e):
            raise
    verify = call("logseq.Editor.getBlockProperty", [args.uuid, args.key])
    if str(verify) != str(args.value):
        err(f"WARNING: property set may not have taken effect (read back: {verify!r})")
        return 1
    out({"uuid": args.uuid, "key": args.key, "value": verify}, session=session)
    return 0


def cmd_write_prop_remove(args, session: Session) -> int:
    """Remove a property from a block."""
    m, a = "logseq.Editor.removeBlockProperty", [args.uuid, args.key]
    if not _gate(args, m, a, f"Remove property {args.key!r} from block {args.uuid}?"):
        return 0 if args.dry_run else 1
    try:
        call(m, a)
    except LogseqError as e:
        if not _benign_dom_error(e):
            raise
    out({"ok": True, "uuid": args.uuid, "key": args.key}, session=session)
    return 0


# ---------- template ops ----------

def cmd_write_template_apply(args, session: Session) -> int:
    """Insert a named template at a target block."""
    m, a = "logseq.Editor.insertTemplate", [args.block_uuid, args.name]
    if not _gate(args, m, a, f"Apply template {args.name!r} at block {args.block_uuid}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else
        {"ok": True, "template": args.name, "block": args.block_uuid}, session=session)
    return 0


def cmd_write_template_create(args, session: Session) -> int:
    """Register an existing block as a named template."""
    m, a = "logseq.Editor.createTemplate", [args.block_uuid, args.name]
    if not _gate(args, m, a,
                 f"Create template {args.name!r} from block {args.block_uuid}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else
        {"ok": True, "template": args.name, "block": args.block_uuid}, session=session)
    return 0


def cmd_write_template_remove(args, session: Session) -> int:
    """Remove a named template."""
    m, a = "logseq.Editor.removeTemplate", [args.name]
    if not _gate(args, m, a, f"Remove template {args.name!r}?"):
        return 0 if args.dry_run else 1
    result = call(m, a)
    out(result if result is not None else {"ok": True, "template": args.name},
        session=session)
    return 0


# ---------- argparse registration ----------

HANDLERS = {
    "page-create": cmd_write_page_create,
    "page-delete": cmd_write_page_delete,
    "page-rename": cmd_write_page_rename,
    "block-insert": cmd_write_block_insert,
    "block-append": cmd_write_block_append,
    "block-prepend": cmd_write_block_prepend,
    "block-update": cmd_write_block_update,
    "block-remove": cmd_write_block_remove,
    "block-move": cmd_write_block_move,
    "block-batch": cmd_write_block_batch,
    "prop-set": cmd_write_prop_set,
    "prop-remove": cmd_write_prop_remove,
    "template-apply": cmd_write_template_apply,
    "template-create": cmd_write_template_create,
    "template-remove": cmd_write_template_remove,
}


def register(subparsers) -> None:
    """Attach `write` + nested mutation verbs."""
    write = subparsers.add_parser("write", help="Mutations (require --yes or confirmation)")
    ws = write.add_subparsers(dest="write_subcommand", required=True)

    p = ws.add_parser("page-create", help="Create a page")
    p.add_argument("name"); p.add_argument("--content", type=str, help="Optional first block content")
    p.add_argument("--properties", type=str, help="JSON dict of page properties")
    p.set_defaults(func=cmd_write_page_create)

    p = ws.add_parser("page-delete", help="Delete a page")
    p.add_argument("name"); p.set_defaults(func=cmd_write_page_delete)

    p = ws.add_parser("page-rename", help="Rename a page (preserves links)")
    p.add_argument("old"); p.add_argument("new"); p.set_defaults(func=cmd_write_page_rename)

    p = ws.add_parser("block-insert", help="Insert a block")
    p.add_argument("parent", help="Parent UUID or page name"); p.add_argument("content")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--before", type=str, help="Insert as sibling before this UUID")
    g.add_argument("--after", type=str, help="Insert as sibling after this UUID")
    p.set_defaults(func=cmd_write_block_insert)

    p = ws.add_parser("block-append", help="Append a block to a page")
    p.add_argument("page"); p.add_argument("content"); p.set_defaults(func=cmd_write_block_append)

    p = ws.add_parser("block-prepend", help="Prepend a block to a page")
    p.add_argument("page"); p.add_argument("content"); p.set_defaults(func=cmd_write_block_prepend)

    p = ws.add_parser("block-update", help="Replace a block's content")
    p.add_argument("uuid"); p.add_argument("content"); p.set_defaults(func=cmd_write_block_update)

    p = ws.add_parser("block-remove", help="Remove a block")
    p.add_argument("uuid"); p.set_defaults(func=cmd_write_block_remove)

    p = ws.add_parser("block-move", help="Move a block under a new parent")
    p.add_argument("uuid"); p.add_argument("new_parent")
    p.set_defaults(func=cmd_write_block_move)

    p = ws.add_parser("block-batch", help="Insert a nested batch of blocks")
    p.add_argument("parent")
    p.add_argument("blocks_json",
                   help='JSON array like [{"content":"...","children":[...]}]')
    p.set_defaults(func=cmd_write_block_batch)

    p = ws.add_parser("prop-set", help="Upsert a block property")
    p.add_argument("uuid"); p.add_argument("key"); p.add_argument("value")
    p.set_defaults(func=cmd_write_prop_set)

    p = ws.add_parser("prop-remove", help="Remove a block property")
    p.add_argument("uuid"); p.add_argument("key"); p.set_defaults(func=cmd_write_prop_remove)

    p = ws.add_parser("template-apply", help="Apply a named template to a block")
    p.add_argument("name"); p.add_argument("block_uuid")
    p.set_defaults(func=cmd_write_template_apply)

    p = ws.add_parser("template-create", help="Create a template from an existing block")
    p.add_argument("name"); p.add_argument("block_uuid")
    p.set_defaults(func=cmd_write_template_create)

    p = ws.add_parser("template-remove", help="Remove a named template")
    p.add_argument("name"); p.set_defaults(func=cmd_write_template_remove)


# ---------- self-test ----------

if __name__ == "__main__":
    import argparse as _ap
    from _logseq_common import load_session, set_session

    ns = _ap.Namespace(token="cc", host="127.0.0.1", port=12315, graph=None,
                       fmt="json", limit=None, offset=None, yes=True, dry_run=False,
                       verbose=False, quiet=False, uuids_only=False)
    s = load_session(ns); set_session(s)

    def N(**kw):
        base = {"yes": True, "dry_run": False}
        base.update(kw)
        return _ap.Namespace(**base)

    scratch = "CLI Test Scratch"
    try:
        print("-- page-create --")
        assert cmd_write_page_create(N(name=scratch, content="first block", properties=None), s) == 0

        print("-- block-append --")
        assert cmd_write_block_append(N(page=scratch, content="second block"), s) == 0

        tree = [b for b in (call("logseq.Editor.getPageBlocksTree", [scratch]) or [])
                if (b.get("content") or "").strip()]
        assert tree, "tree empty"
        uuid = tree[0]["uuid"]
        print(f"   first-block uuid: {uuid}")

        print("-- block-update --")
        assert cmd_write_block_update(N(uuid=uuid, content="updated first block"), s) == 0

        print("-- block-prepend --")
        assert cmd_write_block_prepend(N(page=scratch, content="prepended block"), s) == 0

        sibling = [b for b in (call("logseq.Editor.getPageBlocksTree", [scratch]) or [])
                   if (b.get("content") or "").strip()][0]["uuid"]

        print("-- block-insert (child) --")
        assert cmd_write_block_insert(
            N(parent=uuid, content="a child block", before=None, after=None), s) == 0

        print("-- block-insert --after --")
        assert cmd_write_block_insert(
            N(parent=None, content="sibling after block", before=None, after=sibling), s) == 0

        print("-- block-batch --")
        batch = json.dumps([{"content": "batch parent 1",
                             "children": [{"content": "batch child 1a"}]},
                            {"content": "batch parent 2"}])
        assert cmd_write_block_batch(N(parent=uuid, blocks_json=batch), s) == 0

        print("-- prop-set --")
        assert cmd_write_prop_set(N(uuid=uuid, key="test-key", value="test-val"), s) == 0

        print("-- prop-remove --")
        assert cmd_write_prop_remove(N(uuid=uuid, key="test-key"), s) == 0

        print("-- block-move --")
        assert cmd_write_block_move(N(uuid=sibling, new_parent=uuid), s) == 0

        print("-- block-remove (dry-run) --")
        assert cmd_write_block_remove(
            _ap.Namespace(uuid=uuid, yes=False, dry_run=True), s) == 0

        print("-- page-rename --")
        cmd_write_page_rename(N(old=scratch, new=scratch + " (renamed)"), s)
        if call("logseq.Editor.getPage", [scratch + " (renamed)"]):
            scratch = scratch + " (renamed)"
            print(f"   renamed to {scratch!r}")
    finally:
        print("-- page-delete (cleanup) --")
        try:
            cmd_write_page_delete(N(name=scratch), s)
        except Exception as e:
            print(f"   cleanup failed: {e}")

    print("All writes.py self-tests done.")
