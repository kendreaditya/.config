#!/usr/bin/env bash
# 06_pipes.sh — output-format round-trips for scripting.
#
# --uuids-only  -> one uuid per line, pipable
# --format json -> stable JSON for downstream tools
# --format table -> human-friendly aligned output
# pipe: `search --uuids-only | head -1 | xargs logseq block` round-trip

# ---------------------------------------------------------------------------
# --uuids-only: each line matches a uuid regex.
# ---------------------------------------------------------------------------
count=$(logseq today --uuids-only 2>/dev/null | grep -cE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' || true)
if [ "${count:-0}" -gt 0 ]; then
  _tick "today --uuids-only produces $count uuids"
else
  _cross "today --uuids-only: no uuid-shaped lines emitted"
fi

# ---------------------------------------------------------------------------
# Pipe round-trip: uuid from search, then block lookup.
# ---------------------------------------------------------------------------
MAGIC_WORD=$(python3 -c "
import json
d=json.load(open('$SCRIPT_DIR/seed_manifest.json'))
print(d['expectations'].get('search_magic_word',''))
")

if [ -n "$MAGIC_WORD" ]; then
  magic_uuids=$(logseq search "$MAGIC_WORD" --uuids-only 2>/dev/null | head -1)
  if [ -n "$magic_uuids" ]; then
    assert_exit 0 "pipe: block <uuid from search>"  logseq block "$magic_uuids"
  else
    _cross "pipe: search '$MAGIC_WORD' --uuids-only returned nothing"
  fi
else
  _cross "pipe: manifest expectations.search_magic_word missing"
fi

# ---------------------------------------------------------------------------
# --format json: output must start with `{` or `[`.
# ---------------------------------------------------------------------------
assert_matches "format json: parseable"     '^[[:space:]]*(\{|\[)'   logseq today --format json

# ---------------------------------------------------------------------------
# --format table: should run without error for a tabular data set.
# ---------------------------------------------------------------------------
assert_exit 0 "format table (stats --largest-pages)"  logseq stats --largest-pages --format table
