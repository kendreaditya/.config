---
name: catch-me-up
description: "Explain completed agent work so the user can understand and safely own it, then verify they actually do with a live quiz. Use after a substantial coding, debugging, research, migration, or multi-repo task when the user asks what changed, how it works, why decisions were made, what was verified, what remains uncertain, or to be caught up — and before handing a diff to another human reviewer. Do not use before or during implementation, and do not redo the task. Triggers: 'catch me up', 'what changed', 'explain this diff', 'explain the PR', 'walk me through what you built', 'do I understand this', 'quiz me on this', 'explain-diff'."
upstream:
  gist: a29df1b5f9865506e8952488eac3d524
  file: explain-diff-html.md
  sha: 126e7fe9eecaafadfe1ac8bb183d135812b608f2
  license: none-stated
  checked: 2026-09-03
  content_hash: d81ac148271131c3a9931b71d5f3108a7570519d56c21d2e16d21a5b96017e7f
---

# Catch Me Up

Explain completed work from evidence, in the conversation, then confirm it landed. The goal is
not to recap activity; it is to give the user a compact mental model they can use to reason
about, modify, and defend the result — and to verify they hold it rather than assuming a
document was read.

Everything happens in the conversation. No durable artifact, no HTML file, no separate page to
go read later. If the explanation doesn't fit in a response, it is too long.

Do not run this on a task whose diff fits in one sentence. Imposing ceremony on disposable work
is the single biggest reason these protocols get abandoned — see `comprehension-debt`, which is
the *pre-work* counterpart to this skill.

## Before you explain: get their prediction

One line, before you reveal anything:

> Before I walk through it — what do you expect I did here?

This is the highest-value habit in the whole protocol and it costs 30 seconds. The retention
benefit is specific to the item predicted (g=0.54) and does not spread to the rest of the
explanation (g=0.04), so ask it about the load-bearing decision, not the task in general.
Skip it only if they have already stated their model. Never withhold the explanation waiting
for an answer — ask, then continue in the same breath if they don't bite.

## Establish the evidence

Inspect the completed task, final repository state or artifacts, relevant diff, test results,
and important decisions in the session. Treat prior summaries — including your own, and any
subagent's — as claims until they agree with the resulting files and verification output.

Track completion state precisely. `Implemented`, `verified`, `committed`, `pushed`, `deployed`,
and `observed working in production` are different claims. State each only when direct evidence
supports it, and use the latest evidence when a later message corrects an earlier report.

Do not modify code, rerun the implementation, or broaden the task. If evidence is unavailable,
say what cannot be established instead of reconstructing a plausible story.

## Select what the user needs to retain

Prioritize:

1. The outcome and its practical effect.
2. The mechanism or data flow that makes the result work.
3. The few load-bearing design decisions and why they were chosen.
4. Important invariants, failure modes, and ownership boundaries.
5. What was directly verified, what remains unverified, and why.
6. Where a future engineer should start if a key requirement changes.

Prefer causal explanations over implementation chronology. Explain why the system has its
current shape, not the sequence of tool calls used to produce it.

For multi-component work, explain ownership and the end-to-end boundary crossings before
describing individual repositories or files.

## Write the handoff

Target 4,500 characters and never exceed 5,000. Remove low-value detail rather than allowing a
required section to fall beyond the limit.

```markdown
## Background
[The system this change lands in — where it lives, what it already did. 2-3 sentences.]

## Intuition
[What the change is *for*, in essence, with a concrete example over toy data. 2-3 sentences.]

## What changed
[Outcome and practical effect.]

## How it works
[Short end-to-end mechanism or data flow.]

## Why this design
[Two to four decisions, alternatives rejected, and relevant tradeoffs.]

## Verification and limits
[What was tested, what those tests establish, and what remains unknown.]

## Change map
[The smallest set of code pointers and where to begin for likely future changes.]
```

**Background and Intuition come first because a change-first explanation is only legible to
someone who already understood the system** — which is exactly the reader who did not need
this. Explore the surrounding code to write Background; do not infer it from the diff.

Keep both to a few sentences each. They are scene-setting, not sections that grow, and the
character budget belongs to the mechanism. Say so and skip Background outright when the user
already knows the area.

Intuition and What changed overlap by design and must not repeat: Intuition is the *purpose*
in essence form ("make the garden feel 3D using only 2D drawing tricks"), What changed is the
concrete outcome and its practical effect. Because Intuition carries the essence, a reader who
stops after two sections still leaves with the point.

Include at most two short code excerpts or one compact Mermaid diagram, and only when they
replace substantial prose. Include example data in any diagram, and never use ASCII diagrams.
Use exact file and line pointers when available, but do not emit an exhaustive file inventory.

Write in prose with clear transitions — the model should read as an explanation, not a form
someone filled out.

## The quiz is the gate

End every catch-up with five questions, medium difficulty: hard enough that answering requires
understanding the substance of the change, never gotchas or trivia about line numbers.

**Ask them live through the harness, and grade them yourself.** Never emit a self-grading
quiz — you are in the conversation, so a wrong answer should get its misconception named and a
follow-up, which no static list of answers can give.

- **Claude Code** → `AskUserQuestion`. Cap is 4 questions per call, so five means two calls.
  Put the code under discussion in the `preview` field so the question is answerable without
  scrolling back.
- **Codex** → `request_user_input`. Cap is 3 per call. Requires
  `tools.experimental_request_user_input = { enabled = true }` in `~/.codex/config.toml`, and
  it does not exist in `codex exec`.
- **Neither available** → ask in plain prose and wait. Do not self-grade.

Exact schemas and per-harness quirks: `references/surfaces.md`. How to write questions that
discriminate: `references/quiz.md`.

**The rule this exists to enforce:** do not hand the change to another human reviewer until the
person who owns it can pass the quiz. It is a speed regulator — everything else about agents
optimizes for velocity, and this is the one thing that holds the pace to the speed of
understanding rather than the speed of correctness.

State the outcome plainly. If they miss two or more, say so and offer to re-explain the
specific thing they missed — do not soften it, and do not move on to the next task as though
the gate passed.

## Protect understanding

- Distinguish verified facts, inference, and unresolved questions.
- Never infer that a change was committed, pushed, deployed, or production-tested from a
  successful implementation or local test.
- Name semantic boundaries between components, not merely their filenames.
- Explain non-obvious failure and retry behavior.
- Surface deliberate non-changes when they preserve compatibility or ownership.
- Include enough information to answer how a requirement change would propagate.
- Avoid tool-call chronology, generic praise, long test listings, and changelog-style narration.
- Never expose credentials, tokens, private keys, or secret values.

## References

- `references/surfaces.md` — the question tools and their real schemas and caps, per harness.
  Load before writing the quiz.
- `references/quiz.md` — writing questions that discriminate understanding from fluency, and
  what to do when the gate fails.

Adjacent: `comprehension-debt` classifies work *before* it starts and is the better tool if the
code doesn't exist yet; `socratic` if they want tutoring rather than a handoff;
`documentation-and-adrs` to make the *why* durable once this surfaces it.
