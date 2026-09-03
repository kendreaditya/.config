#!/usr/bin/env bash
# publish.sh — one command for the whole promote → vet → commit → push → sync cycle.
#
# promote.sh deliberately stops before `git push`, because publishing to a public
# repo should be a human decision. That's the right default for a first-time
# promotion, and it's friction you don't want on the tenth. publish.sh is the
# opt-in wrapper: same gate (it calls promote.sh, which calls vet.sh), plus the
# two steps promote.sh leaves to you — pushing main, and confirming the device
# branch ends up a superset of what's public.
#
# Run it from the DEVICE branch's worktree, naming paths to publish:
#
#   publish.sh agents/skills/foo agents/skills/bar
#   publish.sh -m "foo: add the thing" agents/skills/foo
#   publish.sh --dry-run agents/skills/foo      # delegates to promote.sh's dry run
#   publish.sh --no-push agents/skills/foo      # promote + sync, stop before push
#
# Nothing here bypasses vet.sh. If vet.sh fails, promote.sh unstages and aborts,
# and this script exits without pushing anything.
#
# On "rebase": this script does not rebase the device branch onto main, and does
# not need to -- since the 2026-09-03 reconciliation main is a strict ancestor of
# the device branch, so promote.sh's cherry-pick keeps device a superset and this
# script only verifies that. If `git merge-base main <device>` ever returns
# nothing again, that is the signature-stripped-root problem; run
# reconcile-device.sh rather than rebasing. See dotconfig-branching/SKILL.md.
set -uo pipefail

die()  { printf '\n%s\n' "$*" >&2; exit 1; }
note() { printf '\n\033[1m%s\033[0m\n' "$*"; }

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve $0 to an absolute path BEFORE cd'ing to the repo root -- --help does
# `sed "$0"`, and a relative invocation ("./publish.sh --help") breaks once the
# cwd moves.
self="$here/$(basename "${BASH_SOURCE[0]}")"
root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "publish.sh: not inside a git repo"
cd "$root" || die "publish.sh: cannot cd to $root"

do_push=1
promote_args=()
paths=()
want_msg=0
for arg in "$@"; do
  if [ "$want_msg" -eq 1 ]; then promote_args+=("$arg"); want_msg=0; continue; fi
  case "$arg" in
    --no-push)        do_push=0 ;;
    -n|--dry-run)     promote_args+=("$arg"); do_push=0 ;;
    -m|--message)     promote_args+=("$arg"); want_msg=1 ;;
    -h|--help)        sed -n '2,27p' "$self" | sed -e 's/^#$//' -e 's/^# //'; exit 0 ;;
    -*)               die "publish.sh: unknown flag: $arg" ;;
    *)                promote_args+=("$arg"); paths+=("$arg") ;;
  esac
done
[ "$want_msg" -eq 0 ] || die "publish.sh: -m needs a message argument."
[ "${#paths[@]}" -gt 0 ] || die "publish.sh: name at least one path to publish. See --help."

DEVICE="$(git rev-parse --abbrev-ref HEAD)"
[ "$DEVICE" != "main" ] || die "publish.sh: this is main's worktree. Run it from your device branch."
[ "$DEVICE" != "HEAD" ] || die "publish.sh: detached HEAD. Switch to your device branch first."

# Locate main's linked worktree the same way promote.sh does, so the two agree
# on which directory is main even if it isn't the conventional ~/.config-main.
main_wt=""
while IFS= read -r line; do
  case "$line" in
    "worktree "*)            candidate="${line#worktree }" ;;
    "branch refs/heads/main") main_wt="$candidate" ;;
  esac
done < <(git worktree list --porcelain)
[ -n "$main_wt" ] || die "publish.sh: no linked worktree on 'main'. Run worktree-add.sh <path> main"

# Step 1: promote. This is the gate -- it pulls main --ff-only, checks out the
# named paths, runs vet.sh, commits, and cherry-picks back onto $DEVICE. A
# nonzero exit means vet.sh found something or the commit was aborted; either
# way nothing was published and there is nothing to undo here.
promote="$here/promote.sh"
[ -x "$promote" ] || die "publish.sh: promote.sh missing or not executable at $promote"
note "Promoting to main via promote.sh"
"$promote" "${promote_args[@]}" || die "publish.sh: promote.sh did not complete. Nothing pushed."

# A dry run stops here: promote.sh touched nothing, so there is no commit to
# push and no superset to verify.
if [ "$do_push" -eq 0 ] && printf '%s\n' "${promote_args[@]}" | grep -qxE '\-n|--dry-run'; then
  exit 0
fi

# Step 2: push main. Note the direction -- `git -C "$main_wt" push` pushes
# main's HEAD from main's own worktree. Never push from the device worktree,
# whose HEAD is the private branch.
if [ "$do_push" -eq 1 ]; then
  if ! git -C "$main_wt" remote get-url origin >/dev/null 2>&1; then
    note "No origin remote; skipping push."
  else
    ahead="$(git -C "$main_wt" rev-list --count origin/main..main 2>/dev/null || echo 0)"
    if [ "$ahead" -eq 0 ]; then
      note "origin/main already has everything; nothing to push."
    else
      note "Pushing $ahead commit(s) to origin/main"
      git -C "$main_wt" log --oneline origin/main..main
      git -C "$main_wt" push origin main || die "publish.sh: push failed. main is committed locally; retry the push."
    fi
  fi
else
  note "--no-push: main is committed locally but not pushed. Push with:"
  echo "    git -C \"$main_wt\" push origin main"
fi

# Step 3: verify the device branch is a superset of public for the promoted
# paths. promote.sh cherry-picked the promotion commit here, which creates a
# COPY of main's commit with a new hash -- so main stops being a strict ancestor
# by exactly one commit per promotion, even though the content matches. That is
# inherent to cherry-pick-based promotion and harmless: what matters is that no
# promoted path differs. Ancestry drift is reported, not treated as an error;
# reconcile-device.sh re-establishes strict-ancestor status when you want it.
note "Verifying $DEVICE is a superset of main for the promoted paths"
drift=0
for p in "${paths[@]}"; do
  if ! git diff --quiet main.."$DEVICE" -- "$p"; then
    printf '  DRIFT  %s\n' "$p"
    drift=1
  else
    printf '  ok     %s\n' "$p"
  fi
done

behind="$(git rev-list --count "$DEVICE..main" 2>/dev/null || echo 0)"
if [ "$behind" -gt 0 ]; then
  # main being "ahead by hash" is expected and benign: promote.sh cherry-picks
  # its commit back here, which creates a copy with a new hash, so main stops
  # being a strict ancestor by one commit per promotion.
  #
  # Do NOT try to detect a real problem by comparing every file main tracks --
  # device legitimately holds richer versions of many of them (private config,
  # extra provenance), so that check is all false positives. And `git cherry`
  # can't help either: a cherry-picked promotion's whole-commit patch never
  # matches, because main's copy touches only the promoted paths while device's
  # sits on a tree that also carries private config. The promoted-path loop
  # above is the check that actually means something; this is just a note.
  printf '\n  note: main is %s commit(s) ahead of %s by hash — expected, since\n' "$behind" "$DEVICE"
  printf '        promote.sh cherry-picks its commit back as a new copy. The\n'
  printf '        promoted paths above are what must match, and they do.\n'
  printf '        To restore strict-ancestor status: %s/reconcile-device.sh --run\n' "$here"
fi
if [ "$drift" -eq 1 ]; then
  cat <<EOF

Those paths differ between main and $DEVICE after promotion. That usually means
the working tree changed between promote.sh's checkout and now, or a path was
only partly promoted. Inspect with:

    git diff main..$DEVICE -- <path>
EOF
  exit 1
fi

note "Done."
git -C "$main_wt" log --oneline -1
