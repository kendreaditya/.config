#!/usr/bin/env bash
# upstream — track and re-sync vendored Claude Code components against their source.
#
# Reads an `upstream:` block from a component's frontmatter, compares the pinned
# sha to the current upstream sha, and three-way merges when both sides moved.
# The pinned sha IS the merge base: the base text is fetched from GitHub on
# demand, so nothing is cached on disk.
#
# Usage:
#   upstream.sh list                 # every tracked component and its state
#   upstream.sh status [path]        # check upstream for new commits
#   upstream.sh diff <path>          # what have I changed vs my pinned base
#   upstream.sh pull <path>          # sync one component
#   upstream.sh pull --all           # sync everything that moved
set -uo pipefail

ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.config/claude}"

die()  { printf 'upstream: %s\n' "$1" >&2; exit 1; }
warn() { printf 'upstream: %s\n' "$1" >&2; }

command -v gh >/dev/null || die "gh not installed"
command -v git >/dev/null || die "git not installed"

# ---------- frontmatter -------------------------------------------------------

# Read one key from the upstream: block. Only scans frontmatter (to first `---`
# after line 1), so a fenced example later in the body can't be mistaken for it.
fm_get() {
  awk -v key="$2" '
    NR==1 && $0=="---" { in_fm=1; next }
    in_fm && $0=="---" { exit }
    in_fm && /^upstream:[[:space:]]*$/ { in_up=1; next }
    in_up && /^[^[:space:]]/ { in_up=0 }
    in_up {
      line=$0
      sub(/^[[:space:]]+/, "", line)
      split(line, kv, ":")
      k=kv[1]
      if (k==key) {
        sub(/^[^:]*:[[:space:]]*/, "", line)
        gsub(/^["'"'"']|["'"'"']$/, "", line)
        print line
        exit
      }
    }
  ' "$1"
}

# Body hash, excluding the upstream: block. Our own bookkeeping must not read as
# a local edit, or every component would look modified forever.
body_hash() {
  awk '
    NR==1 && $0=="---" { in_fm=1; print; next }
    in_fm && $0=="---" { in_fm=0; print; next }
    in_fm && /^upstream:[[:space:]]*$/ { in_up=1; next }
    in_up && /^[[:space:]]/ { next }
    in_up { in_up=0 }
    { print }
  ' "$1" | shasum -a 256 | cut -d' ' -f1
}

tracked() {
  grep -rl --include='*.md' --include='*.json' '^upstream:' \
    "$ROOT/skills" "$ROOT/agents" "$ROOT/commands" "$ROOT/output-styles" \
    "$ROOT/hooks" "$ROOT/rules" "$ROOT/themes" 2>/dev/null | sort
}

# ---------- github -----------------------------------------------------------

remote_sha() { # repo path ref
  gh api "repos/$1/commits?path=$2&sha=$3&per_page=1" --jq '.[0].sha' 2>/dev/null
}

fetch_at() { # repo path sha -> stdout
  gh api "repos/$1/contents/$2?ref=$3" --jq '.content' 2>/dev/null | base64 -d
}

# ---------- commands ---------------------------------------------------------

cmd_list() {
  local f n
  printf '%-34s %-30s %s\n' COMPONENT SOURCE STATE
  while read -r f; do
    [ -n "$f" ] || continue
    n="${f#$ROOT/}"
    printf '%-34s %-30s %s\n' "$n" "$(fm_get "$f" repo)" "$(local_state "$f")"
  done < <(tracked)
}

local_state() { # edited | clean | unknown
  local f repo path sha stored
  f="$1"
  stored=$(fm_get "$f" content_hash)
  if [ -n "$stored" ]; then
    [ "$stored" = "$(body_hash "$f")" ] && echo clean || echo edited
    return
  fi
  repo=$(fm_get "$f" repo); path=$(fm_get "$f" path); sha=$(fm_get "$f" sha)
  [ -n "$repo" ] && [ -n "$sha" ] || { echo unknown; return; }
  local base; base=$(fetch_at "$repo" "$path" "$sha")
  [ -n "$base" ] || { echo unknown; return; }
  if [ "$(printf '%s\n' "$base" | shasum -a 256 | cut -d' ' -f1)" = "$(body_hash "$f")" ]; then
    echo clean
  else
    echo edited
  fi
}

cmd_status() {
  local f n repo path ref sha cur st
  while read -r f; do
    [ -n "$f" ] || continue
    n="${f#$ROOT/}"
    repo=$(fm_get "$f" repo); path=$(fm_get "$f" path)
    ref=$(fm_get "$f" ref); sha=$(fm_get "$f" sha)
    ref="${ref:-main}"
    [ -n "$repo" ] || { printf '%-34s no repo pinned\n' "$n"; continue; }
    cur=$(remote_sha "$repo" "$path" "$ref")
    st=$(local_state "$f")
    if [ -z "$cur" ]; then
      printf '%-34s %s\n' "$n" "upstream unreachable"
    elif [ "$cur" = "$sha" ]; then
      printf '%-34s up to date (%s)\n' "$n" "$st"
    else
      printf '%-34s UPSTREAM MOVED %s -> %s (local: %s)\n' \
        "$n" "${sha:0:8}" "${cur:0:8}" "$st"
    fi
  done < <( [ $# -gt 0 ] && echo "$1" || tracked )
}

cmd_diff() {
  local f="$1" repo path sha base mine
  [ -f "$f" ] || die "no such file: $f"
  repo=$(fm_get "$f" repo); path=$(fm_get "$f" path); sha=$(fm_get "$f" sha)
  [ -n "$repo" ] || die "no upstream: block in $f"
  base=$(mktemp); fetch_at "$repo" "$path" "$sha" > "$base"
  [ -s "$base" ] || { rm -f "$base"; die "base sha $sha unreachable (force-push? deleted?)"; }
  # Compare without our own upstream: block, so the diff shows only real edits.
  mine=$(mktemp); strip_upstream "$f" > "$mine"
  diff -u --label "upstream@${sha:0:8}" --label "local" "$base" "$mine" || true
  rm -f "$base" "$mine"
}

cmd_pull() {
  local f="$1" repo path ref sha cur base new merged rc st
  [ -f "$f" ] || die "no such file: $f"
  repo=$(fm_get "$f" repo); path=$(fm_get "$f" path)
  ref=$(fm_get "$f" ref); sha=$(fm_get "$f" sha); ref="${ref:-main}"
  [ -n "$repo" ] || die "no upstream: block in $f"

  cur=$(remote_sha "$repo" "$path" "$ref")
  [ -n "$cur" ] || die "cannot reach $repo"
  if [ "$cur" = "$sha" ]; then echo "already at ${cur:0:8}"; return 0; fi

  st=$(local_state "$f")
  new=$(mktemp); fetch_at "$repo" "$path" "$cur" > "$new"
  [ -s "$new" ] || { rm -f "$new"; die "could not fetch $cur"; }

  if [ "$st" = clean ]; then
    # Case 2: clean local, upstream moved -> overwrite, no merge possible.
    cp "$new" "$f"
    stamp "$f" "$repo" "$path" "$ref" "$cur" "$(shasum -a 256 < "$new" | cut -d' ' -f1)"
    echo "updated (clean overwrite) -> ${cur:0:8}"
    rm -f "$new"; return 0
  fi

  # Case 4: both moved -> three-way merge with the pinned sha as base.
  base=$(mktemp); fetch_at "$repo" "$path" "$sha" > "$base"
  if [ ! -s "$base" ]; then
    rm -f "$base" "$new"
    warn "base sha $sha unreachable; not merging. Review manually:"
    warn "  upstream.sh diff $f"
    return 1
  fi
  merged=$(mktemp); strip_upstream "$f" > "$merged"
  git merge-file --diff3 -L local -L "upstream@${sha:0:8}" -L "upstream@${cur:0:8}" \
    "$merged" "$base" "$new"
  rc=$?
  cp "$merged" "$f"
  stamp "$f" "$repo" "$path" "$ref" "$cur" "$(shasum -a 256 < "$new" | cut -d' ' -f1)"
  if [ "$rc" -eq 0 ]; then
    echo "merged cleanly -> ${cur:0:8}"
  else
    echo "MERGED WITH $rc CONFLICT(S) -> ${cur:0:8}; resolve markers in $f"
  fi
  rm -f "$base" "$new" "$merged"
  [ "$rc" -eq 0 ]
}

strip_upstream() {
  awk '
    NR==1 && $0=="---" { in_fm=1; print; next }
    in_fm && $0=="---" { in_fm=0; print; next }
    in_fm && /^upstream:[[:space:]]*$/ { in_up=1; next }
    in_up && /^[[:space:]]/ { next }
    in_up { in_up=0 }
    { print }
  ' "$1"
}

stamp() { # file repo path ref sha [pristine_hash]
  # content_hash records the hash of PRISTINE UPSTREAM at this sha, not of the
  # local file. Comparing the local body against it is what detects local edits;
  # hashing the local file here would make every file look clean forever.
  local f="$1" tmp h
  tmp=$(mktemp)
  strip_upstream "$f" > "$tmp"
  h="${6:-$(shasum -a 256 < "$tmp" | cut -d' ' -f1)}"
  {
    head -1 "$tmp"
    sed -n '2,$p' "$tmp" | sed '/^---$/q' | sed '$d'
    printf 'upstream:\n  repo: %s\n  path: %s\n  ref: %s\n  sha: %s\n  checked: %s\n  content_hash: %s\n' \
      "$2" "$3" "$4" "$5" "$(date +%Y-%m-%d)" "$h"
    echo '---'
    awk 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{f=0;next} !f' "$tmp"
  } > "$f"
  rm -f "$tmp"
}

case "${1:-list}" in
  list)   cmd_list ;;
  status) shift; cmd_status "$@" ;;
  diff)   shift; [ $# -eq 1 ] || die "usage: diff <path>"; cmd_diff "$1" ;;
  pull)
    shift
    if [ "${1:-}" = --all ]; then
      while read -r f; do [ -n "$f" ] && cmd_pull "$f" || true; done < <(tracked)
    else
      [ $# -eq 1 ] || die "usage: pull <path> | pull --all"; cmd_pull "$1"
    fi ;;
  *) die "unknown command: $1 (list|status|diff|pull)" ;;
esac
