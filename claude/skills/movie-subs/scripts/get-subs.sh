#!/usr/bin/env bash
# get-subs.sh — Download and clean movie subtitles
# Usage: get-subs.sh "Movie Title" [year] [output-dir]
#
# Examples:
#   get-subs.sh "The Imitation Game" 2014
#   get-subs.sh "Interstellar" 2014 ~/Downloads
#   get-subs.sh "The Social Network"

set -euo pipefail

TITLE="${1:?Usage: get-subs.sh \"Movie Title\" [year] [output-dir]}"
YEAR="${2:-}"
OUTDIR="${3:-$HOME/Downloads}"
CLEANSUBS="$HOME/.claude/skills/clean/scripts/cleansubs.py"

# Build filename: Title.Year.1080p.mp4
SAFE_TITLE=$(echo "$TITLE" | sed 's/ /./g; s/[^A-Za-z0-9.]//g')
if [ -n "$YEAR" ]; then
  FNAME="${SAFE_TITLE}.${YEAR}.1080p"
else
  FNAME="${SAFE_TITLE}.1080p"
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# Create dummy video file for subliminal
DUMMY="$WORKDIR/${FNAME}.mp4"
dd if=/dev/zero of="$DUMMY" bs=1024 count=1 2>/dev/null

echo "Searching subtitles for: $TITLE ${YEAR:+($YEAR)}..." >&2

# Download subtitles
if ! subliminal download -l en -f "$DUMMY" 2>/dev/null; then
  echo "ERROR: subliminal failed. Is it installed? (pipx install subliminal)" >&2
  exit 1
fi

# Find the downloaded SRT
SRT=$(find "$WORKDIR" -name "*.srt" -type f | head -1)
if [ -z "$SRT" ]; then
  echo "ERROR: No subtitles found for '$TITLE'" >&2
  exit 1
fi

echo "Found subtitles: $(basename "$SRT")" >&2

# Copy raw SRT to output dir
RAW_OUT="$OUTDIR/${FNAME}.en.srt"
cp "$SRT" "$RAW_OUT"
echo "Raw SRT: $RAW_OUT" >&2

# Clean to plain text
TXT_OUT="$OUTDIR/${FNAME}.txt"
python3 "$CLEANSUBS" "$RAW_OUT" -o "$TXT_OUT"
echo "Clean text: $TXT_OUT" >&2

# Clean to markdown
MD_OUT="$OUTDIR/${FNAME}.md"
python3 "$CLEANSUBS" "$RAW_OUT" --md --title "$TITLE${YEAR:+ ($YEAR)}" -o "$MD_OUT"
echo "Markdown: $MD_OUT" >&2

echo ""
echo "Done. Files saved to $OUTDIR:"
echo "  $RAW_OUT"
echo "  $TXT_OUT"
echo "  $MD_OUT"

# Output the txt path for the caller to read
echo "READ:$TXT_OUT"
