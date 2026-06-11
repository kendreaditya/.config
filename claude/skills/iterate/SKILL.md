---
name: iterate
description: >-
  Set an objective and autonomously iterate toward it until it is verifiably met — a "Ralph Loop" /
  goal-mode for Claude Code. Each pass does one unit of work, then evaluates whether the goal is met
  (via a deterministic --check command or a skeptical self-assessment); it stops on success, on a
  max-iteration cap, or at a genuine blocking wall. Use when the user says "iterate until", "keep
  going until X passes/works", "loop until the goal is met", "set a finish line and don't stop",
  invokes "/iterate", or wants an autonomous improve→verify loop toward a measurable outcome. Also
  use for "/iterate resume" / "resume the iterate run" to continue an interrupted run from its
  scratchpad. NOT for fixed-interval polling or one-off tasks — for a recurring scheduled prompt use
  /loop; for a single action just do it. For self-contained goals iterate runs in-session
  back-to-back; for goals gated on external state (CI, a deploy, a log line) it paces with
  ScheduleWakeup/Monitor like /loop.
---

# iterate — loop until a goal is met

A self-evaluating agentic loop: **plan → act → verify → (if not done) iterate**. The loop's own
verdict on *what is still missing* becomes the next iteration's instruction. This is the local
equivalent of Codex's `/goal` Goal Mode / the "Ralph Loop". It terminates — it is not `/loop`
(which runs forever on a schedule).

## Parse the invocation

The argument is the **objective**. Optional flags may appear anywhere:

| Flag | Meaning | Default |
|------|---------|---------|
| `--check "<cmd>"` | Shell command that is the **done signal**: exit code `0` ⇒ goal met. The most reliable gate — prefer it whenever the goal is mechanically checkable (tests, build, lint, a curl assertion). | none → self-evaluate |
| `--max <N>` | Hard cap on iterations (runaway backstop). | `25` |
| `--timeout <Nm/Nh>` | Wall-clock budget for the whole run. Check elapsed time each iteration; stop and report partial progress when exceeded. | none |
| `--interval <Nm/Nh>` | Wait this long between iterations instead of running back-to-back. Use when the goal depends on external state that changes over wall-clock time. | none → continuous in-session |

Subcommand: `/iterate resume [slug]` — continue an interrupted run. Read the named scratchpad under
`~/.claude/iterate/` (or the most recently modified one if no slug), restate goal + criteria + where
it left off, and re-enter the loop at Step 2 with the iteration count carried forward.

If the objective is empty, show usage `/iterate [--check "<cmd>"] [--max N] [--timeout 30m] [--interval Nm] <goal>` and stop.

## Step 1 — Lock the success criteria *before* looping

Restate the goal in one line, then write **concrete, verifiable done-criteria**. The loop is only as
good as this definition.

- If `--check` was given, that command IS the criterion. Run it once now to capture the starting
  state (it will almost certainly fail — that's the baseline).
- If no `--check`, derive 1–5 checkable criteria yourself (e.g. "`pytest -q` is green", "the page
  renders without console errors", "`/health` returns 200"). State them to the user.
- If the goal is too vague to define done-criteria (no measurable finish line), ask **one** sharp
  clarifying question before starting — do not loop on an unfalsifiable goal.

Then create a **scratchpad file** at `~/.claude/iterate/<kebab-slug-of-goal>.md` (Write tool; the
directory may need creating once). Seed it with: goal, flags, done-criteria, baseline state, start
time, and an empty iteration log. A file — not conversation memory — because long runs outlive
context compaction, and it is what makes `/iterate resume` possible.

## Step 2 — The loop

Repeat until a stop condition (Step 3) fires. The scratchpad file is the loop's durable memory
(what's done, what's left, what was just tried) so you never repeat a failed approach. **If context
was compacted mid-run, re-read the scratchpad before acting.**

Each iteration:

1. **Act** — do the *smallest useful unit* of work toward the nearest unmet criterion. One change per
   pass beats a giant edit you can't evaluate.
2. **Verify** — decide "is the goal met?":
   - With `--check`: run the command. Exit `0` ⇒ **done**. Non-zero ⇒ read the output; that error is
     your next instruction.
   - Without `--check`: evaluate **adversarially against the criteria**. Be skeptical — actively try
     to prove it's *not* done (run the thing, read the output, check edge cases). **Default to "not
     done" when uncertain.** Optimistic self-grading is the main failure mode of this loop.
3. **Record** — append an entry to the scratchpad file: iteration #, criterion status, what changed,
   what's still red, approaches ruled out.
4. **Continue or stop** per Step 3.

**Independent verification before declaring done (no `--check` only):** the actor must not grade its
own homework. When you believe all criteria pass, spawn a **fresh subagent** (Agent tool, Explore or
general-purpose) given ONLY the done-criteria and how to check them — none of this conversation's
history — and prompt it to **refute** "the goal is met" (run the checks itself, hunt for the failing
edge). Only a verdict it cannot refute counts as done; anything it finds becomes the next iteration's
instruction. With `--check`, the exit code already is the independent verdict — skip this.

## Step 3 — Stop conditions

Stop and report when **any** of these is true:

- ✅ **Goal met** — all criteria pass / `--check` exits 0 (and the independent verifier could not
  refute it). Mark the scratchpad `status: done`, report success + a one-line summary of what changed.
  If the user may be away (long/overnight run), send a `PushNotification`.
- 🧱 **Blocked** — you hit a wall needing a human decision, a credential, or an irreversible/outward-facing
  action (deploy, send, delete, spend). Stop and surface the **specific** blocking question — don't guess.
- 🔁 **No progress** — 2–3 consecutive iterations make no measurable movement on any criterion (thrash).
  Before quitting, make **one escalation pass**: get a genuinely different perspective — consult the
  `codex` skill (consult mode) or spawn a fresh subagent — feeding it the scratchpad's ruled-out
  approaches, and try its best suggestion once. Still stuck ⇒ stop, report what was tried and why.
  One escalation round only; don't burn the whole `--max` budget spinning.
- ⛔ **Cap hit** — `--max` reached, or `--timeout` wall-clock budget exceeded. Report how far you got
  (which criteria pass, which remain) so the user can decide whether to bump the budget or change
  approach.

Never silently exceed `--max` or pretend a criterion passed. Report the true state.

## Pacing

- **Default (no `--interval`)**: iterate **back-to-back in this turn**. This is an in-context agentic
  loop — no scheduling, no waiting. Best for self-contained goals (make tests pass, build a feature,
  fix a bug, match a reference).
- **With `--interval`, or when the goal is gated on external state** (CI finishing, a deploy going live,
  a file/log changing): reuse the `/loop` machinery — after each verify, if not done, end the turn with
  `ScheduleWakeup` (fallback heartbeat 1200–1800s, or the requested interval) and, if the gate is an
  event, arm a `Monitor` with `persistent: true` so the event wakes the loop. Re-enter on wake, verify,
  and either stop or reschedule. Carry the scratchpad + iteration count forward in the wakeup prompt.

## Example

```
/iterate --check "pytest -q tests/auth" --max 15 fix the failing auth tests
```
→ Criterion = `pytest -q tests/auth` exits 0. Baseline run: 3 failures. Loop: read failure → fix one
cause → re-run → repeat. Stops the instant the suite is green, at iteration 15, or if it stalls on the
same failure 3×.

```
/iterate get the landing page to render with zero console errors and a Lighthouse perf score ≥ 90
```
→ No `--check`, so derive criteria: (a) page loads, (b) console clean, (c) Lighthouse perf ≥ 90.
Verify each adversarially every pass (actually open it, actually read the console, actually run
Lighthouse). Done only when all three hold.

## Guardrails

- The verifier must be **independent of the optimism of the actor** — re-run the real check; don't
  reason "it should work now".
- One unit of work per pass; large unverifiable edits defeat the loop.
- Honor the standing rule on hard-to-reverse / outward-facing actions: those are a **Blocked** stop,
  not something the loop does autonomously.
- `iterate` terminates by design. If the user actually wants an open-ended recurring task, that's
  `/loop`; a cloud cron is `/schedule`.
