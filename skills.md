# Skills

Custom CLI tools and scripts for research, development, and productivity.

---

## yt-research

Stream YouTube channel transcripts to Markdown for research and analysis.

### Usage

```bash
yt-research @channel_name
yt-research https://www.youtube.com/@channel_name
yt-research @channel_name -o output.md
yt-research @channel_name -v  # verbose mode
```

### Options

| Flag | Description |
|------|-------------|
| `-o, --output` | Output file path (default: `./[channel].md`) |
| `-v, --verbose` | Show detailed progress for each video |

### Features

- Fetches transcripts from entire YouTube channels
- Supports both `/videos` and `/shorts` tabs
- Async processing with 5 concurrent tasks
- Progress bar with rich formatting
- VTT caption cleaning with deduplication
- Outputs markdown with video links and transcripts

### Output Format

```markdown
# channel_name

## Video Title
**Video ID:** abc123
**URL:** https://youtube.com/watch?v=abc123

Transcript text here...

---
```

### Dependencies

- `yt_dlp` - YouTube downloading
- `rich` - Progress bars
- Uses venv at `~/.config/config-venv`

---

## shortn

LLM Context Compressor - compress large text/markdown files to fit within token limits using extractive summarization (no LLM required).

### Usage

```bash
shortn input.md -t 8000                    # → input.compressed.md
shortn input.md -t 32000 -o out.md         # Custom output file
shortn input.md -t 8000 --stdout           # Print to stdout
shortn input.md -t 8000 --no-parallel      # Disable parallelization
cat input.md | shortn -t 8000 --stdin --stdout  # Pipe mode
```

### Options

| Flag | Description |
|------|-------------|
| `-t, --tokens` | Target token limit (required) |
| `-o, --output` | Output file (default: `input.compressed.md`) |
| `--model` | Tiktoken model (default: `cl100k_base`) |
| `--stdout` | Print output to stdout |
| `--stdin` | Read input from stdin |
| `-v, --verbose` | Show detailed progress messages |
| `-q, --quiet` | Suppress progress messages |
| `--no-parallel` | Disable parallel processing |

### Algorithm

1. **Parse** - Split document into sections (headers + content)
2. **Classify** - Identify units (titles, headers, code, lists, text)
3. **Score** - Compute TextRank scores using Jaccard similarity
4. **Boost** - Prioritize titles and code blocks
5. **Allocate** - Distribute token budget proportionally to sections
6. **Select** - Choose best units within budget, preserving order

### Features

- Per-section TextRank scoring with parallel processing
- Token counting via `tiktoken` (OpenAI's tokenizer)
- Preserves document structure (headers, code blocks, lists)
- Intelligent section-based compression
- No external LLM calls required

### Dependencies

- `tiktoken` - Token counting
- Uses venv at `~/.config/config-venv`

---

## url

Create HTML redirect files that open URLs in a browser.

### Usage

```bash
url example.com                    # Creates example.com.html
url example.com myfile             # Creates myfile.html
url https://example.com/path       # Auto-detects protocol
```

### Options

| Argument | Description |
|----------|-------------|
| `<url>` | URL to redirect to (required) |
| `[filename]` | Optional filename (default: derived from URL) |

### Features

- Auto-prepends `https://` if protocol missing
- Generates HTML with meta-refresh redirect
- JavaScript fallback for immediate redirect
- Opens in default browser when clicked

### Alias

Configured in `.zshrc`:
```bash
alias url="$HOME/.config/scripts/url-launcher.sh"
```

---

## Setup

### Virtual Environment

Scripts use a shared venv at `~/.config/config-venv`. To set up:

```bash
python3 -m venv ~/.config/config-venv
~/.config/config-venv/bin/pip install yt-dlp rich tiktoken
```

### Making Scripts Executable

```bash
chmod +x ~/.config/scripts/yt-research
chmod +x ~/.config/scripts/shortn
chmod +x ~/.config/scripts/url-launcher.sh
```

### Adding to PATH

Add to `.zshrc`:
```bash
export PATH="$HOME/.config/scripts:$PATH"
```
