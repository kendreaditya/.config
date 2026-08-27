---
name: comprehension-debt
description: "Keep the human in command of systems an agent is writing, so speed doesn't cost them the mental model. Before code: classifies each task into delegate / own-design / hands-on and enforces that mode's gates. After code: a recovery path for rebuilding understanding of code that already landed. Use when the user says they don't understand code that was built for them, asks whether they're accruing tech debt or losing their edge, asks to be kept in the loop, taught as you go, or told what's happening rather than handed a diff; when they want to own the design themselves; when they need to ramp back onto AI-written code they can't explain; or starting non-trivial feature work on code that will persist. Triggers: 'I don't understand what you built', 'am I accruing tech debt', 'keep me in the loop', 'explain as you go', 'don't just do it for me', 'I want to understand this', 'help me ramp back onto this', 'comprehension debt'. NOT for throwaway scripts, spikes, or one-line fixes."
---

# Comprehension Debt

Classic tech debt is code the team understands but hasn't cleaned up. Comprehension debt
is code **nobody holds a theory of** — it runs, tests pass, and no human can explain why it
is shaped that way or safely extend it. This skill spends comprehension effort only where it
pays off, and does not tax work that is genuinely disposable.

The evidence for the concept is real but narrow. Read `references/comprehension-debt.md`
before making a strong claim about it — including the objections, which are not weak.

## Classify first — before any code exists

**If the code already exists and the problem is that they can't explain it, skip this section
entirely and go to Recovery.** The classifier is a pre-work gate; there is nothing left to
classify once the diff has landed. Do not ask the mode question in that case.

If the user's message does not already state a mode, ask **once**, in one line:

> Quick check before I start: if this is wrong, who pays and can it be undone? Will you need
> this logic again? Is there a test/build/rollback that would catch a mistake?
> Delegate, own-design, or hands-on?

Accept the answer. Do not re-derive it, argue with it, or re-ask later in the same task.

- **PAYS** — blast radius, who gets paged, reversibility.
- **LASTS** — will they personally reconstruct, extend, or defend this logic again, or is it
  mechanical work they will never revisit?
- **NET** — does a fast, trustworthy automated check exist? This is the one axis that is a
  fact rather than a feeling, so **you** enforce it, not the user's self-report.

| PAYS | LASTS | Mode |
|---|---|---|
| low | low | delegate |
| low | high | own-design |
| high | any | own-design, or hands-on if NET is absent |

**Gate:** one of the words `delegate`, `own-design`, or `hands-on` appears before the first
line of code. Checkable by grep, not by vibe. Do not start own-design or hands-on work
without it.

## Mode: delegate

- Restate the acceptance criteria in one sentence, then implement.
- Run the tests, build, and linter **yourself, in this session**.
- Never say "done" or "tests pass" without having just executed them.
- Never weaken, skip, or delete a failing check to force green. If it can't pass, say so.
- Write three lines into the PR/commit: what changed, why, what was verified.
- **Gate:** checks observed green — not agent-reported. If no automated check exists at all,
  this mode is invalid: return to Classify, because NET absent forces at least own-design.

## Mode: own-design

- Do not write implementation code until a written plan exists.
- If asked to draft the plan: ask about edge cases and tradeoffs first, present it, and stop.
- **A plan is only valid if it carries the user's own wording or edits.** If they approve an
  unedited draft of yours verbatim, say so plainly and ask for edits before implementing —
  an approved-but-unauthored spec is delegate mode wearing a disguise.
- After implementing, list every point where the code diverged from the plan, and why.
- **Gate:** the plan contains their words, and they can answer "what would you change if
  requirement X changed?" without opening the code.

## Mode: hands-on

- They type the implementation. You answer questions, critique their draft, point at docs,
  and surface one risk at a time.
- **Do not originate or patch the load-bearing logic — not on a second request either.**
  Offer to write the surrounding boilerplate or tests instead. This is a refusal, not a
  negotiation; one granted exception becomes the default within days.
- When asked what a function or approach will do, ask for their prediction first, then
  confirm or correct. Never just reveal.
- **Gate:** they can give an unprompted, notes-free explanation of the mechanism — the 2am
  test. If they can't, the task isn't done, even if the code runs.

## Recovery: code that already exists

For "I don't understand what you built" — after the fact, on code that already landed. This
path is weaker and costs more than classifying up front; say so once, plainly, without
lecturing, then do the work.

Treat it as legacy code by Feathers' definition regardless of how clean it looks or how
recently it was written: nobody currently holds a theory of it. Start with the cheapest step
that fits the situation and stop as soon as they can pass the gate.

1. **Bound it first.** Name the entry points, the blast radius, and what it touches. Do not
   start with a line-by-line walkthrough — that is a rereading strategy and the weakest option
   available.
2. **Predict, then check.** Ask what they expect a piece to do before showing them. Same habit
   as the pre-work path, still the best ratio here.
3. **Characterization tests.** Write tests that pin what the code *actually* does, not what it
   was supposed to do. Writing them is what builds the model; having them is the safety net.
4. **Modify-it.** Have them rearrange, rename, or reconstruct a piece rather than read it —
   better retention than reading, at less cost than a rewrite. Prefer this over a walkthrough.
5. **Scratch refactor.** Restructure a throwaway copy purely to expose the shape, then discard
   it and make the real change afterward.
6. **Rewrite the core unaided.** Highest ceiling, highest cost. Reserve for logic that is both
   load-bearing and staying.

**Gate:** the 2am test — an unprompted, notes-free explanation of the mechanism. Not "it makes
sense when I read it," which is fluency, not retention.

Then close the loop so this doesn't recur: capture the *why* in an ADR or CONTEXT.md
(`documentation-and-adrs`, `domain-modeling`), and classify the next change to that code up
front. If they explicitly want to be walked through it Socratically rather than handed
answers, that is `socratic`, not this.

## Hard floors — independent of mode, not downgradable under time pressure

- **NET absent on a high-PAYS task forces at least own-design.** No exceptions for deadlines.
- **Named risk categories always get a personal human line-read before merge**, regardless of
  mode or CI status: auth, security boundaries, concurrency, money, data deletion, database
  migrations, production credentials. Say explicitly that this one needs their eyes.
- **Never accept your own or another agent's self-report that a check passed.** Verify green.
- **Three strikes:** on the third consecutive attempt to fix the same failing behavior, stop.
  Report what is actually failing. Do not attempt a fourth autonomous fix. This is exactly
  the sunk-cost moment the rule exists to interrupt.
- Automation complacency is a documented attentional effect, not a discipline failure — "just
  review carefully" is not a control. Prefer structural gates.

## The one habit worth keeping if everything else is dropped

**Predict before reveal.** Before they read your diff, get a guess: the approach, the output,
or best of all a test assertion they write themselves so your code has to satisfy their
prediction rather than them grading yours afterward. Costs under 30 seconds, needs no mode,
no classification, no ceremony.

Apply it at each material decision point, not once per session — the benefit is item-specific
(g=0.54 for the predicted item, g=0.04 for everything else in the same lesson). Second-best
per minute: ask them *why* a piece is valid, not just *what* it does; that is the one lever a
controlled AI-coding trial confirmed preserved comprehension.

## Escalate mid-flight — literal triggers only, never a subjective read

Surface these; never silently retry or push through:

- Third identical fix attempt → stop, report, hand back.
- Diff touches a named risk category while mode is `delegate` → say so, ask them to confirm
  the mode before continuing.
- About to touch files or directories outside what the task described → ask first.
- A test was weakened, skipped, or deleted to get green → say so before anything else.

De-escalate only with an explicit yes, against a narrow named pattern: if the same task shape
has cleared own-design 3+ times with no material plan edits, offer to treat it as delegate
going forward. Never downgrade unilaterally.

## When NOT to apply this

Default to delegate, implement directly, and **do not run the classifier out loud**:

- Throwaway prototypes and spikes meant to be deleted.
- One-off scripts run once against known data.
- Glue code calling a stable, versioned external API.
- Feature-flagged experiments slated for removal in weeks.
- Anything fully covered by fast tests plus staging plus one-click rollback.
- Low-stakes internal tooling where a defect costs one person an inconvenience.
- Lookups, one-line fixes, and anything whose diff fits in one sentence.

Median code-line lifespan is roughly 2.4 years, and lines that do get deleted often live under
100 days. Building a durable model of code you already know is disposable is a bad trade.
**Imposing this skill on disposable work is the single biggest reason such protocols get
abandoned wholesale** — so don't.

Deliberately not included: EARS-notation spec rituals as a default, delayed retention quizzes,
written review packets for small diffs, adversarial subagent passes on delegate-mode work.
They are pedagogically nice and will be the first things skipped.

## References — read on demand, they cost nothing until needed

- `references/comprehension-debt.md` — post-AI evidence: what is measured vs. asserted, what
  died in fact-checking, the strongest objections, and what survives them. Load before citing
  a number or making a strong claim.
- `references/learning-loop.md` — why a gate works, and whether a given shortcut is
  defensible. Load when tempted to skip a step.
- `references/field-practice.md` — sourced vendor practice and a tactics table ordered by
  evidence-to-cost. Load when you need a concrete tactic.
- `references/debt-canon.md` — the pre-AI canon (Naur, Feathers, Ousterhout, Parnas) and which
  comprehension mechanisms AI-assisted work quietly removed. Load for grounding or history.

Adjacent skills: `tech-debt` for scoring an existing debt backlog, `socratic` when they
explicitly want tutoring, `documentation-and-adrs` and `domain-modeling` for capturing the
decisions this protocol surfaces. Do not restate their content here.
