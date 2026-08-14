---
name: delegate-to-claude-code
description: Delegate bounded implementation, debugging, review, research, or visual-validation work from Codex to the local Anthropic Claude Code CLI, then supervise, resume, independently verify, and publish the result. Use when the user explicitly asks Codex to use, deploy, continue, or resume Claude Code, the `claude` CLI, a Claude/Opus coding session, multiple separate Claude instances, or an existing Claude session. Also use when repairing an interrupted Codex-to-Claude handoff. Do not invoke merely because Claude Code is available.
---

# Delegate to Claude Code

Act as the orchestrator. Give one bounded task to a separate Claude Code implementer, preserve enough state to resume it, inspect its actual work, and retain final judgment. Claude's report is evidence, not acceptance.

## Load the relevant references

- Read [references/brief-template.md](references/brief-template.md) before writing a new brief.
- Read [references/cli-and-sessions.md](references/cli-and-sessions.md) before launching, resuming, selecting a model, or changing CLI flags.
- Read [references/supervision-and-recovery.md](references/supervision-and-recovery.md) for parallel runs, silent output, timeouts, stuck child processes, interrupted sessions, or new follow-up evidence.
- Read [references/review-and-publish.md](references/review-and-publish.md) before accepting edits, taking screenshots, committing, pushing, or opening/updating a PR.

## Preserve the authority boundary

Use this skill only when the human explicitly requests Claude Code delegation or resumption. Delegation does not broaden the original task.

Never pass `--dangerously-skip-permissions` unless the human explicitly authorized bypass permissions for this work. Treat prior authorization as task-scoped, not permanent. Explain when that flag causes a launch. A clean worktree limits attribution and rollback; it is not a security sandbox.

Keep publication with Codex by default. Tell Claude not to stage, commit, push, open or modify PRs, rewrite history, change repository settings, invoke another coding agent, or perform unrelated cleanup. Delegate publication only when the human specifically asks Claude to own it.

Do not expose secrets in briefs, process arguments, artifacts, screenshots, or reports. Put the brief on stdin through a file, never directly in the command line.

## Run the orchestration loop

### 1. Preflight

1. Run `claude --version` and `claude auth status`.
2. Read all applicable `AGENTS.md`, `CLAUDE.md`, and repository workflow instructions yourself. Claude Code discovers `CLAUDE.md` normally but does not generically auto-load `AGENTS.md`.
3. Inspect the repository, current branch, remotes, dirty state, package scripts, and real verification commands.
4. Resolve the requested model from the human's words. Verify the effective model from the result event rather than trusting an alias such as `opus`.
5. Decide whether this is a fresh session, a delta brief to a known session ID, or an independent parallel task.

Stop if the CLI is unavailable or unauthenticated, if the requested host boundary cannot be provided, or if completing correctly requires new authority.

### 2. Isolate the task

Use one branch and one clean git worktree per independent task. Never run multiple implementers in the same tree. Never let a delegated run inherit unrelated user changes.

Prefer an explicit orchestrator-created worktree because it makes the path, branch, base commit, cleanup, and PR mapping visible. Claude Code's native `--worktree` is acceptable only when its generated path and branch will be recorded and independently reviewed.

Give concurrent preview or dev servers unique ports. Inspect an occupied port and its exact owning process before acting; never use broad `pkill`, `killall`, or guessed process termination.

### 3. Create a self-contained brief

Create the brief outside the worktree. Include:

- the user's outcome and observable acceptance criteria;
- exact repository/worktree scope and files or behaviors that must not change;
- all load-bearing `AGENTS.md` rules and any critical `CLAUDE.md` rules;
- attachment paths and what each image demonstrates;
- reproduction-before-fix instructions for bugs;
- exact tests, lint, typecheck, build, and screenshot gates;
- explicit edge cases and desktop/mobile non-regression requirements;
- the no-commit/no-push ownership boundary;
- a structured final report contract.

Use a delta brief—not the entire original prompt—when resuming the same session after review feedback or new evidence.

### 4. Launch and record

Use the bundled runner for a direct supervised session:

```bash
python3 <skill-dir>/scripts/run_claude.py \
  --workdir /absolute/path/to/worktree \
  --brief /absolute/path/to/brief.md \
  --out-dir /absolute/path/outside/repo/run-name \
  --model opus --effort high
```

Add `--dangerously-skip-permissions` only under the explicit authority rule above. Resume a known conversation with `--resume <session-id>` and a delta brief. Inspect all local options with `python3 <skill-dir>/scripts/run_claude.py --help` and all installed-Claude options with `claude --help`; CLI behavior changes over time.

Record at minimum: task, repo, base commit, branch, worktree, brief path, artifact path, requested/effective model, permission mode, session ID, unique ports, status, and next action. For more than two tasks, maintain a small progress ledger outside the repository.

### 5. Supervise by evidence

The runner uses `stream-json`, mirrors Claude's text to stderr, and preserves raw events. Still, do not equate quiet stdout with a dead session. Check:

- whether the exact process is alive;
- git status, diff, and recent file modification times in its worktree;
- child test/build/browser processes;
- the assigned port and preview health;
- the artifact event stream and stderr tail.

Send concise user updates during long work. Do not interrupt only because no final JSON has appeared.

### 6. Heal interrupted work

On timeout, interruption, tool failure, port collision, or lost final report:

1. Preserve the worktree and artifacts.
2. Inspect unstaged, staged, untracked, and ignored task artifacts before changing anything.
3. Read `result.json`, `events.jsonl`, `stderr.txt`, and `final.txt` when present.
4. Resolve only the exact blocking process or premise.
5. Resume the recorded session ID with a short delta: inspect the existing diff, finish remaining gates, clean task-created processes/files, and return the report.
6. Start a fresh session only if continuity is impossible or the task premise materially changed.

Never reset, clean, switch, or delete partial work reflexively. The worktree is the authoritative recovery copy until reviewed or intentionally discarded.

### 7. Verify independently

After Claude exits, Codex must:

1. inspect `git status --short`, `git diff`, `git diff --cached`, and every untracked file;
2. compare the entire tree with the brief and user evidence;
3. inspect test changes before trusting green results;
4. rerun the repository's real gates;
5. reproduce visual behavior and inspect screenshots at the requested viewport/device conditions;
6. check that temporary servers, scripts, configs, and artifacts were cleaned up;
7. send review defects back to the same Claude session as a delta brief when continuity helps.

Only Codex's verified result may be committed or published. Follow the repository's GitHub/PR workflow and applicable publishing skill after verification.

## Report the handoff

Tell the human:

- what Claude changed and what Codex independently confirmed;
- model and permission mode actually used;
- test/build/visual outcomes;
- branch, commit, and PR links when published;
- any remaining decision, risk, or unverified environment limitation.

Do not claim success merely because Claude returned a success result.
