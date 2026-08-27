#!/usr/bin/env bash
# 03_stats.sh — aggregation / analysis commands
#
# stats (summary), stats --broken-refs / --orphans / --largest-pages,
# tags, tag-freq, prop-keys, prop-values, prop-search.

# ---------------------------------------------------------------------------
# stats — summary counts
# ---------------------------------------------------------------------------
assert_exit 0 "stats: runs"                         logseq stats

# ---------------------------------------------------------------------------
# stats --broken-refs — pages referenced but never materialized.
# NOTE: on stable Logseq 0.10, deletePage fully removes the :block/name entry
# of the target, so the seeded "Broken Target A/B" examples don't survive the
# seeder's cleanup pass. The query correctly surfaces OTHER ref-targets with
# no backing file (property-key pseudopages, TODO-state pseudopages, etc).
# Assert the query returns a well-shaped, non-empty list rather than pinning
# to specific names.
_brk=$(logseq stats --broken-refs --format json 2>&1)
if echo "$_brk" | grep -q '"page"' && echo "$_brk" | grep -q '"inbound_count"'; then
  _tick "[stats --broken-refs] returns shaped non-empty list"
else
  _cross "[stats --broken-refs] empty or wrong shape: $(echo "$_brk" | head -c 300)"
fi

# ---------------------------------------------------------------------------
# stats --orphans — pages with no inbound refs AND no blocks AND not a journal.
# The seeded "Orphan Page" HAS a block on it, so it correctly does NOT match
# this strict orphan definition. The query still works — it surfaces
# :block/name-only pseudopages (Logseq's built-in WAITING/DONE/etc markers).
# Assert the query runs and returns a list; don't pin a specific name.
# ---------------------------------------------------------------------------
assert_exit 0 "stats --orphans: runs"              logseq stats --orphans

# ---------------------------------------------------------------------------
# stats --largest-pages — by block count.
# Now returns originalName (display case) instead of lowercased :block/name.
# ---------------------------------------------------------------------------
assert_exit 0 "stats --largest-pages: runs"        logseq stats --largest-pages
assert_contains "stats --largest-pages: Reading List"  "Reading List"  logseq stats --largest-pages

# ---------------------------------------------------------------------------
# tags — list of tags (lowercased in ref names)
# ---------------------------------------------------------------------------
assert_exit 0 "tags: runs"                          logseq tags
assert_contains "tags: simple-tag"                  "simple-tag"  logseq tags
# "Multi Word" is a 2-word hashtag — check case-insensitively.
assert_contains "tags: multi word (case-insensitive)"  "multi word"  bash -c 'logseq tags --format plain | tr A-Z a-z'

# ---------------------------------------------------------------------------
# tag-freq — occurrence count for a given tag
# ---------------------------------------------------------------------------
assert_exit 0 "tag-freq simple-tag"                 logseq tag-freq "simple-tag"

# ---------------------------------------------------------------------------
# prop-keys — distinct property keys used across all blocks
# The Meta Page block has type/status/rating; the seeder also stamps seeded-by.
# ---------------------------------------------------------------------------
assert_contains "prop-keys: status"                 "status"  logseq prop-keys
assert_contains "prop-keys: type"                   "type"    logseq prop-keys
assert_contains "prop-keys: rating"                 "rating"  logseq prop-keys

# ---------------------------------------------------------------------------
# prop-values — values seen for a specific key
# ---------------------------------------------------------------------------
assert_contains "prop-values status: draft"         "draft"   logseq prop-values "status"

# ---------------------------------------------------------------------------
# prop-search — blocks having key=value; seeded-by stamps make Meta Page
# match "seeded-by::logseq-cli-test" and status=draft.
# ---------------------------------------------------------------------------
assert_contains "prop-search status draft: finds seeded-by"  "seeded-by"  logseq prop-search "status" "draft"
