#!/usr/bin/env bash
# Main test harness. Runs every cases/*.sh file in lexical order,
# aggregates pass/fail counts from assert.sh, and exits non-zero on failure.
#
# Pre-flight:
#   1. logseq CLI is on PATH
#   2. seed_manifest.json exists (instructs user to run seed.py otherwise)
#   3. Current running graph is `logseq-test` (safety: tests mutate data)
#
# Env overrides:
#   LOGSEQ_API_TOKEN (default: cc)
#   LOGSEQ_HOST      (default: 127.0.0.1)
#   LOGSEQ_PORT      (default: 12315)
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export SCRIPT_DIR

# Default env
export LOGSEQ_API_TOKEN="${LOGSEQ_API_TOKEN:-cc}"
export LOGSEQ_HOST="${LOGSEQ_HOST:-127.0.0.1}"
export LOGSEQ_PORT="${LOGSEQ_PORT:-12315}"

# Verify prerequisites
if ! command -v logseq >/dev/null 2>&1; then
  echo "FATAL: \`logseq\` not on PATH. Run \`logseq doctor --fix\` first." >&2
  exit 2
fi

if [ ! -f "$SCRIPT_DIR/seed_manifest.json" ]; then
  echo "FATAL: seed_manifest.json not found at $SCRIPT_DIR/seed_manifest.json" >&2
  echo "       Run: python3 $SCRIPT_DIR/seed.py" >&2
  exit 2
fi

# Safety: ensure we're on logseq-test graph. Tests in 05_writes.sh mutate.
graph=$(logseq graph --format json 2>/dev/null | python3 -c "import json,sys
try:
  d=json.load(sys.stdin)
  print(d.get('name','') if isinstance(d, dict) else '')
except Exception:
  print('')" 2>/dev/null || true)

if [ "$graph" != "logseq-test" ]; then
  echo "FATAL: current graph is '$graph', expected 'logseq-test'." >&2
  echo "       Switch inside Logseq first (Open another graph -> logseq-test)." >&2
  exit 2
fi

# Spot-check that seed ran: a few known seeded pages exist.
# If Reading List is missing, tests will cascade-fail; surface this early.
if ! logseq page "Reading List" --format json >/dev/null 2>&1; then
  echo "WARNING: 'Reading List' page not found; graph may not be seeded." >&2
  echo "         Run: python3 $SCRIPT_DIR/seed.py" >&2
  # Continue anyway — the test cases will log real failures.
fi

echo "==========================================="
echo "  logseq CLI test harness"
echo "  graph:  $graph"
echo "  host:   $LOGSEQ_HOST:$LOGSEQ_PORT"
echo "  token:  ***"
echo "==========================================="

# shellcheck disable=SC1091
source ./assert.sh

export LOGSEQ_TEST_PASS=0
export LOGSEQ_TEST_FAIL=0
export LOGSEQ_TEST_FAILURES=""

for case_file in cases/*.sh; do
  [ -f "$case_file" ] || continue
  echo ""
  echo "--- $(basename "$case_file") ---"
  # shellcheck disable=SC1090
  source "$case_file"
done

echo ""
echo "==========================================="
total=$((LOGSEQ_TEST_PASS + LOGSEQ_TEST_FAIL))
if [ "$LOGSEQ_TEST_FAIL" -eq 0 ]; then
  printf "\033[32m  %d / %d passed\033[0m\n" "$LOGSEQ_TEST_PASS" "$total"
  exit 0
else
  printf "\033[31m  %d / %d passed — %d failed\033[0m\n" "$LOGSEQ_TEST_PASS" "$total" "$LOGSEQ_TEST_FAIL"
  printf "\nFailures:\n%b" "$LOGSEQ_TEST_FAILURES"
  exit 1
fi
