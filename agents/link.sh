#!/usr/bin/env bash
# link.sh — wire this repo's agents/ tree into each harness's config directory.
#
# Layout:
#   agents/skills|commands|memory|personas   harness-agnostic, shared by all
#   agents/harness/<name>/...                per-harness config (settings, prompts)
#
# Shared content is symlinked into every harness; harness/<name>/ only into that
# harness. Idempotent — safe to re-run. Currently wires claude + codex.
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

# NOTE: ~/.codex/config.toml is intentionally NOT linked. It mixes MCP config
# with mutable session state (auth tokens, per-project history), same reason
# ~/.claude.json is untracked. Manage it via `codex mcp` / setup-macos.sh.

echo
echo "done. re-run anytime; nothing is destructive to real files."
