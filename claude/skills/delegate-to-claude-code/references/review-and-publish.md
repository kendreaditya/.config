# Review and publish

Claude performs implementation; Codex owns acceptance and publication unless the human explicitly changes that boundary.

## Inspect the complete tree

Run:

```bash
git status --short
git diff
git diff --cached
```

Open every untracked file; ordinary `git diff` omits them. Inspect ignored task artifacts if they could affect behavior. Confirm the branch and base commit are the ones recorded in the ledger.

Compare the tree with the brief for both scope creep and missing scope. Search relevant call sites and invariants instead of reviewing only the files named in Claude's report.

## Review tests before trusting green gates

Treat these as defects unless explicitly required:

- deleted, skipped, disabled, or commented-out tests;
- weakened assertions or broader tolerances/errors;
- mocks replacing the behavior being tested;
- fixture-specific hardcoding or success-only fallbacks;
- duplicate tests that add volume without new behavior coverage.

Rerun exact repository gates yourself. A reported green test is a claim until Codex sees the final-tree result.

## Review generated code skeptically

Check for:

- broad catches or silent defaults that hide failure;
- APIs, flags, packages, or browser behavior absent from installed versions;
- unused helpers, unreachable branches, or scaffolding comments;
- new state, client, styling, logging, or error patterns beside established ones;
- unnecessary abstractions, options, dependencies, or configuration;
- cleanup that crossed the brief's boundary;
- direct staging, commits, pushes, PR edits, or repository-setting changes.

Send correctable findings to the same session with a delta brief. Review the revised tree from scratch.

## Visual verification

For UI work:

1. reproduce the exact route/state at the specified viewport, theme, scroll, keyboard, overlay, and player state;
2. compare before and after, not only a happy-path screenshot;
3. inspect the image itself, including clipping, alignment, safe areas, stacking, and content beneath overlays;
4. verify required non-regressions on desktop and adjacent breakpoints;
5. keep screenshots outside tracked source unless the repository intentionally stores PR evidence;
6. attach only images that actually show the corrected state, using the repository's PR process.

Do not accept a screenshot Claude says it captured without opening and checking it.

## Cleanup

Before committing:

- stop only task-created preview/test/browser processes;
- remove task-created temporary scripts, settings, configs, downloads, and generated screenshots that do not belong in source;
- keep external run artifacts until the PR is accepted or recovery is no longer needed;
- confirm the worktree contains only intended changes.

## Publish deliberately

After independent verification:

1. stage explicit intended paths;
2. commit with a scoped message;
3. push the task branch;
4. open or update the correct PR using the applicable GitHub workflow;
5. include test outcomes and verified screenshots;
6. check CI, deployment preview, mergeability, and review feedback as requested.

Do not combine independent delegated tasks into one commit or PR merely because they ran together. Preserve the one-task/one-worktree/one-review-unit mapping.

## Final report

Report:

- implementation and root cause;
- what Codex independently checked;
- exact tests/builds and visual states;
- effective Claude model and permission mode;
- commit and PR links;
- remaining limitations or decisions.

Distinguish `implemented`, `verified`, and `published`; they are separate states.
