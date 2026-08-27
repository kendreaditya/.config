---
name: shortn
description: "Compress text/markdown files to fit within a specified token limit using extractive summarization with per-section TextRank (no LLM required, no API cost). Use when the user asks to: compress a file to N tokens, shrink context, reduce a doc to fit a context window, summarize to token budget, fit into Claude/GPT/LLM context. Also use proactively when Claude's own task context contains oversized reference files that could be compressed before ingestion. Triggers: 'shortn', 'compress to N tokens', 'shrink this file', 'fit this in X tokens', 'summarize to token limit', 'reduce tokens', 'compress context'."
---

# shortn

Extractive text compressor for LLM context. Fits a large file into a target token budget via per-section TextRank summarization. Local, deterministic, no API cost.

## Usage

```bash
shortn input.md -t 8000                    # → input.compressed.md
shortn input.md -t 32000 -o out.md         # specify output
shortn input.md -t 8000 --stdout           # print instead of writing
cat input.md | shortn -t 8000 --stdin --stdout
```

Flags that matter:
- `-t TOKENS` (required) — target token limit
- `-o PATH` — output file (default: `<input>.compressed.md`)
- `--stdout` — emit to stdout
- `--stdin` — read from stdin
- `--model MODEL` — tiktoken encoding (default `cl100k_base`, matches GPT-4/Claude roughly)
- `-v` / `-q` — verbose / quiet
- `--no-parallel` — disable multi-process (useful for small files or debugging)

## How it works

1. Splits input on markdown headings to get sections.
2. Within each section, splits into sentences and scores with TextRank (word-overlap graph, no embeddings).
3. Keeps top-ranked sentences per section until the global token budget is met, preserving section order.
4. Never hallucinates — output is a strict subset of input sentences.

## When to use it

- User has a huge doc (API reference, dump, transcript) and wants to feed it into an LLM with a smaller context window.
- Claude itself is about to read a reference file that's too big — compress it first, then read.
- Batch-shrinking multiple files to the same budget.

## When NOT to use it

- Code files — extractive summarization breaks syntax. Use a different tool.
- Content where ordering/flow matters more than facts (narrative prose, instructions with prerequisites).
- Cases where you need the *meaning* rephrased — this is extractive, not abstractive. For paraphrased summaries, use an LLM directly.

## Gotchas

- Requires `tiktoken` in the `~/.config/config-venv` venv. Already installed; `_utils.ensure_config_venv()` handles re-exec.
- Token counts are estimates — actual LLM tokenization may differ by ~5%. Budget with headroom.
- Parallel mode (default) uses `ProcessPoolExecutor`; if the process tree is already in a pool, pass `--no-parallel`.
