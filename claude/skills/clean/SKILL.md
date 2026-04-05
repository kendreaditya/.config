---
name: clean
description: "Clean noisy machine-generated text into readable output. Unlike converting (pandoc), cleaning handles fragmented, duplicated, or metadata-heavy formats. Supports VTT and SRT subtitle files via cleansubs. Triggers: 'clean vtt', 'clean srt', 'clean subtitles', 'vtt to text', 'srt to text', 'vtt to markdown', 'clean transcript', 'subtitle to text', 'cleansubs'."
---

# Clean

Clean noisy, machine-generated text into readable output.

**Converting** (pandoc) = structured data, just change syntax. **Cleaning** = noisy data, strip metadata, dedup, stitch lines, find paragraph boundaries.

## VTT/SRT Subtitles → Text/Markdown

**CLI:** `cleansubs` (at `scripts/cleansubs.py`)

```bash
# Plain text
cleansubs input.vtt                              # stdout
cleansubs input.srt                              # SRT directly, no conversion
cleansubs input.vtt -o output.txt                # file

# Markdown with metadata (matches yt-research output format)
cleansubs input.vtt --md                         # stdout
cleansubs input.srt --md --title "Movie" -o t.md # SRT to markdown
cleansubs input.vtt --md --title "T" --id "abc"  # with metadata

# Stdin
cat /tmp/VIDEO_ID.en.vtt | cleansubs
cat /tmp/VIDEO_ID.en.vtt | cleansubs --md --title "My Video"

# Batch — multiple files to one markdown
cleansubs /tmp/*.vtt --md --heading "Research" -o combined.md

# Force format when auto-detect is wrong
cleansubs input.vtt --format srt
cleansubs input.vtt --format youtube
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--md` | Output markdown with `## Title`, Video ID, URL, transcript, `---` |
| `--title` | Video title (inferred from filename if omitted) |
| `--id` | Video ID (inferred from yt-dlp filename pattern `ID.lang.vtt`) |
| `--url` | Video URL (auto-generated from ID if omitted) |
| `--heading` | H1 heading for combined batch output |
| `--format` | Force format: `auto` (default), `youtube`, `srt`, `structured_vtt` |
| `-o` | Output file (stdout if omitted) |

**Format auto-detection:**
- `.srt` extension or comma-timestamps → SRT pipeline (block-based, timing-gap paragraphs)
- `Kind: captions` header or no cue IDs → YouTube auto-gen VTT (overlap-merge dedup)
- VTT with cue IDs → structured VTT (uses SRT-style pipeline)

**What it cleans:**
- Strips VTT/SRT headers, timestamps, cue IDs, Kind/Language metadata
- Strips HTML/VTT tags (timestamp spans, color tags, speaker tags)
- YouTube VTT: deduplicates overlapping fragments (substring + overlap merge)
- SRT/structured: block-based parsing, preserves commas and punctuation, timing-gap paragraphs (>2s gap = new paragraph)
- Keeps speaker labels and sound effects intact
- Fixes missing punctuation spacing

**Use with youtube skill:**
```bash
# Download subs + clean to plain text
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL" && cleansubs /tmp/VIDEO_ID.en.vtt

# Download subs + clean to markdown with metadata
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download \
  -o "/tmp/%(id)s.%(ext)s" "URL" && \
  cleansubs /tmp/VIDEO_ID.en.vtt --md --title "Video Title" -o transcript.md
```

**Dependencies:** Python 3 (stdlib only — no pip packages)
