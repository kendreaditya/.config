#!/usr/bin/env bash
# vet.sh — audit STAGED changes for anything unsafe to publish to a public repo.
# Exit 0 = clear to push. Exit 1 = findings that need review.
set -uo pipefail
root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "vet.sh: not inside a git repo" >&2; exit 2; }
[ -n "$root" ] || { echo "vet.sh: could not resolve repo root" >&2; exit 2; }
cd "$root" || exit 2

findings=0
report() { printf '\n[%s] %s\n' "$1" "$2"; }

staged=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "$staged" ]; then echo "Nothing staged."; exit 0; fi

# 1. gitignored files that were force-added
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if git check-ignore -q "$f"; then
    report FAIL "gitignored file is staged (force-added?): $f"; findings=1
  fi
done <<< "$staged"

# 2. absolute home paths — break portability and leak usernames
if hits=$(git diff --cached -U0 | grep -nE '^\+.*/(Users|home)/[A-Za-z0-9_.-]+' | grep -vE '^[0-9]+:\+\+\+'); then
  report WARN "absolute home paths (use \$HOME or relative):"; echo "$hits" | cut -c1-160; findings=1
fi

# 3. internal hostnames
if hits=$(git diff --cached -U0 | grep -niE '^\+.*(anduril|lattice|ghe\.|armory|bifrost|teleport|okta|andurildev)' | grep -vE '^[0-9]+:\+\+\+'); then
  report FAIL "internal infrastructure references:"; echo "$hits" | cut -c1-160; findings=1
fi

# 4. credential-shaped strings
if hits=$(git diff --cached -U0 | grep -nE '^\+.*(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[bpa]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|eyJ[A-Za-z0-9_-]{20,}\.)' | grep -vE '^[0-9]+:\+\+\+'); then
  report FAIL "possible credential material:"; echo "$hits" | cut -c1-160; findings=1
fi

# 5. git-crypt fail-open check
if ! ls .git/git-crypt/keys >/dev/null 2>&1; then
  report WARN "git-crypt is LOCKED — encrypted paths would commit as PLAINTEXT."
  report WARN "The .githooks/pre-commit hook blocks this; do not bypass with --no-verify."
fi

if [ "$findings" -eq 0 ]; then
  echo "PASS — no findings in $(wc -l <<< "$staged" | tr -d ' ') staged file(s)."
else
  echo
  echo "Review the findings above before pushing to a PUBLIC repo."
fi
exit "$findings"
