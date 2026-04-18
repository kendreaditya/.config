#!/usr/bin/env bash
# 01_meta.sh — init/doctor/version/graph/graphs/config/use
#
# These commands don't hit the graph data; they report CLI/server meta.
# Sourced from run_tests.sh which sets up $SCRIPT_DIR, env, and assert.sh.

# version
assert_exit 0 "version: runs"                  logseq version
# Logseq Desktop is pinned to 0.10.15 for the test graph; tolerate minor drift
# by just asserting a semver-looking string.
assert_matches "version: semver-ish"           '[0-9]+\.[0-9]+\.[0-9]+'  logseq version

# graph — current graph name
assert_exit 0 "graph: runs"                    logseq graph
assert_contains "graph: logseq-test"           "logseq-test"  logseq graph

# graphs — list of known graphs should mention logseq-test
assert_exit 0 "graphs: runs"                   logseq graphs
assert_contains "graphs: contains logseq-test" "logseq-test"  logseq graphs

# config — show resolved config (host, port, redacted token, etc.)
assert_exit 0 "config-get: runs"               logseq config-get

# doctor — round-trip ping/auth check against running server
assert_exit 0 "doctor: runs"                   logseq doctor
assert_contains "doctor: mentions graph name"  "logseq-test"  logseq doctor
