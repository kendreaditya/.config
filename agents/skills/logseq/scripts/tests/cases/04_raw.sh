#!/usr/bin/env bash
# 04_raw.sh — raw/datalog/q/custom-query escape hatches.
#
# datalog — run a :find query directly
# q       — run a Logseq query-language expression
# raw     — POST to any API method by name (123 known)
# raw --list — enumerate known methods (for discovery / suggestion logic)

# ---------------------------------------------------------------------------
# datalog — count blocks. Seeder guarantees >= 50.
# Use bash -c because the query expression has brackets that shell interprets.
# assert_gt pulls the first integer out of stdout.
# ---------------------------------------------------------------------------
assert_gt "datalog block count > 50" 50  bash -c 'logseq datalog "[:find (count ?b) . :where [?b :block/uuid _]]" --format plain'

# ---------------------------------------------------------------------------
# q — Logseq query language. Simple (page "...") form should run.
# ---------------------------------------------------------------------------
assert_exit 0 "q (page Reading List)"       logseq q '(page "Reading List")'

# ---------------------------------------------------------------------------
# raw --list — prints known methods
# ---------------------------------------------------------------------------
assert_contains "raw --list: get_page"      "get_page"   logseq raw --list
assert_contains "raw --list --grep block"   "get_block"  logseq raw --list --grep "block"

# ---------------------------------------------------------------------------
# raw <method> — call a method by name. get_app_info returns version info.
# ---------------------------------------------------------------------------
assert_matches "raw get_app_info: version-like"  '[0-9]+\.[0-9]+\.[0-9]+'  logseq raw "get_app_info"

# ---------------------------------------------------------------------------
# raw <method> --args — with a JSON-encoded arg array.
# get_page("Reading List") returns a page object whose :block/name is lowercased.
# ---------------------------------------------------------------------------
assert_contains "raw get_page (Reading List)"    "reading list"  logseq raw "get_page" --args '["Reading List"]'
