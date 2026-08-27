# cra — Code Review Agent

A Greptile-style AI code review agent that runs as a **Claude Code Agent Skill**. No webhook server, no separate API runtime — it leverages Claude Code's existing agentic loop and the `Read`/`Grep`/`Bash`/`Agent` tools as its retrieval engine.

## What it does

Reviews a GitHub pull request with the rigor of Greptile:

- **Whole-codebase context.** Walks callers/callees/type references across files using Claude Code's `Grep` + `Read`, not just the diff.
- **Priority taxonomy.** Every comment is P0 (security/breakage), P1 (logic bug), or P2 (style/nit). No "type" axis.
- **Confidence verdict (0–5).** One opinionated number you can gate on. 0 = malicious/injection detected.
- **PR title, body, README, and `.codereview/rules.md` are authoritative context** — not flavor text.
- **Dedicated Security Review section** when prompt-injection or secrets are detected.
- **Resists embedded instructions** in source, README, or PR body.
- **Conditional Mermaid diagrams** (sequence for cross-component flows, flowchart for branching).
- **Two-stage filter:** Opus 4.7 main reviewer → Haiku post-filter that drops nits without rule basis.

## Why it works

Claude Code already has:

- `Read` — read any file
- `Grep` — ripgrep-based search across the repo
- `Bash` — run any shell command (git, gh, anything)
- `Agent` — spawn a Haiku subagent for the post-filter

That's the entire retrieval + agentic loop. cra is just **a system prompt + 4 helper scripts** that turn Claude Code into Greptile-shaped output.

## Install

cra lives in [kendreaditya/.config](https://github.com/kendreaditya/.config) as a
plain skill directory. It previously had its own repo (`kendreaditya/cra`, now
archived); that indirection meant `.config` could only track an absolute symlink,
which broke on any other machine.

```bash
# if you already clone the whole config repo, cra comes with it
git clone https://github.com/kendreaditya/.config ~/.config

# standalone: copy the skill directory into Claude Code's skill path
git clone https://github.com/kendreaditya/.config /tmp/kconfig
cp -R /tmp/kconfig/claude/skills/cra ~/.claude/skills/cra
```

Restart your Claude Code session and you should see `cra` in the skill list.

Dependencies (already on most systems):
- `gh` CLI, authenticated (`gh auth status`)
- `git`
- `python3` (uses your `~/workspace/.venv` per the user's CLAUDE.md convention; adjust paths in `SKILL.md` if different)

## Use

Four input modes:

| What you want to review | Invocation | Notes |
|---|---|---|
| A GitHub PR | `/cra https://github.com/owner/repo/pull/42` | Default; clones into `~/.cache/cra/` |
| A PR in the current repo | `/cra 42` | Shorthand |
| Your branch vs `main` | `/cra --local` | Auto-detects upstream/origin/main; override with `--base <ref>` |
| Working-tree + staged | `/cra --uncommitted` | Everything dirty vs `HEAD` — great pre-commit gate |
| Only staged changes | `/cra --staged` | Index vs `HEAD` — what's about to be committed |
| Only unstaged changes | `/cra --unstaged` | Working tree vs index |

Or speak naturally — Claude Code routes things like *"review this PR"*, *"review my branch vs main"*, *"review my uncommitted changes"* to the right mode.

By default it prints the rendered review to your terminal (**dry-run**). To actually post the comment to GitHub (PR mode only):

```
/cra https://github.com/owner/repo/pull/42 --post
```

`--post` is a no-op in local modes (there's no PR to post to) — the rendered review just stays on stdout.

## Layout

```
skill/
├── SKILL.md                          # entry point — the skill protocol
├── prompts/
│   ├── reviewer-system.md            # the 12 design opinions baked in as a system prompt
│   ├── reviewer-output-schema.md     # the JSON the reviewer must emit
│   ├── post-filter.md                # Haiku noise-filter prompt
│   └── security-rubric.md            # what counts as a security finding
├── scripts/
│   ├── prep.py                       # PR URL → JSON bundle (diff + metadata + context files)
│   ├── render.py                     # review JSON → Markdown/HTML body
│   └── post.py                       # gh pr comment (or --dry-run)
└── examples/
    └── sample-output.md              # canonical expected output for a B1 off-by-one PR
```

## Custom rules

Drop a `.codereview/rules.md` (or `.greptile/rules.md`, `.cra/rules.md`) at the root of any repo:

```
# Custom review rules

1. Any `console.log` in production code is P0.
2. Async functions must end in `Async`.
3. SQL via template strings is allowed only under `src/db/migrations/`.
```

cra reads these at review time (no re-index) and applies them.

## Architecture notes

This repo is the output of reverse-engineering Greptile in May 2026 — see `~/workspace/greptile-reveng/findings.md` for the methodology and metadata we extracted. The 12 design opinions in `prompts/reviewer-system.md` are exactly the opinions Greptile bakes in. We just made them OSS and let Claude Code be the runtime.

Greptile uses Opus 4.5 + a per-language SCIP indexer + Anthropic prompt-cache holding the per-PR retrieval set. cra uses Opus 4.7 (whatever Claude Code is running) + Claude Code's Grep/Read as the indexer + lets Anthropic's automatic prompt cache do its thing. For small/medium repos this is plenty; for >10k-file repos, a tree-sitter + sqlite-vec index (`scripts/index.py`, deferred) is the upgrade path.

## Limitations (v1)

- **Single summary comment**, not inline review comments. (GitHub's inline comment API requires line-mapping math we haven't done yet.)
- **No persistent team memory.** Greptile has a `linkedMemory` per comment tied to a custom-context DB that learns from upvotes/downvotes. We don't yet.
- **No SCIP-based indexer.** Grep is the retrieval mechanism. For Go/Python/TS/Java specifically, dropping in Sourcegraph's `scip-*` indexers is the natural upgrade.
- **Single-round reviews.** No multi-round routing where re-reviews use a different prompt template.

## License

MIT (TBD on commit).
