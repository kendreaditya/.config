# Claude Code CLI and sessions

Treat the locally installed CLI help as authoritative because flags and model aliases change. Run:

```bash
claude --version
claude auth status
claude --help
claude agents --help
```

## Important meanings

- `-p` / `--print` means non-interactive print mode. It does not mean parallelism or model selection.
- `--model opus` is an alias, not proof of the effective model version. Read the stream init/result events and `modelUsage`.
- `--output-format json` emits one terminal object and can appear silent for a long agentic run.
- `--output-format stream-json --verbose` is better for supervision and durable event capture.
- `--resume <session-id>` resumes a specific conversation. Prefer it over `--continue` when multiple sessions exist in one directory.
- `--continue` selects the most recent conversation for the current directory and is only safe when unambiguous.
- `--fork-session` keeps context but creates a new session ID. Use it when branching an investigation, not for ordinary rework on the same tree.
- `--session-id <uuid>` preselects an ID for a fresh run. Record it if used.
- `--worktree [name]` lets Claude create a worktree, but explicit orchestrator-created worktrees usually make branch and cleanup ownership clearer.
- `--bg` and `claude agents --json` provide native background-session management in current releases. Check the installed help and validate compatibility with the chosen print/output mode before relying on them; older Claude versions and relays may not support the same combination.
- `--bare` skips normal `CLAUDE.md` discovery and OAuth/keychain behavior. Do not use it for ordinary repository delegation.

## Permission selection

Use a normal write-capable permission mode unless the human explicitly accepts bypassing checks. The bundled runner defaults to `acceptEdits` with a restricted built-in tool surface and MCP/skill discovery disabled. Repository and managed settings can still change the effective behavior.

`--dangerously-skip-permissions` bypasses Claude permission checks. It is not a generic automation flag. Use it only when the human explicitly authorized it for this task and the target directory is trusted. State the action to the human before launching. The worktree is not an OS security boundary, and direct file tools may reach outside it.

For read-only diagnosis, invoke Claude directly with a read-only tool set and plan permission mode, or extend the runner only after inspecting its help and code. A git status snapshot is an attribution aid, not proof of OS-level read-only behavior because hooks and unrelated processes can still write.

## Direct runner examples

Fresh bounded task:

```bash
python3 <skill-dir>/scripts/run_claude.py \
  --workdir /path/to/clean-worktree \
  --brief /path/outside/repo/brief.md \
  --out-dir /path/outside/repo/artifacts/task-01 \
  --model opus --effort high --max-budget-usd 20
```

Explicitly authorized bypass:

```bash
python3 <skill-dir>/scripts/run_claude.py \
  --workdir /path/to/clean-worktree \
  --brief /path/outside/repo/brief.md \
  --out-dir /path/outside/repo/artifacts/task-01 \
  --model opus --effort high --dangerously-skip-permissions
```

Resume the same task:

```bash
python3 <skill-dir>/scripts/run_claude.py \
  --workdir /path/to/worktree \
  --brief /path/to/delta-brief.md \
  --out-dir /path/to/artifacts/task-01-review-02 \
  --resume SESSION_ID --model opus --effort high --allow-dirty
```

`--allow-dirty` is expected for a resumed implementation because the original edits are the recovery state. Do not use it to hide unrelated pre-existing dirt on a fresh task.

## Artifacts and result fields

The runner stores artifacts outside the repository:

- `brief.md`: exact prompt sent over stdin;
- `events.jsonl`: raw Claude stream events;
- `stderr.txt`: complete CLI stderr;
- `final.txt`: terminal final message when available;
- `result.json`: runner status, session, model, cost/usage, before/after git state, command metadata, and artifact paths.

Use `scripts/inspect_result.py /path/to/result.json` for a compact report. Inspect the raw files when the status is not cleanly completed or the final message is missing.

## Model and effort

Respect an explicitly requested model. If the human asks for “Opus,” pass `--model opus`; do not silently substitute another family. Choose effort proportional to the task and supported by the installed model. Avoid pinning a dated model name unless the user or repository requires reproducibility.

Report both the requested alias and the effective model parsed from Claude events. If no effective model is present, say it was not verified.
