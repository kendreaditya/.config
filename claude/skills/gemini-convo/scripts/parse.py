#!/usr/bin/env python3
"""Parse Google AI Studio / Gemini conversation JSON files into readable markdown."""

import json
import sys
import os


def parse_gemini_convo(filepath, include_thinking=False, output_file=None):
    with open(filepath, 'r') as f:
        data = json.load(f)

    chunks = data.get('chunkedPrompt', {}).get('chunks', [])
    model = data.get('runSettings', {}).get('model', 'unknown')

    lines = []
    lines.append(f"# Gemini Conversation")
    lines.append(f"**Model:** {model}")
    lines.append(f"**Source:** {os.path.basename(filepath)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    msg_num = 0
    for chunk in chunks:
        role = chunk.get('role', 'unknown')
        is_thought = chunk.get('isThought', False)

        # Skip thinking blocks unless requested
        if is_thought and not include_thinking:
            continue

        # Skip chunks that are only thoughtSignature
        parts = chunk.get('parts', [])
        if parts and all(p.get('thoughtSignature') or p.get('thought') for p in parts):
            if not include_thinking:
                continue

        # Get the text content
        text = chunk.get('text', '')

        # If no direct text, combine parts
        if not text and parts:
            text_parts = []
            for part in parts:
                if part.get('thought') and not include_thinking:
                    continue
                if part.get('thoughtSignature'):
                    continue
                part_text = part.get('text', '')
                if part_text:
                    text_parts.append(part_text)
            text = ''.join(text_parts)

        # Skip empty messages
        if not text.strip():
            # Check for drive document references
            drive_doc = chunk.get('driveDocument', {})
            if drive_doc.get('id'):
                msg_num += 1
                lines.append(f"### Message {msg_num} — {role.upper()}")
                lines.append(f"*[Attached Drive Document: {drive_doc['id']}]*")
                lines.append("")
                lines.append("---")
                lines.append("")
            continue

        msg_num += 1

        # Format role header
        if role == 'user':
            lines.append(f"### Message {msg_num} — USER")
        elif role == 'model':
            lines.append(f"### Message {msg_num} — GEMINI")
        else:
            lines.append(f"### Message {msg_num} — {role.upper()}")

        if is_thought:
            lines.append("*(thinking)*")

        lines.append("")
        lines.append(text.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    output = '\n'.join(lines)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        print(f"Saved to {output_file} ({msg_num} messages)")
    else:
        print(output)

    return msg_num


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 parse.py <conversation.json> [--output file.md] [--thinking]")
        print("")
        print("Options:")
        print("  --output FILE    Save output to file instead of stdout")
        print("  --thinking       Include model thinking/reasoning blocks")
        sys.exit(1)

    filepath = sys.argv[1]
    output_file = None
    include_thinking = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--thinking':
            include_thinking = True
            i += 1
        else:
            i += 1

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    parse_gemini_convo(filepath, include_thinking=include_thinking, output_file=output_file)


if __name__ == '__main__':
    main()
