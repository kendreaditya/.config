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

## Model: device branch is home, `main` is a linked worktree

```
device/<DEVICE-NAME>   ← you live here, permanently, in ~/.config. NEVER
                         pushed. Holds everything, including work + machine-
                         local config. This checkout is never switched away
                         from this branch.
main                   ← tracks origin/main. Only vetted, portable,
                         non-sensitive config. This is the public face. Lives
                         in its own linked git worktree (e.g. ~/.config-main),
                         used only for staging and committing promotions —
                         nothing is ever edited there directly.
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

Set up the `main` worktree once per machine:

```bash
scripts/worktree-add.sh ~/.config-main main
git worktree list                        # confirm both worktrees are registered
```

### Why a helper script, not plain `git worktree add`

git-crypt 0.8.0 has a real limitation with linked worktrees: its clean/smudge
filter resolves the symmetric key via the **calling worktree's own** git-dir
(`.git/worktrees/<name>/`), which a linked worktree never has populated — only
the shared common `.git/git-crypt/keys/` does. So a plain `git worktree add`
on this repo fails outright the moment it tries to check out an encrypted path
(`.env`, `agents/memory/**`), with `git-crypt: Error: Unable to open key file`
— even immediately after a successful `git-crypt unlock` in the primary
worktree, and even though the key demonstrably exists at the correct shared
path. `git-crypt unlock` run directly inside the new worktree fails the same
way, for the same reason.

Verified reproducible from three independent from-scratch clones, ruling out
stale state as the cause. The workaround, packaged in `scripts/worktree-add.sh`:

```bash
git worktree add --no-checkout <path> <branch>   # skip the checkout that would fail
common="$(git rev-parse --git-common-dir)"
wtgitdir="$(git -C <path> rev-parse --git-dir)"
ln -s "$(python3 -c 'import os,sys;print(os.path.relpath(sys.argv[1],sys.argv[2]))' \
  "$common/git-crypt" "$wtgitdir")" "$wtgitdir/git-crypt"
git -C <path> checkout <branch>                   # now the smudge filter finds the key
git -C <path> submodule update --init --recursive # submodules aren't shared across worktrees
```

Use the script rather than hand-typing this — it also handles the locked-repo
case (skips the symlink, tells you to unlock first) and initializes submodules.

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
scripts/publish.sh <path>...              # the whole cycle, INCLUDING the push
scripts/publish.sh -m "msg" <path>...     # non-interactive commit message
scripts/publish.sh --no-push <path>...    # promote + verify, stop before pushing

scripts/promote.sh <path> [<path>...]     # guided; vets, commits, does NOT push
scripts/promote.sh --dry-run <path>...    # show what would move, change nothing
```

`publish.sh` is the everyday entry point; `promote.sh` is the gate it wraps.
The split is deliberate: `promote.sh` stops before `git push` because a *first*
promotion should be reviewed by a human, and that is friction you don't want on
the tenth. `publish.sh` opts into the rest — it pushes `main`, then verifies the
device branch is a superset of public for the promoted paths. Both run `vet.sh`;
neither can skip it, since `publish.sh` reaches the push only if `promote.sh`
exits 0.

`publish.sh` **does not rebase the device branch onto main**, despite the shape
of the request it usually answers. The two branches share *no common ancestor*
(`git merge-base` returns nothing) because main's root commit was rewritten by
a past `git-filter-repo` scrub — a rebase would replay the device branch's
entire history against unrelated commit objects. `promote.sh`'s cherry-pick
already achieves the real goal, so `publish.sh` verifies the superset property
instead of recreating it.

Run these from the device branch's worktree (`~/.config`) — never from main's.
`promote.sh` refuses to start from main's worktree or a dirty tree, aborts and
unstages in main's worktree if `vet.sh` finds anything, and stops before
`git push` — printing the command instead. By hand:

```bash
# 0. Start clean. Uncommitted work must be stashed or committed first.
git status --porcelain          # must be empty
DEVICE="$(git rev-parse --abbrev-ref HEAD)"
MAIN_WT="$(git worktree list --porcelain | awk '/^worktree/{p=$2} /^branch refs\/heads\/main$/{print p}')"

# 1. Refresh main's worktree from origin.
git -C "$MAIN_WT" pull --ff-only origin main

# 2. Bring over ONLY the vetted paths into main's worktree. Checkout specific
#    files from the device branch — never merge the whole branch.
git -C "$MAIN_WT" checkout "$DEVICE" -- <specific/safe/path> ...

# 3. VET before committing. vet.sh reads the staged diff wherever it's run.
(cd "$MAIN_WT" && scripts/vet.sh)

# 4. Commit and publish, in main's worktree.
git -C "$MAIN_WT" commit
git -C "$MAIN_WT" push origin main

# 5. Cherry-pick the promotion commit back onto the device branch (this
#    worktree) so it stays a superset of what's public. NOT a rebase: main's
#    root commit was rewritten by a past git-filter-repo history scrub, so a
#    full rebase replays this branch's entire history against unrelated
#    commit objects and can hit unresolvable conflicts on git-crypt-encrypted
#    binaries.
promoted="$(git -C "$MAIN_WT" rev-parse HEAD)"
git cherry-pick --empty=keep -x "$promoted"
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
   in a public repo. The term list is deliberately NOT hardcoded in this
   public script (that would itself disclose which internal tools/services
   exist) — it's read from `.vet-terms.local`, a gitignored, per-machine file.
   Copy `.vet-terms.local.example` to `.vet-terms.local` and fill in your own
   org's internal hostnames/tool names. Without it, only a small generic set is
   checked and `vet.sh` warns loudly that it's missing.

   Because the file is gitignored it exists in exactly one worktree — normally
   the device one. But promotion runs `vet.sh` with cwd set to **main's**
   worktree, where `show-toplevel` resolves elsewhere and the file is absent, so
   this check used to silently degrade to the generic set and still print PASS at
   the one moment it mattered. `vet.sh` now searches the calling worktree first,
   then every worktree registered on the repo; `VET_TERMS_FILE` overrides both.
   If you see the missing-terms WARN during a promotion, treat that PASS as
   unverified.
4. **Credential-shaped strings** (FAIL) — token prefixes, AWS key ids, PEM
   private-key headers, JWTs.
5. **git-crypt locked** (WARN) — when the key is missing the clean filter fails
   *open*, so encrypted paths would commit as plaintext. Checks the shared
   common `.git/git-crypt/keys/` (via `--git-common-dir`), not a hardcoded
   local path, so it reports correctly from a linked worktree too.

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

`install.sh` (macOS/Linux) and `install.ps1` (Windows) automate everything
below except `git-crypt unlock` — the key is deliberately kept out of the
repo, so unlocking stays a manual, out-of-band step:

```bash
curl -sSL https://raw.githubusercontent.com/kendreaditya/.config/main/install.sh | bash
```

By hand, or what the installer does on a fresh clone:

```bash
git clone https://github.com/kendreaditya/.config.git ~/.config
cd ~/.config
git config core.hooksPath .githooks           # enable the secret guard
git switch -c "device/$(hostname -s)"         # or scutil --get LocalHostName
git-crypt unlock /path/to/git-crypt.key       # else encrypted paths stay ciphertext
scripts/worktree-add.sh ~/.config-main main   # linked worktree for promotions
```

If git-crypt isn't unlocked yet when the installer runs, it skips the
worktree step and prints the `worktree-add.sh` command to run by hand once
you've unlocked — it can't check out `.env`/`agents/memory/**` into the new
worktree without the key.

If `~/.config` **already exists and is non-empty** — which is the case on the
work dev server, where a managed tool owns `~/.config/<tool>/` — do not clone
over it. `install.sh` only renames it to `~/.config.bak` and clones fresh; it
does not attempt to adopt anything back in, since deciding what's safe to
track needs a human look, not a script. Adopt it by hand instead:

```bash
mv ~/.config ~/.config-preexisting            # keep the originals, do not delete
git clone https://github.com/kendreaditya/.config.git ~/.config
cd ~/.config
git config core.hooksPath .githooks
git switch -c "device/$(hostname -s)"
git-crypt unlock /path/to/git-crypt.key
scripts/worktree-add.sh ~/.config-main main

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
- Cherry-picking the promotion commit back onto the device branch (step 5)
  keeps it a superset of what's public without re-running the full history —
  see "Why a helper script, not plain `git worktree add`" above for why a
  rebase isn't safe here.
- The device branch is a working branch, not a backup. It exists on exactly one
  machine and is never pushed — so it is **not** disaster recovery. Back up
  secrets (e.g. the git-crypt key) out of band.
- Submodules (`ws`, `parlai`) are not shared across worktrees — each one needs
  its own `git submodule update --init --recursive`, which `worktree-add.sh`
  already does for you.
