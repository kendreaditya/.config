---
name: gemini
description: Gemini CLI for one-shot Q&A, summaries, generation, and large-context codebase analysis (1M token window). Use for quick questions or feeding entire directories to Gemini.
homepage: https://ai.google.dev/
metadata:
  {
    "openclaw":
      {
        "emoji": "✨",
        "requires": { "bins": ["gemini"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "gemini-cli",
              "bins": ["gemini"],
              "label": "Install Gemini CLI (brew)",
            },
          ],
      },
  }
---

# Gemini CLI

## Quick Start

```bash
# One-shot Q&A (non-interactive)
gemini -p "What is the capital of France?"

# With a specific model
gemini -m gemini-3-flash-preview -p "Explain quicksort"

# JSON output
gemini -p "Return a JSON list of planets" -o json
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-p`, `--prompt` | Non-interactive (headless) mode — required for scripting |
| `-i`, `--prompt-interactive` | Run prompt then continue in interactive mode |
| `-m`, `--model` | Select model (see Models below) |
| `-o`, `--output-format` | `text` (default), `json`, `stream-json` |
| `-y`, `--yolo` | Auto-approve all tool calls (use with caution) |
| `--approval-mode` | `default`, `auto_edit`, `yolo`, `plan` (read-only) |
| `-s`, `--sandbox` | Run in sandbox |
| `-r`, `--resume` | Resume a previous session (ID or `latest`) |
| `--list-sessions` | List available sessions |
| `--include-directories` | Add extra directories to workspace |
| `--policy` | Additional policy files/directories |
| `-e`, `--extensions` | Limit which extensions are used |
| `-l`, `--list-extensions` | List all available extensions |
| `--screen-reader` | Accessibility mode |

## Subcommands

```bash
gemini mcp                   # Manage MCP servers
gemini extensions <command>  # Manage extensions
gemini skills <command>      # Manage agent skills
gemini hooks <command>       # Manage hooks
```

## Models

Default to **Flash** — fast and handles most tasks well. Use Pro for deeper reasoning.

| Model | Flag | Use case |
|-------|------|----------|
| Flash (default) | `-m gemini-3-flash-preview` | General tasks, large context |
| Pro | `-m gemini-3.1-pro-preview` | Complex reasoning, architecture |
| Flash-Lite | `-m gemini-3.1-flash-lite-preview` | High-volume, fastest, cheapest |

Check latest available models:

```bash
~/.claude/skills/gemini/scripts/gemini-smart.sh
```

## Large Context Analysis (1M tokens)

Gemini's 1M token context window is ideal for analyzing entire codebases. Use `@path` syntax to include files/directories in the prompt.

### When to use large context

- Analyzing entire codebases or large directories (100KB+)
- Comparing multiple large files simultaneously
- Project-wide pattern discovery or architecture review
- Security audits, test coverage analysis across many files

### File/directory inclusion

```bash
# Single file
gemini -m gemini-3-flash-preview -p "@src/main.py Explain this file"

# Multiple files
gemini -m gemini-3-flash-preview -p "@package.json @src/index.js Analyze dependencies"

# Entire directory (recursive)
gemini -m gemini-3-flash-preview -p "@src/ Summarize architecture"

# All project files
gemini -m gemini-3-flash-preview --all-files -p "Project overview"

# Multiple directories
gemini -m gemini-3-flash-preview -p "@src/ @tests/ Analyze test coverage"
```

### Example patterns

```bash
# Architecture analysis
gemini -m gemini-3.1-pro-preview -p "@src/ Describe overall architecture, key modules, data flow, and external dependencies"

# Security audit
gemini -m gemini-3.1-pro-preview -p "@src/ @api/ Review for input validation, auth patterns, injection risks"

# Test coverage
gemini -m gemini-3-flash-preview -p "@src/ @tests/ Which modules lack tests? What edge cases are missing?"

# Save long output
gemini -m gemini-3-flash-preview -p "@src/ Full analysis" > analysis.md
```

## Authentication

```bash
# Google OAuth (free tier: 60 req/min, 1000/day)
gemini  # Follow OAuth flow on first run

# Or use API key
export GEMINI_API_KEY="your-key"
```

## Notes

- Always use `-p` for non-interactive/scripted usage
- Always add `-y` when the prompt references files via `@path` or when Gemini may need tools (file reads, shell commands) — without it, tool calls silently fail in non-interactive mode
- Piping file content via stdin (`cat file.md | gemini -p "..."`) is a reliable alternative to `@path` for single files
- Avoid `--yolo` for untrusted/dangerous tool calls, but it's safe and necessary for read-only file analysis
- The keychain warning (`Cannot find module keytar.node`) is cosmetic — file-based fallback works fine
- Non-interactive mode has no tool approval flow (read-only effectively)
