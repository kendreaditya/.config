# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Personal dotfiles and CLI research tools for macOS. The primary value is the custom scripts in `scripts/` — CLI utilities that extract web, YouTube, and Twitter content to Markdown for LLM analysis. Secondary purpose is macOS/Linux/Windows environment setup automation.

## Scripts Architecture

All scripts are installed to `~/.local/bin` via symlinks from `scripts/`. They share a common Python venv at `~/.config/config-venv/`.

### Shared Modules (imported by other scripts)
- `scripts/_utils.py` — `ensure_config_venv()` (re-executes in venv), `ProgressLogger` (Rich progress bars), `MarkdownWriter` (buffered writes)
- `scripts/_context.py` — `split_sentences()`, `count_tokens()`, `get_tokenizer()` (tiktoken wrappers)

Every Python script calls `ensure_config_venv()` at the top to auto-switch to the venv.

### Main Tools
- **`wcb`** — Async web scraper; converts sites to LLM-optimized markdown. Uses aiohttp + BeautifulSoup + markdownify. Supports depth control, subdomain filtering, optional Playwright browser.
- **`yt-research`** — Downloads YouTube channel/search transcripts to Markdown via yt-dlp. Supports @channel syntax and search queries.
- **`shortn`** — Compresses markdown to a token limit using TextRank (Jaccard similarity). No LLM calls — pure algorithmic summarization.
- **`tw-research`** — Scrapes Twitter/X user timelines to Markdown via twscrape.
- **`url`** (bash) — Generates HTML redirect files for URLs.

## Common Commands

### Setup
```bash
# macOS dev environment (Homebrew, Oh My Zsh, symlinks, system defaults)
./setup-macos.sh

# Install/update Python dependencies
source ~/.config/config-venv/bin/activate
pip install -r requirements.txt
```

### Running Scripts
```bash
# Scripts are on PATH after setup; run directly:
wcb https://docs.example.com
yt-research @channel_name
shortn input.md -t 8000
tw-research @username

# Or invoke directly during development:
python scripts/wcb https://docs.example.com
```

### Adding a New Script
1. Create `scripts/myscript` (make executable: `chmod +x scripts/myscript`)
2. Add `ensure_config_venv()` call at the top (Python scripts)
3. Add symlink in `setup-macos.sh` (follow existing pattern in the symlinks section)
4. Document in `skills.md`

## Python Venv & Dependencies

The venv at `~/.config/config-venv/` is created by `setup-macos.sh`. `_utils.py::ensure_config_venv()` auto-re-invokes scripts inside it — so scripts work without manually activating the venv.

Dependencies: `rich`, `tiktoken`, `yt-dlp`, `aiohttp`, `aiofiles`, `click`, `tldextract`, `beautifulsoup4`, `markdownify`, `twscrape`.

## Claude Code Config

`~/.config/claude/` stores Claude Code's behavioral files, version-controlled here and symlinked into `~/.claude/`:

| Path | Purpose |
|------|---------|
| `claude/settings.json` | Claude Code preferences (plugins, voice, model) |
| `claude/system-prompt.txt` | Global Claude personality/behavior overrides |
| `claude/skills/` | Installed skills (56 from skillsmp marketplace) |
| `claude/commands/` | Custom slash commands (e.g. `/gdrive-read`) |
| `claude/agents/` | Role/persona prompts — one `.md` per agent type |
| `claude/docs/` | Local Claude Code docs (generated, not tracked) |

Symlinks: `~/.claude/{skills,commands,settings.json}` → `~/.config/claude/{skills,commands,settings.json}`

```bash
# Refresh local Claude Code documentation
sync-docs
```

`agents/` convention: create `claude/agents/researcher.md`, `claude/agents/coder.md`, etc. with role-specific system prompts.

## Shell Config

- Main shell config: `.zshrc` (Oh My Zsh, robbyrussell theme)
- `ZDOTDIR=$HOME/.config` is set so zsh reads from this directory
- Custom scripts on PATH via `~/.local/bin`
