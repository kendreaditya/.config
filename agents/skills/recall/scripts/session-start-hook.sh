#!/bin/sh
# SessionStart hook: surface due recall cards as context, at most once per day.
#
# Wire into ~/.claude/settings.json:
#   {"hooks":{"SessionStart":[{"hooks":[{"type":"command",
#     "command":"~/.config/agents/skills/recall/scripts/session-start-hook.sh"}]}]}}
#
# Prints nothing when nothing is due or when it already fired today, so it stays
# invisible across many sessions per day. Always exits 0 — a memory aid must never
# block a session.

set -u
STORE="${RECALL_HOME:-$HOME/.claude/recall}"
STAMP="$STORE/.last-nudge"
SCRIPT="$HOME/.config/agents/skills/recall/scripts/recall.py"

[ -f "$SCRIPT" ] || exit 0
[ -d "$STORE/cards" ] || exit 0

# Once per calendar day, regardless of how many sessions start.
TODAY=$(date +%Y-%m-%d)
[ -f "$STAMP" ] && [ "$(cat "$STAMP" 2>/dev/null)" = "$TODAY" ] && exit 0

N=$(python3 "$SCRIPT" due --json 2>/dev/null \
    | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null) || exit 0
[ "${N:-0}" -gt 0 ] 2>/dev/null || exit 0

mkdir -p "$STORE" 2>/dev/null
printf '%s' "$TODAY" > "$STAMP" 2>/dev/null

# stdout from SessionStart becomes context Claude can see and act on.
printf 'recall: %s card(s) due for review. If the user has a moment, offer a quick review via the `recall` skill (Mode 2). Do not start one unprompted if they are mid-task.\n' "$N"
exit 0
