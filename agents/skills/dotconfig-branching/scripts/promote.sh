#!/usr/bin/env bash
# promote.sh — move vetted, portable config from this device's branch to main.
#
# Implements the promotion flow in SKILL.md. The device branch is where you
# live; main is the public export. Promotion is per-path and deliberate: it
# cherry-picks file contents, never merges the branch, because a merge would
# drag work config onto a public remote.
#
# Usage:
#   promote.sh <path> [<path>...]     stage those paths from the device branch
#   promote.sh --dry-run <path>...    show what would change, touch nothing
#
# Stops before `git push` and prints the command. Pushing stays a human action.
set -uo pipefail

die() { printf '\n%s\n' "$*" >&2; exit 1; }
note() { printf '\n\033[1m%s\033[0m\n' "$*"; }

root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "promote.sh: not inside a git repo"
cd "$root" || die "promote.sh: cannot cd to $root"

dry_run=0
paths=()
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) dry_run=1 ;;
    -h|--help) sed -n '2,13p' "$0" | sed -e 's/^#$//' -e 's/^# //'; exit 0 ;;
    -*) die "promote.sh: unknown flag: $arg" ;;
    *) paths+=("$arg") ;;
  esac
done
[ "${#paths[@]}" -gt 0 ] || die "promote.sh: name at least one path to promote. See --help."

DEVICE="$(git rev-parse --abbrev-ref HEAD)"
[ "$DEVICE" != "main" ] || die "promote.sh: already on main. Run this from your device branch."
[ "$DEVICE" != "HEAD" ] || die "promote.sh: detached HEAD. Switch to your device branch first."

# Step 0: a dirty tree here would be silently carried onto main by the switch.
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git status --short --untracked-files=no
  die "promote.sh: working tree is dirty. Commit to $DEVICE (or stash) first."
fi

# Everything promoted must exist on the device branch.
for p in "${paths[@]}"; do
  git cat-file -e "$DEVICE:$p" 2>/dev/null \
    || git ls-tree -d --name-only "$DEVICE" -- "$p" | grep -q . \
    || die "promote.sh: '$p' does not exist on $DEVICE."
done

if [ "$dry_run" -eq 1 ]; then
  note "Dry run — would promote from $DEVICE to main:"
  printf '  %s\n' "${paths[@]}"
  note "Diff against main (main <- $DEVICE):"
  git diff --stat main.."$DEVICE" -- "${paths[@]}" || true
  echo
  echo "Nothing was changed."
  exit 0
fi

note "Promoting ${#paths[@]} path(s) from $DEVICE to main"

# Step 1: main, fast-forward only. A non-ff means main moved underneath us and
# needs a human decision, not a merge commit invented here.
git switch main >/dev/null 2>&1 || die "promote.sh: could not switch to main."
restore_device() { git switch "$DEVICE" >/dev/null 2>&1 || true; }

if git remote get-url origin >/dev/null 2>&1; then
  if ! git pull --ff-only origin main; then
    restore_device
    die "promote.sh: 'git pull --ff-only origin main' failed. Reconcile main by hand, then retry. Back on $DEVICE."
  fi
else
  echo "  (no origin remote; skipping pull)"
fi

# Step 2: take file contents, not history. Per-path, never a branch merge.
if ! git checkout "$DEVICE" -- "${paths[@]}"; then
  git restore --staged --worktree . 2>/dev/null || true
  restore_device
  die "promote.sh: checkout of the named paths failed. Back on $DEVICE, nothing staged."
fi

if git diff --cached --quiet; then
  restore_device
  note "Nothing to promote — main already matches $DEVICE for those paths."
  exit 0
fi

note "Staged for main:"
git diff --cached --stat

# Step 3: vet. vet.sh takes no arguments and reads git diff --cached, which is
# why staging happens above. This is the gate: a public repo gets nothing that
# has not passed it.
vet="$root/agents/skills/dotconfig-branching/scripts/vet.sh"
[ -x "$vet" ] || die "promote.sh: vet.sh missing or not executable at $vet"

note "Vetting staged changes"
if ! "$vet"; then
  note "ABORTED — vet.sh found problems. Unstaging and returning to $DEVICE."
  git restore --staged --worktree . 2>/dev/null || true
  restore_device
  die "promote.sh: nothing was committed. Fix the findings on $DEVICE, then retry."
fi

# Step 4: commit on main. Push is deliberately NOT run.
note "Commit message for main (empty message aborts)"
if ! git commit; then
  git restore --staged --worktree . 2>/dev/null || true
  restore_device
  die "promote.sh: commit aborted. Nothing changed. Back on $DEVICE."
fi
promoted="$(git rev-parse --short HEAD)"

# Step 5: back to the device branch and rebase onto the new main, so the device
# branch stays a superset of what is public.
git switch "$DEVICE" >/dev/null 2>&1 || die "promote.sh: committed $promoted on main but could not switch back to $DEVICE."
if ! git rebase main; then
  die "promote.sh: committed $promoted on main, but rebasing $DEVICE onto main hit conflicts. Resolve, then 'git rebase --continue'."
fi

note "Done. $promoted is on main, and $DEVICE is rebased onto it."
cat <<EOF

Not pushed. Review first:

    git -C "$root" log --oneline origin/main..main
    git -C "$root" show $promoted

Then push yourself:

    git -C "$root" push origin main
EOF
