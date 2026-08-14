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

## Visual bug additions

For screenshot-driven work, explicitly state:

- whether the attachment is expected, actual, or both;
- CSS pixel viewport, device scale factor, browser, and light/dark mode;
- keyboard visibility, browser chrome, safe-area, scroll direction, and overlay state;
- what must remain unchanged on desktop or other breakpoints;
- the before/after screenshot names and where to save them.

Require the implementer to reproduce first and Codex to inspect the final pixels independently.
