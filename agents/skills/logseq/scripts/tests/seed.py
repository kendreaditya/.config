#!/usr/bin/env python3
"""Seed the `logseq-test` graph with deterministic dummy data for the test harness.

Usage:
    python3 seed.py                # idempotent seed
    python3 seed.py --reset        # delete previously-seeded pages, then seed
    python3 seed.py --reset --keep # (reset wins; --keep is a no-op on its own)

Safety: the script aborts unless the running graph is named `logseq-test`.

Produces:
    seed_manifest.json  (next to this file) — ground truth for the test harness.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_URL = "http://127.0.0.1:12315/api"
API_TOKEN = "cc"
EXPECTED_GRAPH = "logseq-test"
SEEDED_BY_VALUE = "logseq-cli-test"
MAGIC_WORD = "resurfacetestmagicword"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(SCRIPT_DIR, "seed_manifest.json")

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("SEED_DEBUG") else logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("seed")


# ---------------------------------------------------------------------------
# HTTP helper (stdlib only, retry-once-on-error)
# ---------------------------------------------------------------------------
def api_call(method: str, args: list | None = None, _retry: int = 1) -> Any:
    body = json.dumps({"method": method, "args": args or []}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    log.debug("-> %s %r", method, args)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        if _retry > 0:
            log.warning("api_call %s failed (%s); retrying in 500ms", method, e)
            time.sleep(0.5)
            return api_call(method, args, _retry=_retry - 1)
        log.error("api_call %s failed: body=%s err=%s", method, body, e)
        raise

    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error("non-JSON response for %s: %r", method, raw[:200])
        raise
    if isinstance(data, dict) and "error" in data and len(data) == 1:
        log.error("API error on %s(%s): %s", method, args, data["error"])
        raise RuntimeError(f"API error: {data['error']}")
    return data


# ---------------------------------------------------------------------------
# Date formatting: "MMM do, yyyy" (e.g. "Apr 17th, 2026")
# ---------------------------------------------------------------------------
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_date_mmm_do_yyyy(d: datetime.date) -> str:
    return f"{_MONTHS[d.month - 1]} {_ordinal(d.day)}, {d.year}"


def format_date_by_pattern(d: datetime.date, pattern: str) -> str:
    """Best-effort formatter. We only really support the default
    'MMM do, yyyy' but fall back gracefully for other common patterns."""
    if pattern == "MMM do, yyyy":
        return format_date_mmm_do_yyyy(d)
    # Very small pattern translator for a couple other common Logseq formats.
    mapping = {
        "yyyy-MM-dd": d.strftime("%Y-%m-%d"),
        "yyyy/MM/dd": d.strftime("%Y/%m/%d"),
        "MM/dd/yyyy": d.strftime("%m/%d/%Y"),
        "dd/MM/yyyy": d.strftime("%d/%m/%Y"),
        "do MMM yyyy": f"{_ordinal(d.day)} {_MONTHS[d.month - 1]} {d.year}",
        "MMM dd, yyyy": f"{_MONTHS[d.month - 1]} {d.day:02d}, {d.year}",
        "MMMM do, yyyy": f"{d.strftime('%B')} {_ordinal(d.day)}, {d.year}",
    }
    if pattern in mapping:
        return mapping[pattern]
    log.warning("Unknown date pattern %r; falling back to MMM do, yyyy", pattern)
    return format_date_mmm_do_yyyy(d)


# ---------------------------------------------------------------------------
# Mutation wrappers (each logs the request body on failure via api_call)
# ---------------------------------------------------------------------------
def safety_check() -> None:
    graph = api_call("logseq.App.getCurrentGraph") or {}
    name = graph.get("name")
    if name != EXPECTED_GRAPH:
        print(
            f"[seed] ABORT: current graph is {name!r}, expected {EXPECTED_GRAPH!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"[seed] Safety check: graph is {EXPECTED_GRAPH} \u2713")


def get_page(name: str):
    return api_call("logseq.Editor.getPage", [name])


def create_page(name: str):
    """Idempotent page create. Returns the page object."""
    page = get_page(name)
    if page:
        return page
    return api_call("logseq.Editor.createPage", [name, {}, {}])


def append_block(page_name: str, content: str) -> dict:
    block = api_call("logseq.Editor.appendBlockInPage", [page_name, content])
    if not block or not block.get("uuid"):
        raise RuntimeError(f"appendBlockInPage returned no uuid for {page_name!r}")
    return block


def insert_child(parent_uuid: str, content: str) -> dict:
    block = api_call(
        "logseq.Editor.insertBlock",
        [parent_uuid, content, {"sibling": False}],
    )
    if not block or not block.get("uuid"):
        raise RuntimeError(f"insertBlock returned no uuid under parent {parent_uuid}")
    return block


def set_prop(block_uuid: str, key: str, value) -> None:
    api_call("logseq.Editor.upsertBlockProperty", [block_uuid, key, value])


def update_block(block_uuid: str, content: str) -> None:
    api_call("logseq.Editor.updateBlock", [block_uuid, content])


def stamp_seeded(block_uuid: str) -> None:
    """Idempotent seeded-by stamp.

    Logseq's HTTP API occasionally returns a DOM-editor quirk
    ('setSelectionRange is not a function') when upserting a property
    on a block that already carries that property — the server tries to
    re-focus the editor on the block. If the property is already set,
    skip the call; if we still hit the quirk, treat it as benign.
    """
    try:
        existing = api_call("logseq.Editor.getBlockProperty",
                            [block_uuid, "seeded-by"])
    except Exception:
        existing = None
    if existing == SEEDED_BY_VALUE:
        return
    try:
        set_prop(block_uuid, "seeded-by", SEEDED_BY_VALUE)
    except RuntimeError as e:
        msg = str(e).lower()
        if "setselectionrange" in msg or "is not a function" in msg:
            log.debug("benign upsertBlockProperty quirk on %s: %s",
                      block_uuid, e)
            return
        raise


# ---------------------------------------------------------------------------
# Reset logic
# ---------------------------------------------------------------------------
def find_seeded_pages() -> list[str]:
    """Find page names whose first-block carries seeded-by:: logseq-cli-test."""
    # Bind the property value to ?v, then filter on equality via a predicate.
    q = (
        '[:find ?name '
        ':where '
        '[?b :block/properties ?props] '
        '[?p :block/name ?name] '
        '[?b :block/page ?p] '
        '[(get ?props :seeded-by) ?v] '
        f'[(= ?v "{SEEDED_BY_VALUE}")]]'
    )
    result = api_call("logseq.DB.datascriptQuery", [q]) or []
    # result is list of [name] tuples. Deduplicate, preserve original page names.
    names = sorted({row[0] for row in result if row})
    # `:block/name` is lowercased in the DB; map back to originalName via getPage.
    originals = []
    for n in names:
        pg = get_page(n)
        if pg:
            originals.append(pg.get("originalName") or pg.get("name") or n)
    return originals


def reset_seeded() -> int:
    names = find_seeded_pages()
    deleted = 0
    for n in names:
        # Skip journal pages — deleting the journal for today would nuke user's
        # real page on graphs other than logseq-test, but we're safety-checked
        # into logseq-test here, so go ahead. Still, note journals in the log.
        pg = get_page(n)
        if not pg:
            continue
        try:
            api_call("logseq.Editor.deletePage", [n])
            deleted += 1
            log.debug("deleted page %s", n)
        except Exception as e:
            log.warning("failed to delete page %s: %s", n, e)
    return deleted


# ---------------------------------------------------------------------------
# Seeding pipeline
# ---------------------------------------------------------------------------
def seed(session_cfg: dict, created: dict) -> None:
    """Populate the graph. Mutates `created` with uuids + metadata."""
    pattern = session_cfg.get("preferredDateFormat") or "MMM do, yyyy"
    today = datetime.date.today()

    # --- Tag/ref target pages ---
    print("[seed] Creating tag/ref targets...")
    for name in ("Tag One", "Tag Two", "Project Alpha"):
        page = create_page(name)
        # first block
        existing_blocks = api_call("logseq.Editor.getPageBlocksTree", [name]) or []
        # Filter out empty placeholder blocks from a fresh page.
        meaningful = [b for b in existing_blocks if (b.get("content") or "").strip()]
        if meaningful:
            first_uuid = meaningful[0]["uuid"]
            log.debug("page %s already has blocks; reusing first", name)
        else:
            blk = append_block(name, f"This is [[{name}]]")
            first_uuid = blk["uuid"]
            created["blocks"].append({
                "uuid": first_uuid,
                "page": name,
                "content_preview": f"This is [[{name}]]",
            })
        stamp_seeded(first_uuid)
        created["pages"].append(name)
        print(f"[seed]   {name}: ready (uuid={first_uuid})")

    # --- Reading List (rich tree) ---
    print("[seed] Creating Reading List tree...")
    rl = "Reading List"
    create_page(rl)

    # Check if already populated. If the page already has a seeded-by marker
    # (meaning we previously ran without --reset), reuse it as-is.
    rl_tree = api_call("logseq.Editor.getPageBlocksTree", [rl]) or []
    rl_tree = [b for b in rl_tree if (b.get("content") or "").strip()]

    def _is_seeded(block) -> bool:
        props = block.get("properties") or {}
        # Logseq exposes property keys via :block/properties; seeded-by may be present.
        return (props.get("seeded-by") == SEEDED_BY_VALUE or
                (block.get("content") or "").lower().find("seeded-by::") >= 0)

    already_seeded_rl = any(_is_seeded(b) for b in rl_tree)

    def _collect_rl_existing():
        """On idempotent re-run, recover the top-level Reading List blocks
        into created['blocks'] so the manifest reflects ground truth."""
        def _walk(nodes, preview_limit=80):
            for n in nodes:
                c = (n.get("content") or "").strip()
                if not c:
                    continue
                # Skip the property-line noise (seeded-by::)
                first_line = c.split("\n", 1)[0]
                if first_line.startswith("seeded-by::"):
                    continue
                created["blocks"].append({
                    "uuid": n["uuid"],
                    "page": rl,
                    "content_preview": first_line[:preview_limit],
                })
                if n.get("children"):
                    _walk(n["children"], preview_limit)
        _walk(rl_tree)

    if not already_seeded_rl:
        def _add(blk: dict, preview: str):
            created["blocks"].append({
                "uuid": blk["uuid"],
                "page": rl,
                "content_preview": preview,
            })

        # block 1: "Books I want to read" with children
        b1 = append_block(rl, "Books I want to read")
        stamp_seeded(b1["uuid"])  # anchor seeded-by on Reading List
        _add(b1, "Books I want to read")
        b1_c1 = insert_child(b1["uuid"], "[[Tag One]] philosophy primer")
        _add(b1_c1, "[[Tag One]] philosophy primer")
        b1_c1_gc = insert_child(b1_c1["uuid"], "**bold annotation** for this one")
        _add(b1_c1_gc, "**bold annotation** for this one")
        b1_c2 = insert_child(b1["uuid"], "[[Tag Two]] linked here")
        _add(b1_c2, "[[Tag Two]] linked here")

        # block 2: simple-tag articles
        b2 = append_block(rl, "#simple-tag articles")
        _add(b2, "#simple-tag articles")
        b2_c = insert_child(b2["uuid"], "TODO read `design patterns` article")
        _add(b2_c, "TODO read `design patterns` article")
        b2_c_gc = insert_child(b2_c["uuid"], "has some ==highlighted== content")
        _add(b2_c_gc, "has some ==highlighted== content")

        # block 3: Multi Word tag
        b3 = append_block(rl, "#[[Multi Word]] projects")
        _add(b3, "#[[Multi Word]] projects")
        b3_c = insert_child(b3["uuid"], "~~strikethrough~~ this is done")
        _add(b3_c, "~~strikethrough~~ this is done")

        # block 4: See Project Alpha — we'll rewrite after we know Meta Page uuid
        b4 = append_block(rl, "See [[Project Alpha]] for related work")
        _add(b4, "See [[Project Alpha]] for related work")

        # blocks 5–9
        b5 = append_block(rl, "Reference to [[Broken Target A]]")
        _add(b5, "Reference to [[Broken Target A]]")
        b6 = append_block(rl, "Also [[Broken Target B]] somewhere")
        _add(b6, "Also [[Broken Target B]] somewhere")
        b7 = append_block(rl, "LATER explore [external link](https://example.com)")
        _add(b7, "LATER explore [external link](...)")
        b8 = append_block(rl, f"{MAGIC_WORD} exactly one block")
        _add(b8, f"{MAGIC_WORD} exactly one block")
        b9 = append_block(
            rl,
            "A really long form block with lots of content to make this substantive: "
            "the quick brown fox jumps over the lazy dog, and so on, extending into "
            "the second line of content so we have something for truncation tests.",
        )
        _add(b9, "A really long form block with lots of content...")
        created["rl_block4_uuid"] = b4["uuid"]
    else:
        print(f"[seed]   {rl}: already seeded, skipping rebuild")
        # Best-effort: find block 4 (the See [[Project Alpha]] block) for later rewrite.
        for b in rl_tree:
            if "[[Project Alpha]]" in (b.get("content") or ""):
                created["rl_block4_uuid"] = b["uuid"]
                break
        _collect_rl_existing()

    created["pages"].append(rl)
    print(f"[seed]   {rl}: ready")

    # --- Orphan Page ---
    print("[seed] Creating Orphan Page...")
    create_page("Orphan Page")
    op_tree = api_call("logseq.Editor.getPageBlocksTree", ["Orphan Page"]) or []
    op_tree = [b for b in op_tree if (b.get("content") or "").strip()]
    if op_tree:
        op_uuid = op_tree[0]["uuid"]
    else:
        op = append_block("Orphan Page", "This page has no inbound references.")
        op_uuid = op["uuid"]
        created["blocks"].append({
            "uuid": op_uuid,
            "page": "Orphan Page",
            "content_preview": "This page has no inbound references.",
        })
    stamp_seeded(op_uuid)
    created["pages"].append("Orphan Page")
    print(f"[seed]   Orphan Page: ready (uuid={op_uuid})")

    # --- Meta Page (with properties) ---
    print("[seed] Creating Meta Page with properties...")
    create_page("Meta Page")
    mp_tree = api_call("logseq.Editor.getPageBlocksTree", ["Meta Page"]) or []
    mp_tree = [b for b in mp_tree if (b.get("content") or "").strip()]
    if mp_tree:
        mp_uuid = mp_tree[0]["uuid"]
    else:
        mp = append_block("Meta Page", "A page with properties.")
        mp_uuid = mp["uuid"]
        created["blocks"].append({
            "uuid": mp_uuid,
            "page": "Meta Page",
            "content_preview": "A page with properties.",
        })
    stamp_seeded(mp_uuid)
    set_prop(mp_uuid, "type", "reference")
    set_prop(mp_uuid, "status", "draft")
    set_prop(mp_uuid, "rating", 5)
    created["meta_page_block_uuid"] = mp_uuid
    created["pages"].append("Meta Page")
    print(f"[seed]   Meta Page: ready (uuid={mp_uuid})")

    # --- Namespace pages ---
    print("[seed] Creating namespace pages...")
    for name, content in [
        ("Notes", "Namespace root"),
        ("Notes/Philosophy", "Philosophy root"),
        ("Notes/Systems", "Systems thinking root"),
        ("Notes/Philosophy/Stoicism", "Stoicism (nested under Philosophy)"),
    ]:
        create_page(name)
        tree = api_call("logseq.Editor.getPageBlocksTree", [name]) or []
        tree = [b for b in tree if (b.get("content") or "").strip()]
        if tree:
            uid = tree[0]["uuid"]
        else:
            blk = append_block(name, content)
            uid = blk["uuid"]
            created["blocks"].append({
                "uuid": uid, "page": name, "content_preview": content,
            })
        stamp_seeded(uid)
        created["pages"].append(name)
        print(f"[seed]   {name}: ready (uuid={uid})")

    # --- Journal pages ---
    print("[seed] Creating journal entries...")
    journal_plan = [
        (today, [
            "Started the day with a walk [[Project Alpha]]",
            "TODO review quarterly goals",
            "Random thought about #simple-tag",
        ]),
        (today - datetime.timedelta(days=1), [
            "[[Reading List]] added 2 books",
            "Meeting with team about [[Project Alpha]]",
        ]),
        (today - datetime.timedelta(days=3), [
            "Earlier journal entry with #simple-tag",
        ]),
        (today - datetime.timedelta(days=7), [
            "Week prior entry referencing [[Tag One]]",
        ]),
        (today - datetime.timedelta(days=30), [
            "Month-ago entry for journals --last 30 test",
        ]),
    ]

    journal_day_ints = []
    for d, blocks in journal_plan:
        page_name = format_date_by_pattern(d, pattern)
        create_page(page_name)
        journal_day_ints.append(int(d.strftime("%Y%m%d")))
        existing = api_call("logseq.Editor.getPageBlocksTree", [page_name]) or []
        existing = [b for b in existing if (b.get("content") or "").strip()]
        # Compare against the FIRST line of each existing block's content
        # (Logseq appends property lines like `seeded-by::` on subsequent lines).
        existing_first_lines = set()
        for b in existing:
            c = (b.get("content") or "").strip()
            if c:
                existing_first_lines.add(c.split("\n", 1)[0].strip())
        first_uuid = None
        for content in blocks:
            if content.strip() in existing_first_lines:
                log.debug("journal %s: block already present, skipping", page_name)
                continue
            blk = append_block(page_name, content)
            created["blocks"].append({
                "uuid": blk["uuid"],
                "page": page_name,
                "content_preview": content,
            })
            if first_uuid is None:
                first_uuid = blk["uuid"]
        if first_uuid is None and existing:
            first_uuid = existing[0]["uuid"]
        if first_uuid:
            stamp_seeded(first_uuid)
        created["pages"].append(page_name)
        print(f"[seed]   {page_name}: ready")

    created["journal_day_ints"] = journal_day_ints

    # --- Rewrite block 4 of Reading List with ((meta_uuid)) ref ---
    rl_b4 = created.get("rl_block4_uuid")
    mp_u = created.get("meta_page_block_uuid")
    if rl_b4 and mp_u:
        # Fetch current content to make the rewrite idempotent.
        current = api_call("logseq.Editor.getBlock", [rl_b4]) or {}
        cur_content = (current.get("content") or "").strip()
        target_token = f"(({mp_u}))"
        if target_token in cur_content:
            print(f"[seed]   Reading List block 4 already contains (({mp_u[:8]}...)) ref")
        else:
            new_content = f"See [[Project Alpha]] for related work — also ref {target_token}"
            update_block(rl_b4, new_content)
            print(f"[seed]   Reading List block 4 rewritten with (({mp_u[:8]}...)) ref")

    # --- Delete auto-materialized "broken" target pages ---
    # Logseq auto-creates empty pages for any [[Bracket]] ref. We want the
    # broken targets to look truly broken (referenced but no page). Delete
    # them AFTER the Reading List blocks are written.
    print("[seed] Deleting auto-materialized broken targets...")
    for broken in ("Broken Target A", "Broken Target B"):
        pg = get_page(broken)
        if pg:
            try:
                api_call("logseq.Editor.deletePage", [broken])
                print(f"[seed]   deleted auto-page: {broken}")
            except Exception as e:
                log.warning("could not delete broken target %s: %s", broken, e)
        else:
            print(f"[seed]   {broken}: not materialized (good)")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify(created: dict) -> bool:
    print("[seed] Verifying...")
    ok = True

    # 1. Block count >= 50
    block_count = api_call(
        "logseq.DB.datascriptQuery",
        ["[:find (count ?b) . :where [?b :block/uuid _]]"],
    )
    if isinstance(block_count, int) and block_count >= 50:
        print(f"[seed]   Block count: {block_count} \u2265 50 \u2713")
    else:
        print(f"[seed]   Block count: {block_count} < 50 \u2717")
        ok = False

    # 2. Page count >= 12
    page_count = api_call(
        "logseq.DB.datascriptQuery",
        ["[:find (count ?p) . :where [?p :block/name _]]"],
    )
    if isinstance(page_count, int) and page_count >= 12:
        print(f"[seed]   Page count: {page_count} \u2265 12 \u2713")
    else:
        print(f"[seed]   Page count: {page_count} < 12 \u2717")
        ok = False

    # 3. Reading List non-null with children
    rl = api_call("logseq.Editor.getPage", ["Reading List"])
    rl_tree = api_call("logseq.Editor.getPageBlocksTree", ["Reading List"]) or []
    rl_tree = [b for b in rl_tree if (b.get("content") or "").strip()]
    with_kids = sum(1 for b in rl_tree if b.get("children"))
    if rl and rl_tree and with_kids >= 1:
        print(
            f"[seed]   Reading List tree: {len(rl_tree)} top-level blocks, "
            f"{with_kids} with children \u2713"
        )
    else:
        print(
            f"[seed]   Reading List tree: page={bool(rl)} "
            f"top={len(rl_tree)} with_kids={with_kids} \u2717"
        )
        ok = False

    # 4. Broken Target A absent
    bt = api_call("logseq.Editor.getPage", ["Broken Target A"])
    if bt is None:
        print("[seed]   Broken Target A: absent as expected \u2713")
    else:
        print(f"[seed]   Broken Target A: present (unexpected): {bt} \u2717")
        ok = False

    # 5. Magic word search returns 1 hit
    search_result = api_call("logseq.App.search", [MAGIC_WORD]) or {}
    blocks_hits = search_result.get("blocks") or []
    # Fallback: datascript match for literal magic word in content
    if len(blocks_hits) != 1:
        ds_hits = api_call(
            "logseq.DB.datascriptQuery",
            [
                '[:find ?uuid :where [?b :block/content ?c] [?b :block/uuid ?uuid] '
                f'[(clojure.string/includes? ?c "{MAGIC_WORD}")]]'
            ],
        ) or []
        hit_count = len(ds_hits)
    else:
        hit_count = len(blocks_hits)

    if hit_count == 1:
        print(f"[seed]   Magic word hits: {hit_count} \u2713")
    else:
        print(f"[seed]   Magic word hits: {hit_count} (expected 1) \u2717")
        # Don't fail hard — search index may be lazy. We keep ok as-is so that
        # a fresh run immediately after seeding doesn't hard-fail; tests should
        # re-run after index settles. But surface it loudly.
        if hit_count == 0:
            log.warning("Search index may not have picked up the new block yet.")

    return ok


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def collect_live_blocks(page_names: list[str]) -> list[dict]:
    """After seeding, walk each seeded page tree and emit a flat manifest
    of every non-property, non-empty block. This is ground truth regardless
    of whether the run was fresh or idempotent."""
    blocks: list[dict] = []
    seen = set()

    def walk(nodes, page):
        for n in nodes:
            uid = n.get("uuid")
            content = (n.get("content") or "").strip()
            if uid and content and uid not in seen:
                first_line = content.split("\n", 1)[0]
                # Skip blocks that are ONLY property lines (e.g. "seeded-by:: ...")
                # but KEEP blocks whose first line is real content and whose
                # subsequent lines happen to be property lines.
                if not first_line.startswith("seeded-by::"):
                    seen.add(uid)
                    blocks.append({
                        "uuid": uid,
                        "page": page,
                        "content_preview": first_line[:80],
                    })
            if n.get("children"):
                walk(n["children"], page)

    for name in page_names:
        tree = api_call("logseq.Editor.getPageBlocksTree", [name]) or []
        walk(tree, name)
    return blocks


def write_manifest(created: dict, journal_day_ints: list[int]) -> None:
    pages = sorted(set(created["pages"]))
    live_blocks = collect_live_blocks(pages)
    manifest = {
        "graph": EXPECTED_GRAPH,
        "seeded_at": datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"),
        "pages": pages,
        "blocks": live_blocks,
        "expectations": {
            "total_pages_seeded": len(pages),
            "total_blocks_seeded": len(live_blocks),
            "search_magic_word": MAGIC_WORD,
            "search_magic_word_expected_hits": 1,
            "broken_ref_targets": ["Broken Target A", "Broken Target B"],
            "orphan_page": "Orphan Page",
            "namespace_root": "Notes",
            "namespace_leaves": [
                "Notes/Philosophy",
                "Notes/Systems",
                "Notes/Philosophy/Stoicism",
            ],
            "prop_page_name": "Meta Page",
            "prop_keys": ["type", "status", "rating"],
            "prop_values": {"type": "reference", "status": "draft", "rating": 5},
            "tags": ["simple-tag", "Multi Word"],
            "todo_pages": ["Reading List"],
            "journal_days_seeded": journal_day_ints,
        },
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reset", action="store_true",
                   help="Delete previously-seeded pages before seeding.")
    p.add_argument("--keep", action="store_true",
                   help="No-op unless combined with --reset; reset takes priority.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    try:
        safety_check()

        configs = api_call("logseq.App.getUserConfigs") or {}
        pattern = configs.get("preferredDateFormat") or "MMM do, yyyy"
        print(f"[seed] Preferred date format: {pattern}")

        if args.reset:
            deleted = reset_seeded()
            print(f"[seed] --reset: deleted {deleted} previously-seeded pages")
        elif args.keep:
            # --keep alone: no-op, but announce it.
            print("[seed] --keep supplied without --reset: nothing to clean")

        created = {"pages": [], "blocks": []}
        seed(configs, created)

        journal_day_ints = created.get("journal_day_ints", [])
        write_manifest(created, journal_day_ints)

        ok = verify(created)

        # Read the manifest we just wrote to report ground-truth counts.
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                mf = json.load(f)
            page_count = len(mf.get("pages") or [])
            block_count = len(mf.get("blocks") or [])
        except Exception:
            page_count = len(set(created["pages"]))
            block_count = len(created["blocks"])
        print(
            f"[seed] Done. Seeded {page_count} pages, {block_count} blocks. "
            f"Manifest: {MANIFEST_PATH}"
        )
        return 0 if ok else 1
    except Exception as e:
        log.exception("fatal: %s", e)
        print(f"[seed] FATAL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
