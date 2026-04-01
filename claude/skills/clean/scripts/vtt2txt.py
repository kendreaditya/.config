#!/usr/bin/env python3
"""vtt2txt — Clean VTT subtitle files into readable text or markdown.

Usage:
    vtt2txt input.vtt                          # plain text to stdout
    vtt2txt input.vtt -o out.txt               # plain text to file
    vtt2txt input.vtt --md                     # markdown to stdout
    vtt2txt input.vtt --md --title "T" --id X  # markdown with metadata
    vtt2txt /tmp/*.vtt --md -o combined.md     # batch to one file
    cat file.vtt | vtt2txt                     # stdin
"""
import argparse
import re
import sys
from pathlib import Path

MIN_OVERLAP = 4
SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


def clean_vtt(text: str) -> str:
    """Clean raw VTT content into readable text."""
    # Strip BOM
    text = text.lstrip('\ufeff')

    lines = []
    for line in text.split('\n'):
        # Skip VTT metadata
        if line.startswith('WEBVTT') or '-->' in line:
            continue
        if line.startswith(('Kind:', 'Language:')):
            continue
        if not line.strip():
            continue
        # Skip cue IDs (pure numbers)
        if line.strip().isdigit():
            continue

        # Strip VTT tags
        line = re.sub(r'<[\d:.]+>', '', line)        # timestamp spans
        line = re.sub(r'</?c[^>]*>', '', line)       # color tags
        line = re.sub(r'</?[a-z][^>]*>', '', line)   # generic HTML tags
        line = line.strip()
        if not line:
            continue

        # Hybrid deduplication
        if lines:
            last = lines[-1]
            if line in last:
                continue
            if last in line:
                lines[-1] = line
                continue
            min_len = min(len(last), len(line))
            for ol in range(min_len, MIN_OVERLAP - 1, -1):
                if last[-ol:] == line[:ol]:
                    lines[-1] = last + line[ol:]
                    break
            else:
                lines.append(line)
        else:
            lines.append(line)

    # Join, collapse whitespace
    text = ' '.join(lines)
    text = re.sub(r'\s+', ' ', text).strip()

    # Fix missing space after punctuation
    text = re.sub(r'([.!?])(\w)', r'\1 \2', text)

    # Split into sentences, rejoin as paragraphs
    sentences = [s.strip() for s in SENTENCE_END.split(text) if s.strip()]
    return '\n\n'.join(sentences)


def infer_video_id(path: Path) -> str | None:
    """Infer video ID from yt-dlp filename pattern: VIDEO_ID.lang.vtt"""
    parts = path.stem.split('.')
    if len(parts) >= 2:
        return parts[0]
    return path.stem if path.stem else None


def format_md_section(text: str, title: str | None = None,
                      video_id: str | None = None, url: str | None = None) -> str:
    """Format cleaned text as a markdown section with metadata."""
    header = f"## {title}\n" if title else ""
    meta_lines = []
    if video_id:
        meta_lines.append(f"**Video ID:** {video_id}")
    if url:
        meta_lines.append(f"**URL:** {url}")
    elif video_id:
        meta_lines.append(f"**URL:** https://youtube.com/watch?v={video_id}")
    meta = '\n'.join(meta_lines)
    if meta:
        meta += '\n'
    return f"{header}{meta}\n{text}\n\n---\n"


def process_file(path: Path, args) -> str:
    """Process a single VTT file and return output string."""
    content = path.read_text(encoding='utf-8', errors='replace')
    cleaned = clean_vtt(content)
    if not cleaned:
        return ""

    if args.md:
        vid = args.id or infer_video_id(path)
        title = args.title or (vid if vid else path.stem)
        url = args.url
        return format_md_section(cleaned, title=title, video_id=vid, url=url)
    return cleaned


def main():
    parser = argparse.ArgumentParser(description='Clean VTT subtitles to text or markdown')
    parser.add_argument('files', nargs='*', help='VTT files (reads stdin if none)')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--md', action='store_true', help='Output as markdown with metadata')
    parser.add_argument('--title', help='Video title (for markdown mode)')
    parser.add_argument('--id', help='Video ID (for markdown mode)')
    parser.add_argument('--url', help='Video URL (for markdown mode)')
    parser.add_argument('--heading', help='H1 heading for combined markdown output')
    args = parser.parse_args()

    parts = []

    if args.heading and args.md:
        parts.append(f"# {args.heading}\n\n")

    if args.files:
        for filepath in args.files:
            path = Path(filepath)
            if not path.exists():
                print(f"Warning: {filepath} not found, skipping", file=sys.stderr)
                continue
            result = process_file(path, args)
            if result:
                parts.append(result)
    else:
        # Read from stdin
        content = sys.stdin.read()
        cleaned = clean_vtt(content)
        if cleaned:
            if args.md:
                title = args.title or "Transcript"
                vid = args.id
                url = args.url
                parts.append(format_md_section(cleaned, title=title, video_id=vid, url=url))
            else:
                parts.append(cleaned)

    output = ('\n' if not args.md else '').join(parts)

    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
