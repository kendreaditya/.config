#!/usr/bin/env bash
# Tiny assertion helpers. Source this from every case.
#
# Every helper prints a colored pass/fail line and updates the global
# counters LOGSEQ_TEST_PASS / LOGSEQ_TEST_FAIL / LOGSEQ_TEST_FAILURES so
# run_tests.sh can tally them at the end.
#
# All helpers run their command via `"$@"` so argument quoting is preserved.
# For shell constructs (pipes, redirections, subshells) wrap them in
# `bash -c '...'` at the call site.

# Global counters. `:=` gives each a default without clobbering prior runs.
: "${LOGSEQ_TEST_PASS:=0}"
: "${LOGSEQ_TEST_FAIL:=0}"
: "${LOGSEQ_TEST_FAILURES:=}"

_tick()  { printf '  \033[32m✓\033[0m %s\n' "$*"; LOGSEQ_TEST_PASS=$((LOGSEQ_TEST_PASS+1)); }
_cross() { printf '  \033[31m✗\033[0m %s\n' "$*"; LOGSEQ_TEST_FAIL=$((LOGSEQ_TEST_FAIL+1)); LOGSEQ_TEST_FAILURES="${LOGSEQ_TEST_FAILURES}  $*\n"; }

assert_exit() {
  # assert_exit <expected_code> <label> <cmd...>
  local expected="$1"; local label="$2"; shift 2
  local output; output=$("$@" 2>&1); local rc=$?
  if [ "$rc" -eq "$expected" ]; then
    _tick "[$label] exit=$rc (expected $expected)"
  else
    _cross "[$label] exit=$rc (expected $expected). Output: $(echo "$output" | head -c 300)"
  fi
}

assert_contains() {
  # assert_contains <label> <needle> <cmd...>
  local label="$1"; local needle="$2"; shift 2
  local output; output=$("$@" 2>&1); local rc=$?
  if [ "$rc" -ne 0 ]; then
    _cross "[$label] command failed (rc=$rc). Output: $(echo "$output" | head -c 300)"
    return
  fi
  if echo "$output" | grep -qF -- "$needle"; then
    _tick "[$label] contains $(printf '%q' "$needle")"
  else
    _cross "[$label] missing needle $(printf '%q' "$needle"). Output: $(echo "$output" | head -c 300)"
  fi
}

assert_matches() {
  # assert_matches <label> <regex> <cmd...>
  local label="$1"; local regex="$2"; shift 2
  local output; output=$("$@" 2>&1); local rc=$?
  if [ "$rc" -ne 0 ]; then
    _cross "[$label] command failed (rc=$rc). Output: $(echo "$output" | head -c 300)"
    return
  fi
  if echo "$output" | grep -qE -- "$regex"; then
    _tick "[$label] matches $(printf '%q' "$regex")"
  else
    _cross "[$label] no match for $(printf '%q' "$regex"). Output: $(echo "$output" | head -c 300)"
  fi
}

assert_gt() {
  # assert_gt <label> <threshold> <cmd...>
  # Extracts the FIRST integer in output and asserts > threshold.
  local label="$1"; local threshold="$2"; shift 2
  local output; output=$("$@" 2>&1); local rc=$?
  if [ "$rc" -ne 0 ]; then
    _cross "[$label] command failed (rc=$rc). Output: $(echo "$output" | head -c 300)"
    return
  fi
  local n; n=$(echo "$output" | grep -oE '[0-9]+' | head -1)
  if [ -n "$n" ] && [ "$n" -gt "$threshold" ]; then
    _tick "[$label] $n > $threshold"
  else
    _cross "[$label] $n not > $threshold. Output: $(echo "$output" | head -c 300)"
  fi
}

# Variants for error-UX tests: tolerate non-zero exit codes, assert only on
# the output. The "real" assert_contains / assert_matches bail on rc!=0.

assert_output_contains() {
  # assert_output_contains <label> <needle> <cmd...>
  local label="$1"; local needle="$2"; shift 2
  local output; output=$("$@" 2>&1)  # rc intentionally ignored
  if echo "$output" | grep -qF -- "$needle"; then
    _tick "[$label] output contains $(printf '%q' "$needle")"
  else
    _cross "[$label] missing needle $(printf '%q' "$needle"). Output: $(echo "$output" | head -c 300)"
  fi
}

assert_output_matches() {
  # assert_output_matches <label> <regex> <cmd...>
  local label="$1"; local regex="$2"; shift 2
  local output; output=$("$@" 2>&1)  # rc intentionally ignored
  if echo "$output" | grep -qE -- "$regex"; then
    _tick "[$label] output matches $(printf '%q' "$regex")"
  else
    _cross "[$label] no match for $(printf '%q' "$regex"). Output: $(echo "$output" | head -c 300)"
  fi
}
