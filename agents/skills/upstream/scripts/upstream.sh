#!/usr/bin/env bash
# upstream — track and re-sync vendored agent components against their source.
#
# Reads an `upstream:` block from a component's frontmatter, compares the pinned
# sha to the current upstream sha, and three-way merges when both sides moved.
# The pinned sha IS the merge base: the base text is fetched from GitHub on
# demand, so nothing is cached on disk.
#
# Usage:
#   upstream.sh list                 # every tracked component and its state
#   upstream.sh untracked            # skills needing a provenance decision
#   upstream.sh status [path]        # check upstream for new commits
#   upstream.sh diff <path>          # what have I changed vs my pinned base
#   upstream.sh pull <path>          # sync one component
#   upstream.sh pull --all           # sync everything that moved
set -uo pipefail

ROOT="${AGENT_CONFIG_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.config/agents}}"

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
#
# Every hash in this script MUST go through hash_stream, so that a stored hash and
# the hash it is later compared against are computed identically. The pristine
# upstream text has no upstream: block to strip, but it still has to pass through
# the same awk normalization: awk always terminates the final line with \n, so
# hashing raw bytes here and stripped bytes there diverges on any file that lacks
# a trailing newline -- which silently marks pristine files as `edited` forever.
hash_stream() { shasum -a 256 | cut -d' ' -f1; }

norm() { # strip the upstream: block; normalizes trailing newline as a side effect
  awk '
    NR==1 && $0=="---" { in_fm=1; print; next }
    in_fm && $0=="---" { in_fm=0; print; next }
    in_fm && /^upstream:[[:space:]]*$/ { in_up=1; next }
    in_up && /^[[:space:]]/ { next }
    in_up { in_up=0 }
    { print }
  ' "${1:--}"
}

body_hash() { norm "$1" | hash_stream; }

tracked() {
  local f
  [ -d "$ROOT/skills" ] \
    || { warn "no such directory: $ROOT/skills (set AGENT_CONFIG_DIR?)"; return 0; }

  # Parse candidate files through fm_get. A plain grep also matches the example
  # `upstream:` blocks in this skill's own body and incorrectly reports them as
  # tracked components with an unknown source.
  while IFS= read -r f; do
    if [ -n "$(fm_get "$f" repo)" ] || [ -n "$(fm_get "$f" gist)" ]; then
      printf '%s\n' "$f"
    fi
  done < <(
    for dir in skills agents personas commands output-styles hooks rules themes; do
      [ -d "$ROOT/$dir" ] && find "$ROOT/$dir" -type f \( -name '*.md' -o -name '*.json' \)
    done | sort -u
  )
}

# ---------- github -----------------------------------------------------------

# Two source kinds. A repo pins `repo`/`path`/`ref`; a gist pins `gist`/`file`.
# They need different endpoints, different sha semantics, and different decoding,
# so every network call dispatches on this rather than assuming a repo.
src_kind() { [ -n "$(fm_get "$1" gist)" ] && echo gist || echo repo; }

remote_sha() { # file -> latest upstream sha
  local f="$1" repo path ref
  if [ "$(src_kind "$f")" = gist ]; then
    # A gist has no branches, and its history is global to the gist rather than
    # per-file: editing any file in the gist advances the version every file is
    # compared against. So a moved sha means "something in the gist changed",
    # not necessarily this file. `diff` is what tells you whether yours moved.
    gh api "gists/$(fm_get "$f" gist)" --jq '.history[0].version' 2>/dev/null
    return
  fi
  repo=$(fm_get "$f" repo); path=$(fm_get "$f" path)
  ref=$(fm_get "$f" ref); ref="${ref:-main}"
  # -f lets gh URL-encode the path. Interpolating it raw makes `gh api` hang
  # indefinitely on a path containing a space, rather than failing fast.
  gh api "repos/$repo/commits" -X GET -f "path=$path" -f "sha=$ref" -f per_page=1 \
    --jq '.[0].sha' 2>/dev/null
}

fetch_at() { # file sha -> stdout
  local f="$1" sha="$2" repo path c
  if [ "$(src_kind "$f")" = gist ]; then
    # The gist API returns file content already decoded as a JSON string, so
    # there is no base64 step here. Files over ~1MB come back with
    # "truncated": true and a raw_url instead; reject rather than write a stub.
    #
    # Pipe to real jq rather than using `gh api --jq`: that flag accepts exactly
    # ONE argument, so passing `--arg` to it fails with "accepts 1 arg(s),
    # received 4" -- and because the failure is swallowed by 2>/dev/null it
    # surfaces as a bogus "base sha unreachable", not as a usage error.
    gh api "gists/$(fm_get "$f" gist)/$sha" 2>/dev/null \
      | jq -r --arg n "$(fm_get "$f" file)" \
        'if .files[$n].truncated then empty else (.files[$n].content // empty) end' 2>/dev/null
    return
  fi
  repo=$(fm_get "$f" repo); path=$(fm_get "$f" path)
  # GitHub returns {"content": null} for files over the ~1MB inline limit. jq
  # prints the literal string "null", which base64 -d happily decodes into 3
  # bytes of garbage with exit 0 -- passing every caller's [ -s ] check and
  # overwriting a real skill with junk. Reject it before decoding.
  c=$(gh api "repos/$repo/contents/$path" -X GET -f "ref=$sha" --jq '.content' 2>/dev/null)
  [ -n "$c" ] && [ "$c" != null ] || return 1
  printf '%s' "$c" | base64 -d 2>/dev/null
}

# What to show in `list`, and what to name in errors.
src_label() {
  [ "$(src_kind "$1")" = gist ] \
    && echo "gist:$(fm_get "$1" gist | cut -c1-12)" \
    || fm_get "$1" repo
}

# ---------- commands ---------------------------------------------------------

cmd_list() {
  local f n
  printf '%-34s %-30s %s\n' COMPONENT SOURCE STATE
  while read -r f; do
    [ -n "$f" ] || continue
    n="${f#$ROOT/}"
    printf '%-34s %-30s %s\n' "$n" "$(src_label "$f")" "$(local_state "$f")"
  done < <(tracked)
}

cmd_untracked() {
  local f n
  [ -d "$ROOT/skills" ] \
    || { warn "no such directory: $ROOT/skills (set AGENT_CONFIG_DIR?)"; return 0; }
  printf '%s\n' 'SKILLS WITHOUT VERIFIED UPSTREAM'
  while IFS= read -r f; do
    [ -n "$(fm_get "$f" repo)" ] && continue
    [ -n "$(fm_get "$f" gist)" ] && continue
    n="${f#$ROOT/}"
    printf '%s\n' "$n"
  done < <(find "$ROOT/skills" -type f -name SKILL.md | sort)
}

local_state() { # edited | clean | unknown
  local f sha stored base bh
  f="$1"
  stored=$(fm_get "$f" content_hash)
  if [ -n "$stored" ]; then
    [ "$stored" = "$(body_hash "$f")" ] && echo clean || echo edited
    return
  fi
  sha=$(fm_get "$f" sha)
  [ -n "$(src_label "$f")" ] && [ -n "$sha" ] || { echo unknown; return; }
  # Route the base through a FILE, never `$(fetch_at ...)`. Command substitution
  # strips every trailing newline, so a file whose upstream ends in a blank line
  # hashes differently here than in body_hash (which reads the file directly) --
  # reporting a pristine component as `edited` forever, which then routes it into
  # the three-way merge path and writes conflict markers into a file the user
  # never touched. Same class of bug as the awk normalization note above.
  base=$(mktemp)
  fetch_at "$f" "$sha" > "$base"
  if [ ! -s "$base" ]; then rm -f "$base"; echo unknown; return; fi
  bh=$(norm "$base" | hash_stream)
  rm -f "$base"
  [ "$bh" = "$(body_hash "$f")" ] && echo clean || echo edited
}

cmd_status() {
  local f n sha cur st
  while read -r f; do
    [ -n "$f" ] || continue
    n="${f#$ROOT/}"
    sha=$(fm_get "$f" sha)
    [ -n "$(src_label "$f")" ] || { printf '%-34s no source pinned\n' "$n"; continue; }
    cur=$(remote_sha "$f")
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
  local f="$1" sha base mine
  [ -f "$f" ] || die "no such file: $f"
  sha=$(fm_get "$f" sha)
  [ -n "$(src_label "$f")" ] || die "no upstream: block in $f"
  base=$(mktemp); fetch_at "$f" "$sha" > "$base"
  [ -s "$base" ] || { rm -f "$base"; die "base sha $sha unreachable (force-push? deleted?)"; }
  # Compare without our own upstream: block, so the diff shows only real edits.
  mine=$(mktemp); strip_upstream "$f" > "$mine"
  diff -u --label "upstream@${sha:0:8}" --label "local" "$base" "$mine" || true
  rm -f "$base" "$mine"
}

cmd_pull() {
  local f="$1" sha cur base new merged rc st
  [ -f "$f" ] || die "no such file: $f"
  sha=$(fm_get "$f" sha)
  [ -n "$(src_label "$f")" ] || die "no upstream: block in $f"

  cur=$(remote_sha "$f")
  [ -n "$cur" ] || die "cannot reach $(src_label "$f")"
  if [ "$cur" = "$sha" ]; then echo "already at ${cur:0:8}"; return 0; fi

  st=$(local_state "$f")
  new=$(mktemp); fetch_at "$f" "$cur" > "$new"
  # A gist sha advances when ANY file in it changes, so an unreachable or
  # identical fetch here is normal rather than an error: this file did not move.
  if [ ! -s "$new" ]; then
    rm -f "$new"
    if [ "$(src_kind "$f")" = gist ]; then
      warn "gist moved to ${cur:0:8} but $(fm_get "$f" file) is absent there; not pulling"
      return 1
    fi
    die "could not fetch $cur"
  fi

  if [ "$st" = clean ]; then
    # Case 2: clean local, upstream moved -> overwrite, no merge possible.
    cp "$new" "$f"
    stamp "$f" "$cur" "$(norm "$new" | hash_stream)"
    echo "updated (clean overwrite) -> ${cur:0:8}"
    rm -f "$new"; return 0
  fi

  # Case 4: both moved -> three-way merge with the pinned sha as base.
  base=$(mktemp); fetch_at "$f" "$sha" > "$base"
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
  stamp "$f" "$cur" "$(norm "$new" | hash_stream)"
  if [ "$rc" -eq 0 ]; then
    echo "merged cleanly -> ${cur:0:8}"
  else
    echo "MERGED WITH $rc CONFLICT(S) -> ${cur:0:8}; resolve markers in $f"
  fi
  rm -f "$base" "$new" "$merged"
  [ "$rc" -eq 0 ]
}

strip_upstream() { norm "$1"; }

stamp() { # file sha [pristine_hash]
  # content_hash records the hash of PRISTINE UPSTREAM at this sha, not of the
  # local file. Comparing the local body against it is what detects local edits;
  # hashing the local file here would make every file look clean forever.
  #
  # Source coordinates (repo/path/ref, or gist/file) are preserved verbatim from
  # the existing block: only sha, checked, and content_hash advance on a pull.
  local f="$1" tmp h coords
  tmp=$(mktemp)
  strip_upstream "$f" > "$tmp"
  h="${3:-$(hash_stream < "$tmp")}"
  if [ "$(src_kind "$f")" = gist ]; then
    coords=$(printf '  gist: %s\n  file: %s\n' \
      "$(fm_get "$f" gist)" "$(fm_get "$f" file)")
  else
    coords=$(printf '  repo: %s\n  path: %s\n  ref: %s\n' \
      "$(fm_get "$f" repo)" "$(fm_get "$f" path)" "$(fm_get "$f" ref)")
  fi
  {
    head -1 "$tmp"
    sed -n '2,$p' "$tmp" | sed '/^---$/q' | sed '$d'
    printf 'upstream:\n%s\n' "$coords"
    printf '  sha: %s\n  checked: %s\n  content_hash: %s\n' \
      "$2" "$(date +%Y-%m-%d)" "$h"
    echo '---'
    awk 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{f=0;next} !f' "$tmp"
  } > "$f"
  rm -f "$tmp"
}

case "${1:-list}" in
  list)      cmd_list ;;
  untracked) cmd_untracked ;;
  status)    shift; cmd_status "$@" ;;
  diff)   shift; [ $# -eq 1 ] || die "usage: diff <path>"; cmd_diff "$1" ;;
  pull)
    shift
    if [ "${1:-}" = --all ]; then
      while read -r f; do [ -n "$f" ] && cmd_pull "$f" || true; done < <(tracked)
    else
      [ $# -eq 1 ] || die "usage: pull <path> | pull --all"; cmd_pull "$1"
    fi ;;
  *) die "unknown command: $1 (list|untracked|status|diff|pull)" ;;
esac
