#!/usr/bin/env bash
# promote.sh — move vetted, portable config from this device's branch to main.
#
# Implements the promotion flow in SKILL.md. The device branch is where you
# live, permanently, in this working directory — this script never switches
# it to another branch. `main` lives in its own linked worktree (set up once
# via worktree-add.sh), used only for staging/vetting/committing promotions.
# Promotion is per-path and deliberate: it cherry-picks file contents, never
# merges the branch, because a merge would drag work config onto a public
# remote.
#
# Usage:
#   promote.sh <path> [<path>...]     stage those paths from the device branch
#   promote.sh -m <msg> <path>...     non-interactive commit message
#   promote.sh --dry-run <path>...    show what would change, touch nothing
#
# Stops before `git push` and prints the command. Pushing stays a human action.
set -uo pipefail

die() { printf '\n%s\n' "$*" >&2; exit 1; }
note() { printf '\n\033[1m%s\033[0m\n' "$*"; }

root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "promote.sh: not inside a git repo"
# Absolute path to this script, resolved BEFORE the cd below -- --help does
# `sed "$self"`, which fails on a relative invocation once the cwd moves.
self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
cd "$root" || die "promote.sh: cannot cd to $root"

dry_run=0
msg=""
paths=()
want_msg=0
for arg in "$@"; do
  if [ "$want_msg" -eq 1 ]; then msg="$arg"; want_msg=0; continue; fi
  case "$arg" in
    --dry-run|-n) dry_run=1 ;;
    -m|--message) want_msg=1 ;;
    -h|--help) sed -n '2,18p' "$self" | sed -e 's/^#$//' -e 's/^# //'; exit 0 ;;
    -*) die "promote.sh: unknown flag: $arg" ;;
    *) paths+=("$arg") ;;
  esac
done
[ "$want_msg" -eq 0 ] || die "promote.sh: -m needs a message argument."
[ "${#paths[@]}" -gt 0 ] || die "promote.sh: name at least one path to promote. See --help."

DEVICE="$(git rev-parse --abbrev-ref HEAD)"
[ "$DEVICE" != "main" ] || die "promote.sh: this is main's worktree. Run promote.sh from your device branch's worktree."
[ "$DEVICE" != "HEAD" ] || die "promote.sh: detached HEAD. Switch to your device branch first."

# Everything promoted must exist on the device branch.
for p in "${paths[@]}"; do
  git cat-file -e "$DEVICE:$p" 2>/dev/null \
    || git ls-tree -d --name-only "$DEVICE" -- "$p" | grep -q . \
    || die "promote.sh: '$p' does not exist on $DEVICE."
done

# Locate main's linked worktree. It's a standing fixture, set up once via
# worktree-add.sh — promote.sh doesn't create it on the fly.
main_wt=""
while IFS= read -r line; do
  case "$line" in
    "worktree "*) candidate="${line#worktree }" ;;
    "branch refs/heads/main") main_wt="$candidate" ;;
  esac
done < <(git worktree list --porcelain)
[ -n "$main_wt" ] || die "promote.sh: no linked worktree checked out on 'main'. Run: agents/skills/dotconfig-branching/scripts/worktree-add.sh <path> main"
[ -d "$main_wt" ] || die "promote.sh: main worktree registered at $main_wt but the directory is missing."

if [ "$dry_run" -eq 1 ]; then
  note "Dry run — would promote from $DEVICE to main ($main_wt):"
  printf '  %s\n' "${paths[@]}"
  note "Diff against main (main <- $DEVICE):"
  git diff --stat main.."$DEVICE" -- "${paths[@]}" || true
  echo
  echo "Nothing was changed."
  exit 0
fi

# Step 5 cherry-picks the promotion commit back onto this worktree, which
# needs a clean tree — same requirement the old in-place-switch version had,
# just for a different reason now (nothing to switch away from, but a dirty
# tree still blocks a cherry-pick). Checked here, after the dry-run early
# exit, since a dry run touches nothing and shouldn't require a clean tree.
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git status --short --untracked-files=no
  die "promote.sh: working tree is dirty on $DEVICE. Commit or stash first."
fi

note "Promoting ${#paths[@]} path(s) from $DEVICE to main ($main_wt)"

# Step 1: main's worktree, fast-forward only. A non-ff means main moved
# underneath us and needs a human decision, not a merge commit invented here.
if git -C "$main_wt" remote get-url origin >/dev/null 2>&1; then
  if ! git -C "$main_wt" pull --ff-only origin main; then
    die "promote.sh: 'git pull --ff-only origin main' failed in $main_wt. Reconcile by hand, then retry."
  fi
else
  echo "  (no origin remote; skipping pull)"
fi

# Step 2: take file contents, not history. Per-path, never a branch merge.
if ! git -C "$main_wt" checkout "$DEVICE" -- "${paths[@]}"; then
  git -C "$main_wt" restore --staged --worktree . 2>/dev/null || true
  die "promote.sh: checkout of the named paths into $main_wt failed. Nothing staged there."
fi

if git -C "$main_wt" diff --cached --quiet; then
  note "Nothing to promote — main already matches $DEVICE for those paths."
  exit 0
fi

note "Staged in $main_wt for main:"
git -C "$main_wt" diff --cached --stat

# Step 3: vet. vet.sh takes no arguments and reads git diff --cached against
# whatever repo/worktree it's run in, which is why it's invoked with cwd set
# to main's worktree — this is the gate: a public repo gets nothing that has
# not passed it.
vet="$root/agents/skills/dotconfig-branching/scripts/vet.sh"
[ -x "$vet" ] || die "promote.sh: vet.sh missing or not executable at $vet"

note "Vetting staged changes in $main_wt"
if ! (cd "$main_wt" && "$vet"); then
  note "ABORTED — vet.sh found problems. Unstaging in $main_wt."
  git -C "$main_wt" restore --staged --worktree . 2>/dev/null || true
  die "promote.sh: nothing was committed. Fix the findings on $DEVICE, then retry."
fi

# Step 4: commit in main's worktree. Push is deliberately NOT run.
if [ -n "$msg" ]; then
  note "Committing to main with the supplied message"
  if ! git -C "$main_wt" commit -m "$msg"; then
    git -C "$main_wt" restore --staged --worktree . 2>/dev/null || true
    die "promote.sh: commit failed in $main_wt. Nothing changed."
  fi
else
  note "Commit message for main (empty message aborts)"
  if ! git -C "$main_wt" commit; then
    git -C "$main_wt" restore --staged --worktree . 2>/dev/null || true
    die "promote.sh: commit aborted in $main_wt. Nothing changed."
  fi
fi
promoted="$(git -C "$main_wt" rev-parse --short HEAD)"

# Step 5: bring the promotion commit back onto the device branch (this
# worktree, still checked out on $DEVICE the entire time), so it stays a
# superset of what is public. A cherry-pick of just this one commit, not
# `git rebase main` -- main's root commit was rewritten by a past
# git-filter-repo history scrub (see AGENTS.md), so a full rebase replays
# device's entire history against unrelated commit objects and can hit
# unresolvable conflicts on git-crypt-encrypted binaries. The promoted
# commit's content came FROM $DEVICE (step 2's checkout), so applying it here
# is normally a no-op diff -- --empty=keep records that no-op commit instead
# of erroring, so $DEVICE's log stays an honest record of what's public.
if ! git cherry-pick --empty=keep -x "$promoted"; then
  die "promote.sh: committed $promoted on main, but cherry-picking it onto $DEVICE hit conflicts. Resolve, then 'git cherry-pick --continue'."
fi

note "Done. $promoted is on main ($main_wt), and $DEVICE has it cherry-picked in."
cat <<EOF

Not pushed. Review first:

    git -C "$main_wt" log --oneline origin/main..main
    git -C "$main_wt" show $promoted

Then push yourself:

    git -C "$main_wt" push origin main
EOF
