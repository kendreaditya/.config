---
name: upstream
description: "Track vendored Claude Code components against their source and re-sync them without losing local edits. Use when the user asks whether a vendored skill/agent/command is out of date, wants to pull upstream changes, asks what they changed in a borrowed component, or is about to copy someone else's skill/agent/plugin file into their config. Triggers: 'upstream', 'is this out of date', 'sync my skills', 'pull upstream changes', 'what did I change in this skill', 'vendor this'."
---

# upstream

Copied someone else's skill, agent, or command into `~/.config/agents/`? This tracks
where it came from and re-syncs it later, keeping your local edits.

The pinned commit sha **is** the merge base — the base text is fetched from GitHub on
demand, so there is no cached copy to go stale. Nothing is stored but the pointer.

## The metadata

Add an `upstream:` block to the component's frontmatter:

```yaml
---
name: wayfinder
description: "…"
upstream:
  repo: mattpocock/skills
  path: skills/engineering/wayfinder/SKILL.md
  ref: main
  sha: 321658273cb1d20b76026717d027d505790106d4
  license: MIT
  checked: 2026-08-22
  content_hash: fee6e1d0c5…
---
```

`sha` is what your copy is based on. `content_hash` is the hash of *pristine upstream
at that sha*, so comparing your file against it detects local edits with no network
call. `ref` is the branch to watch for new commits.

This block is the only registry. `upstream.sh` finds tracked components by grepping
for it, so there is no manifest to drift out of sync.

## Usage

```bash
S=~/.config/agents/skills/upstream/scripts/upstream.sh

$S list                    # every tracked component + clean/edited
$S status                  # check upstream for new commits
$S diff  <abs-path>        # what have I changed vs my pinned base
$S pull  <abs-path>        # sync one
$S pull  --all             # sync everything that moved
```

Pass absolute paths. Exit is nonzero when a merge conflicts.

## How a sync decides

Four cases. Only the last one merges.

| local | upstream | what happens |
|---|---|---|
| clean | same sha | nothing — one API call |
| clean | moved | overwrite; no conflict is possible |
| edited | same sha | nothing |
| edited | moved | three-way merge, base fetched at pinned sha |

On conflict you get `--diff3` markers showing your version, the base, and theirs —
so you can see what each side actually did. Resolve, then re-run `status`.

## What can be tracked

Any file-based component. `upstream.sh` scans `skills/`, `agents/`, `commands/`,
`output-styles/`, `hooks/`, `rules/`, and `themes/`.

Claude Code's authorable component types, for reference:

| Component | Lives in | What it is |
|---|---|---|
| Skills | `skills/<name>/SKILL.md` | Task instructions, loaded on trigger |
| Agents | `agents/<name>.md` | Subagents with own prompt, model, tools |
| Commands | `commands/<name>.md` | `/name` slash commands |
| Output styles | `output-styles/<Name>.md` | Modifies the system prompt session-wide |
| Hooks | `settings.json` + scripts | Fire on lifecycle events |
| Rules | `rules/*.md` | Instructions scoped to file globs |
| MCP servers | `.mcp.json` | External tool servers |
| LSP servers | plugin manifest | Language servers |
| Monitors | plugin manifest | Persistent background processes |
| Themes | `themes/*.json` | Colors, shown in `/theme` |
| Statusline | `settings.json` | Custom status line command |
| Keybindings | `keybindings.json` | Key remaps and chords |
| Workflows | `workflows/*.js` | Scripted multi-agent orchestration |
| Memory | `CLAUDE.md`, `memory/` | Persistent context |
| Plugins | `plugins/` | Bundles of all the above, versioned |

Plugins are the packaged alternative to vendoring: they auto-update, but you take
every component in the bundle. Vendor when you want three skills out of twenty.

## Pitfalls

- **Needs `gh` authenticated.** Private repos work if your token can read them.
- **Force-pushed or rebased base.** If the pinned sha is gone the base fetch fails;
  the tool refuses to merge and tells you to `diff` manually rather than guessing.
- **Line-based merge.** A wholesale upstream restructure conflicts loudly. Correct —
  you should read that one.
- **`content_hash` is optional.** Without it, state is derived by fetching the base,
  which costs a call per component. `pull` writes it, so it self-heals.
- Only the first `upstream:` block in frontmatter is read; a fenced example in the
  body is ignored.

## Verification

```bash
~/.config/agents/skills/upstream/scripts/upstream.sh list
```

Tested against `mattpocock/skills` across all four cases: clean overwrite, clean
merge preserving a local addition, same-line conflict producing `--diff3` markers,
and a no-op second pull.
