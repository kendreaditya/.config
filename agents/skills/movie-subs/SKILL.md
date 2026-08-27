---
name: movie-subs
description: "Download and clean movie/TV subtitles given a title. Searches for the movie first, confirms with user which version/year, then downloads SRT via subliminal, cleans via the clean skill's cleansubs.py, and reads the result. Triggers: 'movie subtitles', 'get subtitles for', 'download subs', 'movie dialogue', 'movie script', 'film transcript', 'what does X say in the movie', 'nuremberg trials movie'. Dependencies: subliminal (pipx install subliminal), clean skill (cleansubs.py)."
---

# Movie Subs

Download, clean, and read movie/TV subtitles from a title alone.

## Workflow

### Step 1: Search and confirm

Before downloading, **always search for the movie first** to find the correct title and year. Many titles have multiple versions (remakes, TV movies, miniseries).

Use WebSearch to find: `"<user's query>" movie site:imdb.com`

Present the top matches to the user as a numbered list:

```
Found these matches:
1. Nuremberg (2000) — TV miniseries with Alec Baldwin
2. Judgment at Nuremberg (1961) — Classic courtroom drama with Spencer Tracy
3. Nuremberg: Tyranny on Trial (2024) — Documentary

Which one? (number or name)
```

**Wait for user confirmation before downloading.** Do not guess.

### Step 2: Download subtitles

Once confirmed, run the download script with the exact title and year:

```bash
~/.claude/skills/movie-subs/scripts/get-subs.sh "Exact Movie Title" YEAR [output-dir]
```

Examples:
```bash
~/.claude/skills/movie-subs/scripts/get-subs.sh "The Imitation Game" 2014
~/.claude/skills/movie-subs/scripts/get-subs.sh "Interstellar" 2014 ~/Downloads
```

Default output dir is `~/Downloads`.

### Step 3: Read and respond

Output files:
- `Title.Year.1080p.en.srt` — raw SRT
- `Title.Year.1080p.txt` — cleaned plain text (via cleansubs)
- `Title.Year.1080p.md` — cleaned markdown (via cleansubs)

Read the `.txt` file to answer user questions about the dialogue.

### Manual fallback (if script fails)

```bash
dd if=/dev/zero of="/tmp/Movie.Title.Year.1080p.mp4" bs=1024 count=1 2>/dev/null
subliminal download -l en -f "/tmp/Movie.Title.Year.1080p.mp4"
python3 ~/.claude/skills/clean/scripts/cleansubs.py "/tmp/Movie.Title.Year.1080p.en.srt" -o clean.txt
```

## Tips

- Include the **year** — critical for disambiguation
- If subliminal finds no results, try alternate titles (drop "The", use international title)
- The clean skill preserves speaker labels and sound effects
- For searching specific dialogue, grep the `.txt` output
