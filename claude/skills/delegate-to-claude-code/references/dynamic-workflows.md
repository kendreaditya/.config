# Dynamic workflows

Claude Code's `Workflow` tool runs a JavaScript orchestration script inside a `vm`
sandbox, fanning out `agent()` calls to subagents. Codex has no equivalent tool, so
delegate the execution. Everything here was verified against Claude Code 2.1.226.

## Decide who authors the script

There are three invocation forms, and the choice is a permissions decision, not a
style preference.

| Form | Who writes the logic | Approval behavior |
|---|---|---|
| `script` (inline) | Claude, from your brief | Launches with no prompt under `-p` |
| `scriptPath` | Codex | **Always** asks; cannot be allow-listed |
| `name` | Codex | Allow-listable; launches with no prompt |

The `scriptPath` gate is structural, not a heuristic. In `checkPermissions`, the rule
lookup key is `e.scriptPath ? undefined : e.name`, so when `scriptPath` is set no
`allow` rule can ever match and the tool falls through to
`behavior: "ask"` with `"Review dynamic workflow before running"`. Under `-p` there is
no human to approve, so the run stalls. Additionally `toAutoClassifierInput` returns
only the path string, so in `auto` permission mode the classifier sees a request to
execute code it cannot read and may deny it outright as untrusted code integration.

**Therefore:**

- Let **Claude author** the script when the task is exploratory. Cheapest, no gate.
- Have **Codex author** it when the orchestration logic itself is the deliverable
  (fixed branch conditions, exact schemas, reproducible topology). Install it as a
  **named** workflow, never pass `scriptPath` to a `-p` session.

To install a Codex-authored workflow as named: write the file to
`~/.claude/workflows/<name>.js` (or `<project>/.claude/workflows/`). It must have a
`.js` extension — `.mjs`, `.cjs`, and `.ts` are counted as near-misses and skipped —
be under 524288 bytes, and carry a valid `meta` block. `meta.name` is the invocation
name and must match what the brief tells Claude to call. Then brief Claude with
`name: <meta.name>` plus `args`. Verified: launches immediately, no gate, and the
persisted copy is byte-identical (sha256) to the Codex original.

## Script contract

`export const meta = {...}` must be the literal first AST node, a pure literal
(no variables, calls, spreads, or template interpolation). `name` and `description`
are required; `whenToUse` and `phases:[{title,detail,model?}]` are optional. The rest
of the file is the script body.

Injected globals: `agent, args, budget, parallel, phase, pipeline, workflow, log,
console, Date, setTimeout, clearTimeout`. There is no `require`, `process`, or `fetch`.

- `agent(prompt, opts?)` -> `Promise`. opts: `label, phase, schema, model, effort,
  isolation:'worktree', agentType`. Resolves `null` on skip/error; **never rejects**,
  so a partly failed run looks successful. Pass `schema` (JSON Schema) to force the
  subagent through a validated `StructuredOutput` call.
- `pipeline(items, ...stages)` — **no barrier between stages**; item 1 can reach
  stage 2 while item 3 is still in stage 1. Stage callback receives
  `(prevResult, originalItem, index)`. A throwing stage drops that item to `null`.
  This is the right default for per-item fan-out.
- `parallel(thunks)` — barrier; failures become `null` entries; never rejects.
- `workflow(nameOrRef, args?)` — nests **one level only** and **does reject**, so
  wrap it in try/catch.
- `budget: {total, spent(), remaining()}` — hard ceiling; `agent()` throws when spent.
  With no budget set, `remaining()` is `Infinity`, which serializes to `null`.

Determinism is enforced twice: a static pre-scan rejects `Date.now()`,
`Math.random()`, argless `new Date()`, and `import()` **before** launch, and runtime
traps catch computed-access bypasses. `new Date(0)` is allowed. Pass timestamps
through `args` instead.

Limits: concurrency `min(16, cores-2)`; 1000 agents per run; 4096 items per
`pipeline`/`parallel` call; script cap 524288 bytes.

## Model selection is a real trap

`--model opus` on the parent does **not** set the workflow subagent model, and neither
does `opts.model` if the environment overrides it. On a machine with
`CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5[1m]` in `~/.claude/settings.json`, a
script requesting `model: 'opus'` produced `agent-*.meta.json` files recording
`"model": "opus"` while **every actual API call in `agent-*.jsonl` was
`us.anthropic.claude-sonnet-5`**.

`meta.json` records what was *requested*; the transcript records what *ran*. Verify
the transcript, and check `CLAUDE_CODE_SUBAGENT_MODEL` during preflight before
promising anyone an Opus review.

## Verify from the journal

```bash
D=~/.claude/projects/<slug-cwd>/<sessionId>/subagents/workflows/<runId>
python3 -c "
import json
for l in open('$D/journal.jsonl'):
    d=json.loads(l)
    if d['type']=='result': print(d['key'][:20], json.dumps(d['result'])[:300])
"
```

`journal.jsonl` holds one `started` and one `result` per agent, keyed
`v2:<sha256(prompt,opts)>`; it is the only reliable record of what each agent actually
returned. The persisted script is at
`<sessionId>/workflows/scripts/<name>-<runId>.js` — diff it against your original.
Check `agents_done`/`agents_error`/`agents_skipped`, and confirm branch-skipped items
came from your script's logic rather than the runtime.

## Resume and iterate

The tool result carries a `runId` (`wf_<hex>-<3>`). Relaunch with
`Workflow({scriptPath, resumeFromRunId})` — resume is the one case where `scriptPath`
is expected, but it needs an interactive approval, so plan for it. The longest
unchanged prefix of `agent()` calls returns from cache instantly; the first
edited/new call and everything after runs live. Same script plus same args is a 100%
cache hit. Resume is same-session only.

## Enablement preflight

Confirm before promising a workflow: `disableWorkflows` absent from user and managed
settings; `CLAUDE_CODE_DISABLE_WORKFLOWS` unset; `Workflow` not in the permissions
deny list; no `--safe-mode`. Also check `CLAUDE_CODE_SUBAGENT_MODEL` as above.

Codex cannot interpose on a child's tool calls mid-run — there is no `PreToolUse` veto
once `claude -p` is running. Everything else is reachable through the brief.

## Worked example

[../workflows/example-triage-then-deep-dive.js](../workflows/example-triage-then-deep-dive.js)
is a Codex-authored script that was run and verified end to end. It takes
`args.root` and `args.files`, triages each file with a cheap agent, and deep-dives only
the ones classified `high` — so the branch decision belongs to the script, not to a
model's judgment.

To use it: copy it to `~/.claude/workflows/codex-authored-triage.js`, then brief Claude to
invoke `name: codex-authored-triage` with `args: { root, files }`. Verified run
`wf_32a44248-256`: launched with no approval prompt, persisted copy byte-identical to the
original (sha256 `5683b6ef…835c3e`), 5 agents, 1 file correctly skipped by the script's own
branch. Its `model: 'opus'` request was recorded in `meta.json` but overridden to Sonnet by
`CLAUDE_CODE_SUBAGENT_MODEL` — the exact trap described above.
