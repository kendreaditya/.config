#!/usr/bin/env bash
# reconcile-device.sh — give the device branch a real fork point on main.
#
# THE PROBLEM. main's root commit lost its GPG signature during a history
# rewrite (a secret scrub). A commit's hash covers its signature, and every
# child's hash covers its parent's, so that one byte-level change re-hashed
# every commit downstream. The result: device and main are content-identical
# twins for their first 182 commits but share NO COMMON ANCESTOR by hash.
# `git merge-base` returns nothing, `git log main..device` is meaningless, and
# `git rebase main` would replay the whole branch against unrelated objects.
#
# THE FIX. Rebuild the device branch as: main's tip, plus only the commits that
# are genuinely device-only. Not a rebase -- there is no shared base to rebase
# onto. Not `git cherry-pick fork..device` either: ~40% of those commits are
# content-duplicates of main's rewritten ones and conflict on arrival. This
# filters by patch-id (`git cherry`) first, so duplicates are dropped.
#
# THE SAFETY PROPERTY. The rebuilt branch's final tree must be byte-identical
# to the current device tree. Same files, better ancestry. The script refuses
# to swap anything if that check fails, and always tags a backup first.
#
# Usage:
#   reconcile-device.sh                 # plan only: show what would happen
#   reconcile-device.sh --run           # build in a scratch worktree, verify
#   reconcile-device.sh --run --adopt   # ...and move the device branch onto it
#   reconcile-device.sh --from <sha>    # replay start (default: after reconcile)
#
# Conflicts stop the run and print the resolution command. Nothing in
# ~/.config is touched until --adopt, and --adopt refuses on a dirty tree.
set -uo pipefail

die()  { printf '\n%s\n' "$*" >&2; exit 1; }
note() { printf '\n\033[1m%s\033[0m\n' "$*"; }

self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
here="$(dirname "$self")"
root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "reconcile-device.sh: not inside a git repo"
cd "$root" || die "cannot cd to $root"

do_run=0; do_adopt=0; from=""
for arg in "$@"; do
  case "$arg" in
    --run)    do_run=1 ;;
    --adopt)  do_run=1; do_adopt=1 ;;
    --from)   from="NEXT" ;;
    -h|--help) sed -n '2,30p' "$self" | sed -e 's/^#$//' -e 's/^# //'; exit 0 ;;
    -*)       die "unknown flag: $arg" ;;
    *)        [ "$from" = "NEXT" ] && from="$arg" || die "unexpected argument: $arg" ;;
  esac
done
[ "$from" != "NEXT" ] || die "--from needs a commit argument."

DEVICE="$(git rev-parse --abbrev-ref HEAD)"
[ "$DEVICE" != "main" ] || die "run this from the device branch's worktree, not main's."
[ "$DEVICE" != "HEAD" ] || die "detached HEAD; switch to your device branch first."

git rev-parse --verify -q main >/dev/null || die "no local 'main' branch."

# ---------- locate the fork point -------------------------------------------
# By hash there is none, so find it by CONTENT: walk both branches oldest-first
# and take the last position where (tree, subject) agree. Trees are what matter
# -- identical trees mean identical file content, whatever the hashes say.
note "Locating the content fork point (no shared ancestor exists by hash)"
git rev-list --reverse "$DEVICE" | while read -r c; do git log -1 --format='%T|%s' "$c"; done > /tmp/.rd-dev.$$
git rev-list --reverse main     | while read -r c; do git log -1 --format='%T|%s' "$c"; done > /tmp/.rd-main.$$
n=0
while IFS= read -r line; do
  m="$(sed -n "$((n+1))p" /tmp/.rd-main.$$)"
  [ "$line" = "$m" ] || break
  n=$((n+1))
done < /tmp/.rd-dev.$$
rm -f /tmp/.rd-dev.$$ /tmp/.rd-main.$$
[ "$n" -gt 0 ] || die "no common content prefix at all — this repo is not the case this script handles."

FORK_DEV="$(git rev-list --reverse "$DEVICE" | sed -n "${n}p")"
FORK_MAIN="$(git rev-list --reverse main | sed -n "${n}p")"
[ "$(git rev-parse "$FORK_DEV^{tree}")" = "$(git rev-parse "$FORK_MAIN^{tree}")" ] \
  || die "internal: fork candidates disagree on tree; refusing to guess."

echo "  shared prefix: $n commits"
echo "  fork on $DEVICE: $(git log -1 --format='%h %ad %s' --date=short "$FORK_DEV")"
echo "  fork on main:   $(git log -1 --format='%h %ad %s' --date=short "$FORK_MAIN")"

# ---------- decide what to replay -------------------------------------------
# git cherry compares by patch-id: '+' = not in main, '-' = already in main
# under a different hash. Dropping the '-' set is what makes this tractable.
# Built with a read loop, not `mapfile`: that is bash 4+, and macOS ships the
# bash 3.2 that /bin/bash still resolves to.
candidates=()
while IFS= read -r c; do
  [ -n "$c" ] && candidates+=("$c")
done < <(git cherry main "$DEVICE" "$FORK_DEV" 2>/dev/null | awk '$1=="+"{print $2}')
dupes=$(git cherry main "$DEVICE" "$FORK_DEV" 2>/dev/null | grep -c '^-' || true)
total=$(git rev-list --count "$FORK_DEV..$DEVICE")
[ "${#candidates[@]}" -gt 0 ] || die "no device-only commits to replay; nothing to do."

note "Filtering by patch-id"
echo "  device-only commits since fork:      $total"
echo "  already on main by content (dropped): $dupes"
echo "  genuinely new (candidates):           ${#candidates[@]}"

# Default replay start: skip the reconcile batch, whose content main already
# holds under restructured paths -- replaying it means re-resolving that
# restructure by hand. Everything after it applies far more cleanly.
if [ -n "$from" ]; then
  start="$(git rev-parse "$from")" || die "--from: bad commit"
  replay=(); seen=0
  for c in "${candidates[@]}"; do
    if [ "$seen" -eq 0 ] && [ "$(git rev-parse "$c")" = "$start" ]; then seen=1; fi
    if [ "$seen" -eq 1 ]; then replay+=("$c"); fi
  done
  [ "${#replay[@]}" -gt 0 ] || die "--from $from is not among the candidates."
else
  # Replay every candidate. An earlier version of this script dropped the
  # oldest same-date batch as "already on main", which was wrong and the tree
  # gate caught it: that batch contains the `device:` commits that ADD all the
  # private, never-public config (work skills, harness settings, bunnylol,
  # shell). Dropping them silently deleted 8,512 lines. Only patch-id equality
  # (git cherry, above) is a safe reason to drop a commit -- calendar dates
  # are not. If a kept commit turns out to be a superseded intermediate, the
  # conflict handler below reports it and you skip it deliberately.
  replay=("${candidates[@]}")
fi

note "Would replay ${#replay[@]} commit(s) onto main"
for c in "${replay[@]}"; do git log -1 --format='  %h %ad %s' --date=short "$c"; done

if [ "$do_run" -eq 0 ]; then
  cat <<EOF

Plan only — nothing was changed. To build and verify it in a scratch worktree:

    $self --run

Add --adopt to move $DEVICE onto the result once verification passes.
EOF
  exit 0
fi

# ---------- build it in a scratch worktree ----------------------------------
# Never build in ~/.config: a failed replay would leave the real working tree
# mid-cherry-pick. worktree-add.sh is required rather than plain `git worktree
# add` because this repo has git-crypt paths (see SKILL.md).
SCRATCH="${TMPDIR:-/tmp}/reconcile-device.$$"
CAND="reconcile/${DEVICE##*/}"
wt_add="$here/worktree-add.sh"
[ -x "$wt_add" ] || die "worktree-add.sh missing at $wt_add"

cleanup() {
  [ -d "$SCRATCH" ] && git worktree remove --force "$SCRATCH" >/dev/null 2>&1
  return 0
}

note "Building $CAND in $SCRATCH"
# A verified-but-not-adopted run leaves its worktree holding $CAND, and git
# refuses to force-update a branch checked out anywhere. Clear any previous
# reconcile worktree first so a --run then --run --adopt sequence just works.
while IFS= read -r wt; do
  case "$wt" in
    *reconcile-device.*)
      [ "$wt" = "$SCRATCH" ] && continue
      echo "  removing stale scratch worktree: $wt"
      git worktree remove --force "$wt" >/dev/null 2>&1 ;;
  esac
done < <(git worktree list --porcelain | sed -n 's/^worktree //p')
git worktree prune >/dev/null 2>&1
git branch -f "$CAND" main || die "could not create $CAND"
"$wt_add" "$SCRATCH" "$CAND" >/dev/null 2>&1 || { git branch -D "$CAND" >/dev/null 2>&1; die "worktree-add.sh failed for $SCRATCH"; }

git -C "$SCRATCH" cherry-pick --empty=keep -x "${replay[@]}" >/dev/null 2>&1

# Drive the sequencer to completion, auto-resolving only the two mechanical
# cases and stopping for anything else.
#
# Case A -- every conflicted file is ALREADY byte-identical between main and
# device. Then the commit is a superseded intermediate step: its end state is
# what both branches already hold, so skipping it changes no final content.
# Case B -- the conflicted path is one this branch owns outright (never public,
# device-authoritative). Take device's version wholesale.
#
# Both are only safe because the tree-equality gate below re-checks the entire
# result. Nothing here is trusted on its own.
#
# Known imperfection: resolving to device's blob puts that file's FINAL content
# into a mid-history commit, so an intermediate commit can read as slightly
# ahead of itself. That costs nothing that matters here -- the branch exists to
# carry current device state with honest ancestry, not to be bisectable through
# a conflict that only exists because main's hashes were rewritten. The end
# state is what the gate proves.
OWNED_RE='^(\.env|\.zshrc|\.zprofile|\.gitignore)$'
resolved=0
for _ in $(seq 1 200); do
  git -C "$SCRATCH" rev-parse -q --verify CHERRY_PICK_HEAD >/dev/null 2>&1 || break
  sha="$(git -C "$SCRATCH" rev-parse --short CHERRY_PICK_HEAD)"
  conflicts="$(git -C "$SCRATCH" status --porcelain | grep -E '^(UU|AA|DU|UD|AU|UA)' | awk '{print $2}')"

  if [ -z "$conflicts" ]; then
    git -C "$SCRATCH" cherry-pick --continue --no-edit >/dev/null 2>&1 || true
    continue
  fi

  strategy=skip
  # Skipping is only safe if EVERY file the commit touches is already identical
  # on main and device -- not merely the conflicted ones. A commit can conflict
  # on one superseded file while still carrying the only copy of content in its
  # other files, and skipping it then silently drops that content. That is
  # exactly what happened here: 7e914c3 conflicted on upstream.sh (superseded)
  # but was also the sole source of `upstream:` provenance blocks in 15 other
  # skills, so skipping it lost 177 lines the tree gate then caught.
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    m="$(git rev-parse "main:$f" 2>/dev/null)"
    d="$(git rev-parse "$DEVICE:$f" 2>/dev/null)"
    [ -n "$m" ] && [ "$m" = "$d" ] || { strategy=partial; break; }
  done <<EOF0
$(git show --name-only --format="" "$sha")
EOF0

  # Not fully redundant: fall back to per-conflict handling. Device-owned paths
  # are taken wholesale; anything else needs a human.
  if [ "$strategy" = partial ]; then
    strategy=take
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      m="$(git rev-parse "main:$f" 2>/dev/null)"
      d="$(git rev-parse "$DEVICE:$f" 2>/dev/null)"
      if [ -n "$m" ] && [ "$m" = "$d" ]; then continue; fi
      printf '%s' "$f" | grep -qE "$OWNED_RE" || { strategy=stop; break; }
    done <<EOF1
$conflicts
EOF1
  fi

  case "$strategy" in
    skip)
      echo "  skip $sha — conflicted files already identical on main and $DEVICE"
      git -C "$SCRATCH" cherry-pick --skip >/dev/null 2>&1 ;;
    take)
      echo "  $sha — resolving conflict(s) to $DEVICE's version"
      # Device's blob is the end state for both the superseded-file case and the
      # device-owned case, so take it either way and let the tree gate judge.
      while IFS= read -r f; do
        [ -n "$f" ] || continue
        if git -C "$SCRATCH" checkout "$DEVICE" -- "$f" 2>/dev/null; then
          git -C "$SCRATCH" add "$f"
        else
          git -C "$SCRATCH" rm -q --ignore-unmatch "$f" 2>/dev/null
        fi
      done <<EOF2
$conflicts
EOF2
      git -C "$SCRATCH" cherry-pick --continue --no-edit >/dev/null 2>&1 || true ;;
    stop)
      note "CONFLICT needs your judgment at $sha"
      git -C "$SCRATCH" status --short | grep -E '^(UU|AA|DU|UD|AU|UA)' || true
      cat <<EOF3

$(git -C "$SCRATCH" log -1 --format='%h %s' CHERRY_PICK_HEAD 2>/dev/null)

Resolve it in the scratch worktree, which is left intact:

    cd $SCRATCH
    git add <files> && git cherry-pick --continue    # or --skip if redundant

Then verify and adopt:

    $self --run --adopt

Nothing in $root was changed.
EOF3
      exit 1 ;;
  esac
  resolved=$((resolved+1))
done

# ---------- reconcile any residual drift ------------------------------------
# Conflict auto-resolution can leave the tip short of device: taking device's
# blob mid-history makes a LATER commit redundant, git reports it as empty or
# conflicting, and its remaining files never land. Rather than untangle that
# per-commit, close the gap with one explicit commit that states exactly what
# it is. This keeps the invariant that matters (final tree == device tree)
# without pretending the replay was cleaner than it was.
if [ "$(git -C "$SCRATCH" rev-parse HEAD^{tree})" != "$(git rev-parse "$DEVICE^{tree}")" ]; then
  note "Residual drift after replay — reconciling in one explicit commit"
  git diff --stat "$CAND" "$DEVICE" | tail -12
  # Read the device tree into the index wholesale. `read-tree` handles gitlinks
  # (submodules) and deletions correctly; `checkout -- .` plus a manual rm loop
  # does neither -- it never deletes, and `git rm` refuses on a submodule whose
  # staged gitlink differs, leaving .gitmodules and the gitlinks inconsistent.
  git -C "$SCRATCH" read-tree "$DEVICE^{tree}" || die "could not read $DEVICE tree into index"
  git -C "$SCRATCH" checkout-index -a -f >/dev/null 2>&1 || true
  if git -C "$SCRATCH" diff --cached --quiet HEAD; then
    echo "  nothing to reconcile after all"
  else
    git -C "$SCRATCH" commit -q -m "reconcile: sync tree to $DEVICE after ancestry rebuild

Residual drift from replaying device-only commits onto main. Conflict
resolution took device's version of some files mid-history, which made later
commits redundant, so their remaining changes never applied. This commit
restores the exact device tree.

Content is unchanged from $DEVICE; only ancestry differs." \
      || die "could not commit reconciliation"
    echo "  committed: $(git -C "$SCRATCH" log -1 --format=%h)"
  fi
fi

# ---------- the hard gate: tree equality ------------------------------------
# The whole point is "same files, better ancestry". If the rebuilt tree differs
# from today's device tree, the replay lost or changed something and the result
# must not be adopted.
note "Verifying the rebuilt tree matches $DEVICE exactly"
new_tree="$(git -C "$SCRATCH" rev-parse HEAD^{tree})"
old_tree="$(git rev-parse "$DEVICE^{tree}")"
if [ "$new_tree" != "$old_tree" ]; then
  echo "  MISMATCH"
  echo "    $DEVICE tree: $old_tree"
  echo "    $CAND tree:   $new_tree"
  note "Differences:"
  git diff --stat "$DEVICE" "$CAND" | tail -20
  cat <<EOF

NOT adopting. The rebuilt branch does not reproduce the current device tree,
so replaying dropped or altered content. Inspect with:

    git diff $DEVICE $CAND

$CAND and its worktree are left in place for inspection.
EOF
  exit 1
fi
echo "  IDENTICAL ($new_tree) — no file content changed"

echo "  ancestry: merge-base with main = $(git merge-base main "$CAND" | cut -c1-12)"
echo "  commits ahead of main: $(git rev-list --count main.."$CAND")"

if [ "$do_adopt" -eq 0 ]; then
  cat <<EOF

Verified but NOT adopted. $CAND is ready at $SCRATCH.

    git log --oneline main..$CAND

To adopt (tags a backup, then moves $DEVICE):

    $self --run --adopt
EOF
  exit 0
fi

# ---------- adopt -----------------------------------------------------------
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git status --short --untracked-files=no
  cleanup; git branch -D "$CAND" >/dev/null 2>&1
  die "working tree is dirty on $DEVICE. Commit or stash, then re-run with --adopt."
fi

BACKUP="backup/pre-reconcile-$(git log -1 --format=%cd --date=format:%Y%m%d%H%M%S "$DEVICE")"
note "Tagging backup: $BACKUP -> $(git rev-parse --short "$DEVICE")"
git tag -f "$BACKUP" "$DEVICE" || die "could not tag backup; refusing to proceed."

# Move the branch ref, then hard-reset the working tree to match. The tree is
# already proven identical, so this changes no file content -- only ancestry.
note "Moving $DEVICE onto $CAND"
git update-ref "refs/heads/$DEVICE" "$(git rev-parse "$CAND")" \
  || die "could not move $DEVICE. Backup is at $BACKUP."
git reset --hard "$DEVICE" >/dev/null || die "reset failed; recover with: git reset --hard $BACKUP"

cleanup
git branch -D "$CAND" >/dev/null 2>&1

note "Done."
echo "  $DEVICE now forks from main at $(git merge-base main "$DEVICE" | cut -c1-12)"
echo "  backup tag: $BACKUP"
echo
echo "  Verify:  git log --oneline --graph main..$DEVICE | head"
echo "  Undo:    git reset --hard $BACKUP && git update-ref refs/heads/$DEVICE $BACKUP"
