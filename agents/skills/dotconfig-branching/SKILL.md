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

Known devices: `MAC-DT4JNF66GH` (work laptop), `adityas-macbook-pro-1`
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

Use when a change is genuinely portable and safe to publish.

```bash
scripts/promote.sh <path> [<path>...]     # guided; vets, commits, does NOT push
scripts/promote.sh --dry-run <path>...    # show what would move, change nothing
```

`promote.sh` runs the flow below, refuses to start from a dirty tree or from
`main`, aborts and returns you to the device branch if `vet.sh` finds anything,
and stops before `git push` — printing the command instead. By hand:

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

# 3. VET before committing. vet.sh reads the staged diff; exit 0 = clear.
scripts/vet.sh

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

## Vetting — required before any push to main

`scripts/vet.sh` is the check. It takes no arguments, reads `git diff --cached`,
and exits 0 for clear / 1 for findings / 2 if it cannot resolve the repo. Stage
first, then run it:

```bash
git add <paths>
scripts/vet.sh
```

It reports on five things:

1. **Gitignored files that were force-added** (FAIL) — an `-f` add defeats every
   ignore rule protecting this repo.
2. **Absolute home paths** (WARN) — break on other machines and leak the
   username. Use `$HOME` or a relative path.
3. **Internal hostnames** (FAIL) — org infrastructure references have no place
   in a public repo.
4. **Credential-shaped strings** (FAIL) — token prefixes, AWS key ids, PEM
   private-key headers, JWTs.
5. **git-crypt locked** (WARN) — when the key is missing the clean filter fails
   *open*, so encrypted paths would commit as plaintext.

Do not re-implement these checks inline; call `vet.sh` so there is one
definition to keep correct. `.githooks/pre-commit` independently enforces case 5
at commit time — keep `core.hooksPath=.githooks` configured
(`git config core.hooksPath .githooks`) and never bypass it with `--no-verify`.

## What belongs where

**Promote to `main` (portable, non-sensitive):**
- Skills with no internal references; `scripts/` and their symlinks (relative)
- `nvim/`, `tmux/`, shell config that is not host-specific
- `.gitignore`, `.githooks/`, `AGENTS.md`, `CLAUDE.md`, `README.md`
- Cross-platform `setup-*.sh` logic

**Keep on the device branch only:**
- `agents/harness/claude/settings.json` when it carries a non-public API base
  URL, telemetry endpoint, or org plugin list
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
git-crypt unlock /path/to/git-crypt.key       # else encrypted paths stay ciphertext
```

If `~/.config` **already exists and is non-empty** — which is the case on the
work dev server, where a managed tool owns `~/.config/<tool>/` — do not clone
over it. Adopt it instead:

```bash
mv ~/.config ~/.config-preexisting            # keep the originals, do not delete
git clone https://github.com/kendreaditya/.config.git ~/.config
cd ~/.config
git config core.hooksPath .githooks
git switch -c "device/$(hostname -s)"

# Copy the pre-existing local files back in, then commit them to the device
# branch — never to main, since that is where machine-local state belongs.
rsync -a --ignore-existing ~/.config-preexisting/ ~/.config/
git status --short                            # review before staging anything
git add <the paths you actually want tracked>
git commit -m "device: adopt pre-existing config from this machine"
```

Review `git status` by hand rather than `git add -A`: the pre-existing tree is
exactly where a managed tool's credentials are likely to be. Keep
`~/.config-preexisting/` until the new tree is confirmed working.

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
