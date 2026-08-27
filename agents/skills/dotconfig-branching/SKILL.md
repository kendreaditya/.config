---
name: dotconfig-branching
description: "Manage the PUBLIC ~/.config dotfiles repo using a per-device local branch as the default working branch, promoting only vetted changes to origin/main. Use when committing or pushing anything in ~/.config, when setting up dotfiles on a new machine, when unsure whether a config change is safe to publish, or when work/personal config needs to stay off GitHub. Triggers: 'dotconfig', 'dotfiles', 'push my config', 'commit my config', 'is this safe to push', 'new machine setup', 'device branch', 'promote to main', 'private config'."
---

# dotconfig-branching

Workflow for `~/.config` — a **public** GitHub repo (`kendreaditya/.config`) that
also holds work-specific and machine-specific configuration.

## The core constraint

**GitHub visibility is per-repository, not per-branch.** There is no such thing
as a private branch of a public repo. Anyone can `git clone --mirror` and read
every ref that has been pushed. Therefore:

> A branch is private **only** for as long as it is never pushed.

This skill's entire job is to make "never pushed" the *default* state, and
publishing an explicit, deliberate act.

## Model: device branch is home, `main` is the export target

```
device/<DEVICE-NAME>   ← you live here. NEVER pushed. Holds everything,
                         including work + machine-local config.
main                   ← tracks origin/main. Only vetted, portable,
                         non-sensitive config. This is the public face.
```

Branch name comes from the device's own hostname, so it is self-documenting and
collision-free across machines:

```bash
git rev-parse --abbrev-ref HEAD          # where am I?
scutil --get LocalHostName               # macOS device name
hostname -s                              # Linux/portable
```

Known devices: `MAC-DT4JNF66GH` (Anduril work laptop), `adityas-macbook-pro-1`
(personal, gold standard), `adityas-macbook-pro-2`, `dev-x86-gov-akendre`
(Ubuntu dev server).

## Default behavior

1. **Commit to the device branch.** No safety analysis needed — it never leaves
   the machine. Commit freely and often.
2. **Never `git push` from a device branch.** If asked to push while on one,
   stop and run the promotion flow instead.
3. **Never `git push --all` or `git push --mirror` in this repo.** These ignore
   the "don't push device branches" rule and would publish everything at once.

## Promotion flow: device branch → `origin/main`

Use when a change is genuinely portable and safe to publish. Run
`scripts/promote.sh` for the guided version, or by hand:

```bash
# 0. Start clean. Uncommitted work must be stashed or committed first.
git status --porcelain          # must be empty
DEVICE="$(git rev-parse --abbrev-ref HEAD)"

# 1. Move to main and refresh from origin.
git switch main
git pull --ff-only origin main

# 2. Bring over ONLY the vetted paths. Cherry-pick a commit, or checkout
#    specific files from the device branch — never merge the whole branch.
git checkout "$DEVICE" -- <specific/safe/path> ...
#   or: git cherry-pick <sha>       (if the commit is already clean/isolated)

# 3. VET before committing (see checklist below).
git diff --cached --name-only

# 4. Commit and publish.
git commit
git push origin main

# 5. Rebase the device branch onto the new main so history stays linear
#    and the promoted change is not duplicated.
git switch "$DEVICE"
git rebase main
```

**Why `git checkout <branch> -- <path>` rather than `git merge`:** merging a
device branch into `main` drags along *every* commit on it, including work
config and machine-local state. Path-scoped checkout is allowlist-shaped —
you name exactly what becomes public. Default-deny beats default-allow when the
failure mode is a public credential leak.

## Vetting checklist — required before any push to main

Never promote without checking all of these:

```bash
# 1. Nothing gitignored is being force-added.
git diff --cached --name-only | while read -r f; do
  git check-ignore -q "$f" && echo "IGNORED FILE STAGED: $f"
done

# 2. No absolute home paths (breaks on other machines & leaks usernames).
git diff --cached -U0 | grep -nE '^\+.*/(Users|home)/[a-z]+' 

# 3. No internal hostnames.
git diff --cached -U0 | grep -niE '^\+.*(anduril|lattice|ghe\.|armory|bifrost|teleport|okta)'

# 4. No credential-shaped strings.
git diff --cached -U0 | grep -nE '^\+.*(sk-[A-Za-z0-9]{20,}|gh[pousr]_|xox[bp]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|eyJ[A-Za-z0-9_-]{20,})'

# 5. git-crypt is not silently failing open (the pre-commit hook enforces this,
#    but confirm the key is actually installed).
ls .git/git-crypt/keys >/dev/null 2>&1 || echo "WARNING: git-crypt LOCKED"
```

Items 1–4 producing no output means clear to proceed. The `.githooks/pre-commit`
hook enforces the git-crypt case automatically; keep `core.hooksPath=.githooks`
configured (`git config core.hooksPath .githooks`).

## What belongs where

**Promote to `main` (portable, non-sensitive):**
- Skills with no internal references; `scripts/` and their symlinks (relative)
- `nvim/`, `tmux/`, shell config that is not host-specific
- `.gitignore`, `.githooks/`, `AGENTS.md`, `CLAUDE.md`, `README.md`
- Cross-platform `setup-*.sh` logic

**Keep on the device branch only:**
- `claude/settings.json` when it carries a non-public API base URL, telemetry
  endpoint, or org plugin list
- Work shell integration (e.g. the `dx env` block in `.zshrc`)
- `bunnylol/config.toml` while it is org-specific shortcuts
- Anything naming internal infrastructure

**Never commit anywhere (gitignored):**
- `.env` (git-crypt; fails open when locked — see hook), `.env.enc`
- `argocd/`, `confluence-cli/`, `wandb/`, `cagent/`
- `tailscale-official-proxy/` (node private key), skill `state/` dirs

## New machine setup

```bash
git clone https://github.com/kendreaditya/.config.git ~/.config
cd ~/.config
git config core.hooksPath .githooks           # enable the secret guard
git switch -c "device/$(hostname -s)"         # or scutil --get LocalHostName
```

If `~/.config` **already exists and is non-empty** — which is the case on the
Anduril dev server, where `dx` owns `~/.config/dx/` — do not clone over it. Back
it up, clone, then restore the pre-existing local files as the first commit on
the device branch. `scripts/adopt-existing.sh` does this.

## Notes

- `git push` defaults to `simple` (current branch → its upstream). Device
  branches must have **no upstream** so an accidental bare `push` fails loudly
  rather than publishing. Verify: `git config --get branch.<device>.remote`
  should be empty.
- Rebasing the device branch onto `main` (step 5) keeps history linear and
  avoids re-promoting the same change twice.
- The device branch is a working branch, not a backup. It exists on exactly one
  machine and is never pushed — so it is **not** disaster recovery. Back up
  secrets (e.g. the git-crypt key) out of band.
