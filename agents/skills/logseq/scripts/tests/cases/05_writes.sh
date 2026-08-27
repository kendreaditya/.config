#!/usr/bin/env bash
# 05_writes.sh — full CRUD cycle on a scratch page.
#
# Safety discipline:
#   1. Hard-check current graph is logseq-test (even though run_tests.sh did).
#   2. trap EXIT -> delete scratch page regardless of how we exit.
#   3. Exercise --dry-run path FIRST so we verify it doesn't leak.
#   4. Exercise --yes path to actually mutate.

SCRATCH="CLI Test Scratch"

cleanup_scratch() {
  logseq write page-delete "$SCRATCH" --yes >/dev/null 2>&1 || true
}
trap cleanup_scratch EXIT

# ---------------------------------------------------------------------------
# Guard: must be on logseq-test.
# ---------------------------------------------------------------------------
graph=$(logseq graph --format json 2>/dev/null | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print(d.get('name','') if isinstance(d, dict) else '')
except Exception:
  print('')
" 2>/dev/null || true)

if [ "$graph" != "logseq-test" ]; then
  _cross "writes: aborted — not on logseq-test (current: '$graph')"
  return 0 2>/dev/null || exit 0
fi

# Pre-clean in case a previous run left the scratch page behind.
logseq write page-delete "$SCRATCH" --yes >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# page-create --dry-run: should NOT actually create.
# ---------------------------------------------------------------------------
assert_exit 0 "page-create --dry-run"             logseq write page-create "$SCRATCH" --dry-run
# Confirm the page does not exist afterward. `logseq page` should report null
# or a "not found" style message.
_after=$(logseq page "$SCRATCH" --format json 2>&1 || true)
if echo "$_after" | grep -qiE 'null|not found|no such page|does not exist'; then
  _tick "page-create --dry-run did not create"
else
  _cross "page-create --dry-run appears to have leaked a page. Output: $(echo "$_after" | head -c 200)"
fi

# ---------------------------------------------------------------------------
# page-create --yes: actually create the scratch page.
# ---------------------------------------------------------------------------
assert_exit 0 "page-create --yes"                 logseq write page-create "$SCRATCH" --content "first block" --yes
assert_contains "page exists after create"        "$SCRATCH"  logseq page "$SCRATCH"

# ---------------------------------------------------------------------------
# block-append — add a second block to the scratch page.
# ---------------------------------------------------------------------------
assert_exit 0 "block-append"                      logseq write block-append "$SCRATCH" "second block" --yes

# ---------------------------------------------------------------------------
# Get uuid of the first block. `page --tree --format json` returns a tree
# of block objects. Each exposes `uuid`.
# ---------------------------------------------------------------------------
UUID=$(logseq page "$SCRATCH" --tree --format json 2>/dev/null | python3 -c "
import json,sys
try:
  t=json.load(sys.stdin)
except Exception:
  sys.exit(0)
# Be tolerant of wrappers: top-level might be {'blocks': [...]} or a plain list.
if isinstance(t, dict):
  t = t.get('blocks') or t.get('tree') or []
if isinstance(t, list) and t:
  print(t[0].get('uuid',''))
")

if [ -z "$UUID" ]; then
  _cross "could not find uuid of first block on scratch page; aborting remaining writes cycle"
else
  # block-update
  assert_exit 0 "block-update"                    logseq write block-update "$UUID" "updated first block" --yes
  assert_contains "block content updated"         "updated first block"  logseq block "$UUID"

  # prop-set / prop (read) / prop-remove
  assert_exit 0 "prop-set test-key=test-val"      logseq write prop-set "$UUID" "test-key" "test-val" --yes
  assert_contains "prop-set persisted"            "test-val"  logseq prop "$UUID" "test-key"
  assert_exit 0 "prop-remove"                     logseq write prop-remove "$UUID" "test-key" --yes

  # block-remove — dry-run first, then real.
  assert_exit 0 "block-remove --dry-run"          logseq write block-remove "$UUID" --dry-run
  assert_exit 0 "block-remove --yes"              logseq write block-remove "$UUID" --yes
fi

# ---------------------------------------------------------------------------
# Explicit page-delete (trap will also try, but belt-and-suspenders).
# ---------------------------------------------------------------------------
assert_exit 0 "page-delete"                       logseq write page-delete "$SCRATCH" --yes
