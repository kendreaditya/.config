# Brief template

Use this template as a checklist, not ceremony. Remove empty sections. The delegated session has no Codex conversation history, so include facts that are neither in the tree nor loaded by Claude Code.

```xml
<role_and_task>
You are the implementer in a Codex-orchestrated task. Explore the repository enough to understand the relevant architecture, then complete this one bounded task:

Current behavior:
Desired behavior:
User-visible acceptance criteria:
</role_and_task>

<evidence>
Screenshot or attachment paths and what each demonstrates:
Relevant URLs, PRs, issue text, error output, or reproduction steps:
</evidence>

<scope>
Repository root:
Expected application/package:
Allowed scope:
Must remain unchanged:
Base branch or commit:
</scope>

<repository_instructions>
Read the applicable CLAUDE.md. Also read these explicitly named AGENTS.md files; Claude Code does not generically auto-load them:

Copy the load-bearing rules here, including generated-file policy, documentation-first requirements, styling conventions, and forbidden actions.
</repository_instructions>

<diagnosis_and_implementation>
For a bug, reproduce and identify the root cause before editing. Add or update a behavior-level regression test that fails for the old behavior and passes for the fix when practical.

Implement the smallest complete fix. Preserve desktop/mobile and unrelated behavior. Search for call sites and edge cases affected by the same invariant. Do not hide failures with fallbacks, broad catches, weakened tests, or hardcoded fixture values.
</diagnosis_and_implementation>

<verification_loop>
Run and make green these exact commands:
  TEST COMMAND
  LINT OR FORMAT COMMAND
  TYPECHECK OR BUILD COMMAND

For visual work:
  viewport/device and color scheme
  exact route and state
  screenshot path outside tracked source
  behavior to inspect, including keyboard/safe-area/scroll/overlay states

Confirm git status contains only intended source/test changes. Remove task-created preview processes, temporary scripts, generated configs, and disposable artifacts.
</verification_loop>

<action_safety>
Stay within scope. Do not perform unrelated cleanup. Do not run git add, commit, push, merge, rebase, reset, clean, or open/update a PR. Do not modify repository or deployment settings. Do not invoke another Claude/Codex agent. Leave changes uncommitted for Codex to review.
</action_safety>

<final_report>
End with:
1. Root cause and implementation summary
2. Files changed and why
3. Exact gate outcomes with useful counts
4. Visual evidence produced and inspected
5. Cleanup performed
6. Deviations, unresolved questions, and decisions Codex should review
</final_report>
```

## Delta brief for resumption

Keep follow-ups short because the session retains its history:

```xml
<review_delta>
Keep the existing implementation unless this evidence requires changing it.

New evidence or review defect:
Required correction:
Gates to rerun:

Inspect the current worktree first. Preserve valid existing edits, complete cleanup, leave the tree uncommitted, and return the same final report contract.
</review_delta>
```

## Dynamic workflow additions

For multi-agent orchestration, add these blocks. See
[dynamic-workflows.md](dynamic-workflows.md) for the mechanics.

```xml
<orchestration_optin>
I am explicitly opting in to multi-agent orchestration. Use the `Workflow` tool.
Do not hand-roll sequential Task calls and do not do this work inline in the main loop.
</orchestration_optin>

<workflow_shape>
Author a script whose first statement is `export const meta = {...}` (pure literals only)
with name, description, and phases.

Topology: pipeline() over ITEMS with these stages, or parallel() if a barrier is required.
  Stage 1 (phase: '...'): agent() that ... , schema { FIELDS }
  Stage 2 (phase: '...'): agent() receiving stage 1's result, schema { FIELDS }

May a stage read files other than the one it was given? State yes or no explicitly.

Return an aggregate object so the main loop can read it.

The VM rejects the script before launch if it uses Date.now(), Math.random(), argless
new Date(), import(), require, process, or fetch. Keep it deterministic; pass timestamps
via args.
</workflow_shape>

<workflow_report>
Report, in order: the verbatim final script; runId, absolute scriptPath, and transcript
directory; the exact returned JSON (read the full output file if the notification says it
was truncated); agent count, subagent tokens, duration; the model each agent actually ran
on; and any rejection or correction on your first attempt, quoted verbatim.

I will check these claims against journal.jsonl myself.
</workflow_report>
```

To run a workflow Codex authored, install it at `~/.claude/workflows/<name>.js` and
replace `<workflow_shape>` with an instruction to invoke `name: <meta.name>` with the
given `args`, and not to re-author the script.

## Visual bug additions

For screenshot-driven work, explicitly state:

- whether the attachment is expected, actual, or both;
- CSS pixel viewport, device scale factor, browser, and light/dark mode;
- keyboard visibility, browser chrome, safe-area, scroll direction, and overlay state;
- what must remain unchanged on desktop or other breakpoints;
- the before/after screenshot names and where to save them.

Require the implementer to reproduce first and Codex to inspect the final pixels independently.
