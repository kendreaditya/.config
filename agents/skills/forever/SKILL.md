---
name: forever
description: >-
  Work on a problem endlessly with no finish line — a Ralph-Loop-style perpetual improvement agent.
  Each pass re-reads durable state from disk, picks the single highest-value next improvement, does
  it, verifies nothing regressed, records, and continues; it never declares "done" and only the user
  stops it. Use when the user says "work on this forever", "never stop", "keep improving X
  indefinitely", "ralph this", "run on this all night / 24-7", invokes "/forever", or "/forever
  resume" to continue a prior run. NOT for goal-bounded work (/iterate terminates when a goal is
  met), recurring fixed prompts (/loop has no progress memory), or one-off tasks. State lives in
  ~/.claude/forever/<slug>/ so runs survive context compaction and are resumable.
---

# forever — the loop with no finish line

A perpetual improvement loop: **orient → pick → act → verify → record → repeat**. Modeled on the
Ralph Loop (`while true; do cat task.md | claude -p; done`): the filesystem is the memory, each pass
behaves as if context were fresh, and there is **no done-condition by design**. Contrast: `/iterate`
terminates when a goal is met; `/loop` re-runs a fixed prompt with no memory of progress; `/forever`
compounds work on one mission indefinitely.

## Parse the invocation

The argument is the **mission** — an open-ended direction, not a finish line ("make this codebase
faster", "keep the test suite healthy and growing", "improve the dashboard's polish endlessly").

| Flag | Meaning | Default |
|------|---------|---------|
| `--check "<cmd>"` | **Invariant, not finish line**: this command must exit `0` after every pass. A pass that turns it red must be fixed or reverted before the loop continues. | none |
| `--interval <Nm/Nh>` | Sleep between passes (a5c-forever style: work → sleep → repeat). Use when each pass should wait for the world to change (new tickets, new data, new commits). | none → continuous |

Subcommand: `/forever resume [slug]` — re-read `~/.claude/forever/<slug>/state.md` (most recently
modified if no slug) and re-enter the loop where it left off.

If the mission is empty, show usage `/forever [--check "<cmd>"] [--interval 4h] <mission>` and stop.

## Step 0 — Charter

Create `~/.claude/forever/<kebab-slug>/state.md` with:

- **Mission** — the open-ended direction, one line.
- **Invariants** — what must never break (the `--check` command, plus derived ones: "tests stay
  green", "no force-push", "don't touch X").
- **Backlog** — 5–10 concrete candidate improvements, ranked by value. Generate this by actually
  surveying the current state, not by guessing.
- **Done log** — empty; one line per completed pass.
- **Learnings** — empty; ruled-out approaches, discovered constraints.

Disk, not conversation memory, because the run will outlive context compaction many times over —
after any compaction, **re-read state.md before acting**. This file is also what `resume` reads.

## The eternal loop — thin orchestrator, fresh worker per pass

The Ralph property that makes the bash loop work — **a fresh context window every iteration** — is
replicated with subagents. The main conversation is only an orchestrator; it never does the work
itself. Each pass = spawn a **fresh subagent** (Agent tool, general-purpose) whose entire knowledge
of the run comes from `state.md`, exactly like a new `claude -p` reading the repo from scratch.
Every pass runs at peak model quality, and the orchestrator's context grows by ~one line per pass
instead of a full work transcript.

**Worker contract** — the subagent prompt contains only: the state-dir path, the mission line, the
`--check` command, and whether this is a consolidation pass. The worker must:

1. Read `state.md` (and survey whatever it references). Backlog < 3 items ⇒ replenishing it with the
   next 5 most valuable improvements IS this pass's work.
2. Pick the single highest-value backlog item — one unit, small enough to verify.
3. Do it.
4. Run the `--check` invariant (and derived invariants). Red ⇒ fix or revert *within the pass*;
   never leave a broken floor for the next worker.
5. Update `state.md` (done log entry with evidence, learnings, prune the item) and commit per the
   project's conventions if in a repo — disk and git are the only memory the next worker gets.
6. Return ONLY a one-line summary plus a status tag: `ok` | `blocked: <specific question>` |
   `reverted: <why>` | `low-value: <why>`.

**Orchestrator per pass** — spawn worker → read its status line → act on it:
`ok` ⇒ next pass (with `--interval`, end the turn with ScheduleWakeup for that delay, prompt
`/forever resume <slug>`; otherwise spawn immediately). `blocked` ⇒ pause-on-human (below).
Worker crash/no return ⇒ log it, spawn the next worker — a dead worker never kills the loop.
Every 5th pass, flag the worker prompt as a **consolidation pass**: maintenance instead of new work
(dedupe/refactor what the loop produced, update docs, prune stale backlog, re-rank by value).
Endless loops generate slop unless something periodically composts it.

If the orchestrator's own context is ever compacted, nothing is lost: re-read `state.md`, resume
spawning. The pass counter lives in the done log, not in memory.

## Stopping & pausing — only the user stops it

- There is **no success-stop**. Milestones (an invariant upgraded, a backlog tier cleared) get a
  `PushNotification` and the loop continues.
- **Blocked ≠ stopped**: needing a human decision, credential, or any irreversible/outward-facing
  action (deploy, send, delete, spend) pauses the loop — surface the specific question, note
  `status: paused-on-human` in state.md, and keep a long ScheduleWakeup heartbeat so an answer
  resumes it. Never burn the block down autonomously.
- **Diminishing returns**: if 3 consecutive workers return `low-value`, say so honestly and ask the
  user whether to continue, redirect the mission, or stop. Forever shouldn't mean pretending there's
  value when there isn't.
- User says stop ⇒ mark `status: stopped` in state.md, summarize the done log, end.

## Session-boundary honesty

In-session, the loop sustains itself with ScheduleWakeup — but **ScheduleWakeup dies with the
session**. For true 24/7 operation across sessions, offer the user one of:

- `/schedule` — cloud cron invoking `/forever resume <slug>` on a cadence (survives everything), or
- the classic bash Ralph escape hatch, run in a terminal the user owns:
  `while true; do cat ~/.claude/forever/<slug>/prompt.md | claude -p --dangerously-skip-permissions; done`
  (write a `prompt.md` containing "/forever resume <slug>" first; warn about the permissions flag).

State the limitation when the run starts so an overnight expectation isn't silently unmet.

## Guardrails

- Each pass must leave the system **strictly better or untouched** — never worse. The invariant
  check is the floor; reverting is always preferable to proceeding broken.
- No churn-to-feel-busy: cosmetic rewrites, gratuitous refactors, and oscillating between two
  styles are the failure modes of endless loops. Value-ranked backlog + consolidation passes are
  the defense; when in doubt, replenish the backlog rather than polish noise.
- Honor the standing rule on hard-to-reverse / outward-facing actions: pause-on-human, always.
- Token cost is real and unbounded by design — at start, tell the user roughly what a pass costs
  and confirm cadence for `--interval`-less runs they intend to leave unattended.
