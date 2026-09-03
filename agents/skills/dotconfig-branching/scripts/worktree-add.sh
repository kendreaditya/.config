#!/usr/bin/env bash
# worktree-add.sh — add a linked git worktree for this repo, working around a
# git-crypt 0.8.0 bug that otherwise breaks it.
#
# git-crypt stores its symmetric key once, in the shared common
# .git/git-crypt/keys/ directory. That part works fine across worktrees. But
# git-crypt's own clean/smudge filter looks for the key under the calling
# worktree's OWN git-dir (.git/worktrees/<name>/git-crypt/), which is never
# populated for a linked worktree — so `git-crypt unlock`, `git status`, and
# any checkout that touches an encrypted path all fail with "Unable to open
# key file", even though the key demonstrably exists at the shared path.
# Verified reproducible from a from-scratch clone, not a stale-state artifact.
#
# The fix: symlink the linked worktree's git-dir git-crypt/ path to the shared
# common one, then (re-)checkout so the smudge filter reruns now that it can
# find the key. `git worktree add --no-checkout` is required first — a plain
# `add` tries to check out immediately and fails before this script gets a
# chance to place the symlink.
#
# Usage:
#   worktree-add.sh <path> <branch>
#
# Example:
#   worktree-add.sh ~/.config-main main
set -uo pipefail

die() { printf '\n%s\n' "$*" >&2; exit 1; }
note() { printf '\n\033[1m%s\033[0m\n' "$*"; }

root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "worktree-add.sh: not inside a git repo"
cd "$root" || die "worktree-add.sh: cannot cd to $root"

[ "$#" -eq 2 ] || die "worktree-add.sh: usage: worktree-add.sh <path> <branch>"
wt_path="$1"
wt_branch="$2"

note "Adding worktree for '$wt_branch' at $wt_path"
git worktree add --no-checkout "$wt_path" "$wt_branch" \
  || die "worktree-add.sh: 'git worktree add' failed."

common_dir="$(git rev-parse --git-common-dir)"
wt_gitdir="$(git -C "$wt_path" rev-parse --git-dir)"

if [ -d "$common_dir/git-crypt/keys" ]; then
  if [ ! -e "$wt_gitdir/git-crypt" ]; then
    rel="$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" \
      "$common_dir/git-crypt" "$wt_gitdir")"
    ln -s "$rel" "$wt_gitdir/git-crypt"
    note "Linked $wt_gitdir/git-crypt -> $rel (git-crypt worktree workaround)"
  fi
else
  note "git-crypt is locked here — skipping the key-directory symlink."
  note "Run 'git-crypt unlock <key>' in $root first, then re-run this script."
fi

git -C "$wt_path" checkout "$wt_branch" \
  || die "worktree-add.sh: checkout failed even after the git-crypt symlink workaround."

note "Initializing submodules in $wt_path (not shared across worktrees)"
git -C "$wt_path" submodule update --init --recursive \
  || die "worktree-add.sh: submodule init failed."

note "Done. $wt_path is a clean, decrypted worktree on '$wt_branch'."
git -C "$wt_path" status --short --untracked-files=no
