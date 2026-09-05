#!/usr/bin/env bash
# link.sh — wire this repo's agents/ tree into each harness's config directory.
#
# Layout:
#   agents/skills|commands|memory|personas   harness-agnostic, shared by all
#   agents/harness/<name>/...                per-harness config (settings, prompts)
#
# Shared content is symlinked into every harness; harness/<name>/ only into that
# harness. Idempotent — safe to re-run. Currently wires the shared Agent Skills
# location plus Claude Code, Codex, and Pi.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS="$REPO/agents"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

log()  { printf '  %s\n' "$*"; }
warn() { printf '  WARN: %s\n' "$*" >&2; }

# link <target> <linkpath>
link() {
  local target="$1" linkpath="$2"
  [ -e "$target" ] || { warn "missing target, skipped: $target"; return 0; }
  if [ -L "$linkpath" ] && [ "$(readlink "$linkpath")" = "$target" ]; then
    log "ok       ${linkpath/#$HOME/~}"; return 0
  fi
  # Refuse to clobber real files/dirs — only replace symlinks or absent paths.
  if [ -e "$linkpath" ] && [ ! -L "$linkpath" ]; then
    warn "exists as real file/dir, NOT replacing: ${linkpath/#$HOME/~}"
    warn "         move it aside and re-run to link ${target/#$HOME/~}"
    return 0
  fi
  if [ "$DRY" = 1 ]; then log "would    ${linkpath/#$HOME/~} -> ${target/#$HOME/~}"; return 0; fi
  mkdir -p "$(dirname "$linkpath")"
  ln -sfn "$target" "$linkpath"
  log "linked   ${linkpath/#$HOME/~} -> ${target/#$HOME/~}"
}

# ---------------------------------------------------------- shared agent skills
# Pi discovers ~/.agents/skills natively. Other Agent Skills-compatible tools
# can use it too, so point it at the same canonical collection instead of
# maintaining a copied directory that can drift.
echo "agent skills:"
link "$AGENTS/skills" "$HOME/.agents/skills"

# ---------------------------------------------------------------- claude code
# Claude reads skills/commands/agents/memory as directories directly under
# ~/.claude, and its settings/prompt files at fixed names there.
echo "claude:"
CLAUDE_DIR="$HOME/.claude"
link "$AGENTS/skills"                        "$CLAUDE_DIR/skills"
link "$AGENTS/commands"                      "$CLAUDE_DIR/commands"
link "$AGENTS/memory"                        "$CLAUDE_DIR/memory"
link "$AGENTS/personas"                      "$CLAUDE_DIR/agents"
link "$AGENTS/harness/claude/settings.json"  "$CLAUDE_DIR/settings.json"
link "$AGENTS/harness/claude/CLAUDE.md"      "$CLAUDE_DIR/CLAUDE.md"
link "$AGENTS/harness/claude/output-styles"  "$CLAUDE_DIR/output-styles"

# ---------------------------------------------------------------------- codex
# Codex namespaces user skills under ~/.codex/skills/user (its own generated
# content lives in ~/.codex/skills/.system, so do NOT link the parent).
# Codex agents are .toml, not .md, so personas are not shared here — they live
# in harness/codex/agents/.
echo "codex:"
CODEX_DIR="$HOME/.codex"
link "$AGENTS/skills"                     "$CODEX_DIR/skills/user"
link "$AGENTS/commands"                   "$CODEX_DIR/prompts"
link "$AGENTS/memory"                     "$CODEX_DIR/memory"
link "$AGENTS/harness/codex/AGENTS.md"    "$CODEX_DIR/AGENTS.md"
link "$AGENTS/harness/codex/agents"       "$CODEX_DIR/agents"

# ------------------------------------------------------------------------- pi
# Pi discovers shared skills through ~/.agents/skills above. Only its global
# context file is harness-specific; settings.json remains machine-local because
# it can contain provider and extension configuration.
echo "pi:"
PI_DIR="$HOME/.pi/agent"
link "$AGENTS/harness/pi/AGENTS.md" "$PI_DIR/AGENTS.md"

# NOTE: ~/.codex/config.toml is intentionally NOT linked. It mixes MCP config
# with mutable session state (auth tokens, per-project history), same reason
# ~/.claude.json and ~/.pi/agent/settings.json are untracked. Manage them with
# their respective harnesses and setup scripts.

echo
echo "done. re-run anytime; nothing is destructive to real files."
