---
name: clean
description: "Clean noisy machine-generated text into readable output. Unlike converting (pandoc), cleaning handles fragmented, duplicated, or metadata-heavy formats. Currently supports VTT subtitle files via vtt2txt. Triggers: 'clean vtt', 'clean subtitles', 'vtt to text', 'vtt to markdown', 'clean transcript', 'subtitle to text', 'vtt2txt'."
---

# Clean

Clean noisy, machine-generated text into readable output.

**Converting** (pandoc) = structured data, just change syntax. **Cleaning** = noisy data, strip metadata, dedup, stitch lines, find paragraph boundaries.

## VTT Subtitles → Text/Markdown

**CLI:** `vtt2txt` (at `scripts/vtt2txt.py`)

```bash
# Plain text
vtt2txt input.vtt                              # stdout
vtt2txt input.vtt -o output.txt                # file

# Markdown with metadata (matches yt-research output format)
vtt2txt input.vtt --md                         # stdout
vtt2txt input.vtt --md --title "T" --id "abc"  # with metadata
vtt2txt input.vtt --md -o transcript.md        # to file

# Stdin
cat /tmp/VIDEO_ID.en.vtt | vtt2txt
cat /tmp/VIDEO_ID.en.vtt | vtt2txt --md --title "My Video"

# Batch — multiple VTTs to one markdown
vtt2txt /tmp/*.vtt --md --heading "Research" -o combined.md
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--md` | Output markdown with `## Title`, Video ID, URL, transcript, `---` |
| `--title` | Video title (inferred from filename if omitted) |
| `--id` | Video ID (inferred from yt-dlp filename pattern `ID.lang.vtt`) |
| `--url` | Video URL (auto-generated from ID if omitted) |
| `--heading` | H1 heading for combined batch output |
| `-o` | Output file (stdout if omitted) |

**What it cleans:**
- Strips VTT headers, timestamps, cue IDs, Kind/Language metadata
- Strips HTML/VTT tags (timestamp spans, color tags, speaker tags)
- Deduplicates repeated caption lines (substring + overlap merge)
- Fixes missing punctuation spacing
- Splits into sentence paragraphs

**Use with youtube skill:**
```bash
# Download subs + clean to plain text
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL" && vtt2txt /tmp/VIDEO_ID.en.vtt

# Download subs + clean to markdown with metadata
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL" && \
  vtt2txt /tmp/VIDEO_ID.en.vtt --md --title "Video Title" -o transcript.md
```

**Dependencies:** Python 3 (stdlib only — no pip packages)
