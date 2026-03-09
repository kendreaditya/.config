# yt-research

Download YouTube channel or search transcripts to Markdown for research and analysis.

## Trigger

Use when the user wants to research a YouTube channel, download a single video transcript, or gather video content for analysis. Keywords: "youtube research", "youtube transcripts", "channel transcripts", "yt research", "yt scribe".

## Usage

```bash
# Single video transcript
yt-research https://www.youtube.com/watch?v=VIDEO_ID

# Channel transcripts
yt-research @channel_name
yt-research https://www.youtube.com/@channel_name

# Search query transcripts
yt-research "search query terms"
yt-research https://www.youtube.com/results?search_query=...

# With options
yt-research @channel_name -o output.md        # Custom output file
yt-research @channel_name -v                  # Verbose mode
yt-research "search query" -n 20              # Number of search results (default: 15)
```

## Options

| Flag | Description |
|------|-------------|
| `-o, --output` | Output file path (default: `./[channel_or_query].md`) |
| `-v, --verbose` | Show detailed progress for each video |
| `-n, --num-results` | Number of search results to process (default: 15) |

## Behavior

- Fetches transcript from a single YouTube video URL
- Fetches transcripts from YouTube channels (both `/videos` and `/shorts` tabs)
- Supports YouTube search queries (plain text or search URLs)
- Async processing with 5 concurrent tasks and rate-limit handling
- Resumes from existing output files (skips already-processed videos)
- Outputs Markdown with video titles, IDs, URLs, and cleaned transcripts
- Cleans VTT captions with deduplication and sentence splitting

## Output Format

Creates a Markdown file in the current directory (or specified path) with:
- H1 header with channel name or search query
- H2 sections per video with title, video ID, URL, and transcript text
- Horizontal rules between videos

## Dependencies

Requires the `~/.config/config-venv` virtualenv with `yt_dlp` and `rich`.

## Instructions

Run the script via Bash. The output file will be created in the current working directory unless `-o` is specified. For large channels, the process may take several minutes. If rate-limited, the script will prompt interactively (wait or abort).
