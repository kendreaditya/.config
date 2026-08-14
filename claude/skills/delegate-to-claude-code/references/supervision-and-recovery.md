# Supervision and recovery

## Parallel runs

Parallelize only independent tasks. Give each run:

- a distinct worktree and branch from the intended base;
- a separate brief and Claude session;
- a separate artifact directory;
- unique preview/test ports;
- its own acceptance gates and eventual commit/PR;
- a ledger entry mapping all of the above.

Never share a mutable worktree between implementers. If tasks depend on one another, run them sequentially and land each verified unit first.

For more than two tasks, keep a progress ledger outside the repository:

| Task | Worktree | Branch/base | Session | Model/mode | Port | Artifact result | State | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

States should distinguish `queued`, `running`, `review`, `rework`, `verified`, `published`, and `blocked`.

## Determine activity, not merely elapsed time

Single-object JSON mode can produce no visible output until completion. Even stream mode can be quiet during tool execution. Before calling a run stalled, inspect:

1. the exact runner and Claude PIDs;
2. child processes such as tests, browsers, compilers, or servers;
3. `events.jsonl` and `stderr.txt` growth;
4. worktree status, diff, and recent modification times;
5. assigned port ownership and HTTP health;
6. system resource pressure if a child appears wedged.

Use a stall threshold based on no process, artifact, filesystem, or service activity—not blank stdout alone. Keep the human updated while waiting.

## Resolve a stuck child precisely

If a dev server or browser blocks progress:

1. inspect the exact port (`ss`, `lsof`, or platform equivalent);
2. map it to the owning PID and command;
3. confirm it belongs to this delegated run;
4. terminate only that exact child, starting with a graceful signal;
5. preserve the parent Claude process when it can recover;
6. tell the resumed session what changed if necessary.

Never kill a broad process name or an unrelated service. A familiar port may belong to another project.

## Recover an interrupted session

After Ctrl-C, timeout, host tool failure, or lost terminal output:

1. Do not reset or clean the worktree.
2. Read the run's `result.json`; if absent, inspect `events.jsonl` for the last `system/init` or `result` session ID.
3. Inspect git status, unstaged/staged diffs, untracked files, and task-created processes.
4. Decide whether the implementation is partial, complete without a report, or premise-invalid.
5. Resolve the exact environmental blocker.
6. Resume the recorded session ID with `--allow-dirty` and a delta brief.

Suggested recovery delta:

```xml
<recovery_delta>
The previous invocation was interrupted while preserving its worktree. Inspect the existing diff and artifacts before editing. Keep valid work, complete the original acceptance criteria and remaining gates, remove only task-created temporary processes/files, leave the tree uncommitted, and return the original structured final report.

Known interruption or new evidence:
</recovery_delta>
```

If no session ID survives, start a new session with a recovery brief that explains the existing diff; do not pretend it is a clean implementation.

## Incorporate review feedback or screenshots

Resume the same session when the new input is about the same implementation. Attach or cite the new screenshot path, explain exactly what it proves, and ask Claude first to reproduce or measure the discrepancy. Do not ask it to rewrite working code blindly.

When a PR base changed or conflicts appeared, first update the worktree safely and understand the semantic conflict. Then resume with the new base/diff context if implementation judgment is needed. Codex remains responsible for reviewing and publishing the resolved result.

## Stop conditions

Stop and ask the human when:

- the correct fix materially expands scope or authority;
- bypass permissions, network access, deployment, or external writes are newly required;
- repository evidence contradicts the requested behavior;
- parallel tasks are no longer independent;
- continuing risks user changes or unrelated host processes.

Report the preserved worktree, session ID, artifacts, completed work, and precise open decision.
