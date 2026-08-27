#!/usr/bin/env bash
# 02_reads.sh — read-only commands: today/yesterday/journals/page/pages/block
#                                   props/prop/backlinks/tag/search/recent/
#                                   favorites/templates
#
# Ground-truth comes from seed_manifest.json. See tests/seed.py for how the
# graph was seeded.

# Helper: pull a scalar expectation from seed_manifest.json.
_mf() {
  python3 -c "
import json,sys
d=json.load(open('$SCRIPT_DIR/seed_manifest.json'))
v=d['expectations'].get('$1','')
print(v)
"
}

MAGIC_WORD=$(_mf search_magic_word)
PROP_PAGE=$(_mf prop_page_name)

# ---------------------------------------------------------------------------
# today / yesterday
# ---------------------------------------------------------------------------
assert_exit 0 "today: runs"                        logseq today
# Today's journal has a block containing "quarterly goals" — but only
# visible via --tree (bare `today` returns page metadata only).
assert_contains "today --tree: seeded block present" "quarterly goals" logseq today --tree --format plain
assert_exit 0 "today --tree"                       logseq today --tree

assert_exit 0 "yesterday: runs"                    logseq yesterday

# ---------------------------------------------------------------------------
# journals — list N recent journals or query by date
# ---------------------------------------------------------------------------
assert_exit 0 "journals --last 7"                  logseq journals --last 7
assert_exit 0 "journals --on Apr 17th, 2026"       logseq journals --on "Apr 17th, 2026"

# ---------------------------------------------------------------------------
# page — single-page read, tree, formats
# ---------------------------------------------------------------------------
assert_exit 0 "page Reading List"                  logseq page "Reading List"
# The tree should include the child block carrying the "simple-tag" hashtag.
assert_contains "page Reading List tree: simple-tag" "simple-tag"  bash -c 'logseq page "Reading List" --tree --format plain'

# ---------------------------------------------------------------------------
# pages — full index, namespace filter, filter substring
# ---------------------------------------------------------------------------
assert_exit 0 "pages"                              logseq pages
# Namespace filter: Notes/* should include Stoicism.
assert_contains "pages --namespace Notes"          "Stoicism"   logseq pages --namespace "Notes"
# Free-form filter.
assert_contains "pages --filter Orphan"            "Orphan Page" logseq pages --filter "Orphan"

# ---------------------------------------------------------------------------
# backlinks — use Project Alpha (top-level-block refs, reliably indexed)
# Tag One's inbound refs come from a nested block that doesn't always get
# :block/refs populated when inserted via the HTTP API.
# ---------------------------------------------------------------------------
assert_contains "backlinks Project Alpha: Reading List"  "Reading List"  logseq backlinks "Project Alpha"

# ---------------------------------------------------------------------------
# tag — blocks tagged with #simple-tag
# ---------------------------------------------------------------------------
assert_exit 0 "tag simple-tag"                     logseq tag "simple-tag"

# ---------------------------------------------------------------------------
# search — magic word is a unique hit in Reading List
# ---------------------------------------------------------------------------
if [ -n "$MAGIC_WORD" ]; then
  assert_contains "search magic word"              "$MAGIC_WORD"   logseq search "$MAGIC_WORD"
else
  _cross "search: manifest expectations.search_magic_word missing"
fi

# ---------------------------------------------------------------------------
# recent / favorites / templates — just need to not explode
# ---------------------------------------------------------------------------
assert_exit 0 "recent"                             logseq recent
assert_exit 0 "favorites"                          logseq favorites
assert_exit 0 "templates"                          logseq templates

# ---------------------------------------------------------------------------
# block lookup — pull a uuid from the manifest
# ---------------------------------------------------------------------------
UUID=$(python3 -c "
import json
d=json.load(open('$SCRIPT_DIR/seed_manifest.json'))
blocks=d.get('blocks') or []
print(blocks[0]['uuid'] if blocks else '')
")
if [ -n "$UUID" ]; then
  assert_exit 0 "block <uuid>"                     logseq block "$UUID"
  assert_exit 0 "block <uuid> --children"          logseq block "$UUID" --children
else
  _cross "block: manifest.blocks is empty — cannot pick a uuid"
fi

# ---------------------------------------------------------------------------
# props / prop — read properties on the Meta Page block
# ---------------------------------------------------------------------------
META_UUID=$(python3 -c "
import json
d=json.load(open('$SCRIPT_DIR/seed_manifest.json'))
target='$PROP_PAGE'
for b in d.get('blocks', []):
    if b.get('page') == target:
        print(b['uuid']); break
")
if [ -n "$META_UUID" ]; then
  assert_exit 0 "props <meta uuid>"                logseq props "$META_UUID"
  assert_contains "prop status=draft"              "draft"  logseq prop "$META_UUID" "status"
else
  _cross "could not find '$PROP_PAGE' uuid in manifest — skipping props/prop tests"
fi
