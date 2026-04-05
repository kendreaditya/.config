#!/usr/bin/env python3
"""cleansubs — Clean VTT/SRT subtitle files into readable text or markdown.

Usage:
    cleansubs input.vtt                          # plain text to stdout
    cleansubs input.srt                          # SRT directly, no conversion
    cleansubs input.vtt -o out.txt               # plain text to file
    cleansubs input.srt --md --title "T" --id X  # markdown with metadata
    cleansubs /tmp/*.vtt --md -o combined.md     # batch to one file
    cat file.vtt | cleansubs                     # stdin
    cleansubs input.vtt --format srt             # force format override
"""
import argparse
import re
import sys
from pathlib import Path

MIN_OVERLAP = 4
SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
GAP_THRESHOLD_MS = 2000  # 2s gap = new paragraph for structured subs

SRT_TS = re.compile(r'(\d{1,2}:\d{2}:\d{2}),(\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}),(\d{3})')
VTT_TS = re.compile(r'(\d{1,2}:?\d{2}:\d{2})\.(\d{3})\s*-->\s*(\d{1,2}:?\d{2}:\d{2})\.(\d{3})')


def _ts_to_ms(hms: str, frac: str) -> int:
    """Convert HH:MM:SS + milliseconds string to total ms."""
    parts = hms.split(':')
    if len(parts) == 2:
        parts = ['0'] + parts
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    return (h * 3600 + m * 60 + s) * 1000 + int(frac)


def _strip_tags(line: str) -> str:
    """Strip VTT/HTML tags from a line."""
    line = re.sub(r'<[\d:.]+>', '', line)       # timestamp spans
    line = re.sub(r'</?c[^>]*>', '', line)      # color tags
    line = re.sub(r'</?[a-z][^>]*>', '', line)  # generic HTML tags
    return line.strip()


def parse_srt_blocks(text: str) -> list[dict]:
    """Parse SRT content into cue blocks."""
    text = text.lstrip('\ufeff')
    blocks = re.split(r'\n\n+', text.strip())
    cues = []
    for block in blocks:
        lines = block.strip().split('\n')
        # Find the timestamp line
        ts_line_idx = None
        for i, line in enumerate(lines):
            if SRT_TS.search(line):
                ts_line_idx = i
                break
        if ts_line_idx is None:
            continue
        m = SRT_TS.search(lines[ts_line_idx])
        start = _ts_to_ms(m.group(1), m.group(2))
        end = _ts_to_ms(m.group(3), m.group(4))
        text_lines = [_strip_tags(l) for l in lines[ts_line_idx + 1:] if l.strip()]
        text_joined = ' '.join(text_lines)
        if text_joined:
            cues.append({'start_ms': start, 'end_ms': end, 'text': text_joined})
    return cues


def parse_vtt_blocks(text: str) -> list[dict]:
    """Parse VTT content into cue blocks."""
    text = text.lstrip('\ufeff')
    blocks = re.split(r'\n\n+', text.strip())
    cues = []
    for block in blocks:
        lines = block.strip().split('\n')
        ts_line_idx = None
        for i, line in enumerate(lines):
            if VTT_TS.search(line):
                ts_line_idx = i
                break
        if ts_line_idx is None:
            continue
        m = VTT_TS.search(lines[ts_line_idx])
        start = _ts_to_ms(m.group(1), m.group(2))
        end = _ts_to_ms(m.group(3), m.group(4))
        text_lines = [_strip_tags(l) for l in lines[ts_line_idx + 1:] if l.strip()]
        text_joined = ' '.join(text_lines)
        if text_joined:
            cues.append({'start_ms': start, 'end_ms': end, 'text': text_joined})
    return cues


def detect_format(text: str, extension: str | None = None) -> str:
    """Detect subtitle format. Returns 'srt', 'youtube_vtt', or 'structured_vtt'."""
    if extension == '.srt':
        return 'srt'
    if SRT_TS.search(text):
        return 'srt'
    # Check for YouTube auto-gen markers
    has_kind = bool(re.search(r'^Kind:', text, re.MULTILINE))
    has_cue_ids = bool(re.search(r'^\d+\s*$', text, re.MULTILINE))
    if has_kind or not has_cue_ids:
        return 'youtube_vtt'
    return 'structured_vtt'


def clean_youtube_vtt(text: str) -> str:
    """Clean YouTube auto-generated VTT (overlapping fragments). Original logic."""
    text = text.lstrip('\ufeff')
    lines = []
    for line in text.split('\n'):
        if line.startswith('WEBVTT') or '-->' in line:
            continue
        if line.startswith(('Kind:', 'Language:')):
            continue
        if not line.strip():
            continue
        if line.strip().isdigit():
            continue
        line = _strip_tags(line)
        if not line:
            continue
        # Hybrid deduplication (works well for YouTube fragments)
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
    text = ' '.join(lines)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'([.!?])(\w)', r'\1 \2', text)
    sentences = [s.strip() for s in SENTENCE_END.split(text) if s.strip()]
    return '\n\n'.join(sentences)


def clean_structured_subs(text: str, fmt: str) -> str:
    """Clean SRT or structured VTT (complete cue blocks, no overlap)."""
    if fmt == 'srt':
        cues = parse_srt_blocks(text)
    else:
        cues = parse_vtt_blocks(text)

    if not cues:
        return ''

    # Exact-match dedup (no overlap merge — movie subs are complete)
    deduped = [cues[0]]
    for cue in cues[1:]:
        if cue['text'] != deduped[-1]['text']:
            deduped.append(cue)

    # Build paragraphs by timing gaps
    paragraphs = []
    current = [deduped[0]['text']]
    for i in range(1, len(deduped)):
        gap = deduped[i]['start_ms'] - deduped[i - 1]['end_ms']
        if gap >= GAP_THRESHOLD_MS:
            paragraphs.append(' '.join(current))
            current = []
        current.append(deduped[i]['text'])
    if current:
        paragraphs.append(' '.join(current))

    # Clean each paragraph
    cleaned = []
    for para in paragraphs:
        para = re.sub(r'\s+', ' ', para).strip()
        para = re.sub(r'([.!?])(\w)', r'\1 \2', para)
        if para:
            cleaned.append(para)

    return '\n\n'.join(cleaned)


def clean_vtt(text: str, extension: str | None = None,
              fmt_override: str | None = None) -> str:
    """Route to the appropriate cleaner based on format detection."""
    if fmt_override and fmt_override != 'auto':
        fmt = fmt_override
    else:
        fmt = detect_format(text, extension)

    if fmt == 'youtube_vtt':
        return clean_youtube_vtt(text)
    else:
        return clean_structured_subs(text, fmt)


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
    """Process a single VTT/SRT file and return output string."""
    content = path.read_text(encoding='utf-8', errors='replace')
    fmt = args.format if hasattr(args, 'format') else 'auto'
    cleaned = clean_vtt(content, extension=path.suffix.lower(), fmt_override=fmt)
    if not cleaned:
        return ""

    if args.md:
        vid = args.id or infer_video_id(path)
        title = args.title or (vid if vid else path.stem)
        url = args.url
        return format_md_section(cleaned, title=title, video_id=vid, url=url)
    return cleaned


def main():
    parser = argparse.ArgumentParser(description='Clean VTT/SRT subtitles to text or markdown')
    parser.add_argument('files', nargs='*', help='VTT or SRT files (reads stdin if none)')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--md', action='store_true', help='Output as markdown with metadata')
    parser.add_argument('--title', help='Video title (for markdown mode)')
    parser.add_argument('--id', help='Video ID (for markdown mode)')
    parser.add_argument('--url', help='Video URL (for markdown mode)')
    parser.add_argument('--heading', help='H1 heading for combined markdown output')
    parser.add_argument('--format', choices=['auto', 'youtube', 'srt', 'structured_vtt'],
                        default='auto', help='Force subtitle format (default: auto-detect)')
    args = parser.parse_args()

    # Normalize format flag
    if args.format == 'youtube':
        args.format = 'youtube_vtt'

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
        fmt = args.format if args.format != 'auto' else None
        cleaned = clean_vtt(content, fmt_override=fmt)
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
