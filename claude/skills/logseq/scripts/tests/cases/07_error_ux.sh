#!/usr/bin/env bash
# 07_error_ux.sh — exit codes and user-facing error messages.
#
# Contract (from AGENT_CONTRACT.md):
#   0 success, 1 generic failure, 2 unauthorized (401),
#   3 unreachable (connection refused), 4 bad args, 5 method doesn't exist.

# ---------------------------------------------------------------------------
# Connection refused — port 65530 nobody is listening on.
# Use assert_output_* variants that tolerate the non-zero rc we expect.
# ---------------------------------------------------------------------------
assert_exit 3 "wrong port: exit 3"                   env LOGSEQ_PORT=65530 logseq today
assert_output_matches "wrong port: says 'not running'"  "not running|refused|unreachable"  env LOGSEQ_PORT=65530 logseq today

# ---------------------------------------------------------------------------
# Bad token — server returns 401; CLI should exit 2 and mention auth.
# CAVEAT: if the user's Logseq server was started WITHOUT any configured
# tokens, the server accepts any bearer token (server-side validation no-ops
# on an empty tokens list). In that case we can't exercise the bad-token
# path. Probe once and skip gracefully.
# ---------------------------------------------------------------------------
_probe=$(env LOGSEQ_API_TOKEN=definitely-wrong-token-xyz logseq today --format json 2>&1)
_probe_rc=$?
if [ "$_probe_rc" -eq 0 ]; then
  _tick "[bad token] skipped — server accepts any token (no :server/tokens configured)"
else
  assert_exit 2 "bad token: exit 2"                         env LOGSEQ_API_TOKEN=definitely-wrong-token-xyz logseq today
  assert_output_matches "bad token: mentions token/auth"    "token|auth|Invalid|unauthorized"  env LOGSEQ_API_TOKEN=definitely-wrong-token-xyz logseq today
fi

# ---------------------------------------------------------------------------
# Unknown API method — exit 5 and suggest (Levenshtein) the closest known.
# ---------------------------------------------------------------------------
assert_exit 5 "bad method: exit 5"                          logseq raw "get_pag"
assert_output_matches "bad method: suggests 'get_page'"     "Did you mean|get_page"  logseq raw "get_pag"

# ---------------------------------------------------------------------------
# Bad datalog — the server returns an error body; CLI should exit non-zero.
# Some builds classify as 4 (bad args) vs 1 (generic); accept any non-zero.
# ---------------------------------------------------------------------------
# Use a raw rc check since assert_exit takes a single expected value.
output=$(logseq datalog "not-valid-datalog" 2>&1); rc=$?
if [ "$rc" -ne 0 ]; then
  _tick "bad datalog: non-zero exit=$rc"
else
  _cross "bad datalog: expected non-zero exit, got 0. Output: $(echo "$output" | head -c 300)"
fi
