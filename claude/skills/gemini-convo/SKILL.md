---
name: gemini-convo
description: Parse and read Google AI Studio / Gemini conversation files (.json with `application/vnd.google-makersuite.prompt` mime type). Use when user asks to read, parse, or extract a Gemini conversation, AI Studio prompt, or Google Makersuite file. Handles thinking blocks, streamed parts, and Drive document references.
---

# gemini-convo

Parse Google AI Studio / Gemini conversation JSON files into readable markdown.

## Usage

```bash
# Print to stdout
python3 ~/.claude/skills/gemini-convo/scripts/parse.py /path/to/conversation.json

# Save to file
python3 ~/.claude/skills/gemini-convo/scripts/parse.py /path/to/conversation.json --output output.md

# Include thinking/reasoning blocks
python3 ~/.claude/skills/gemini-convo/scripts/parse.py /path/to/conversation.json --thinking
```

## Workflow with Google Drive

1. Search: `gog drive search "conversation name" --json --account user@gmail.com`
2. Download: `gog drive download <fileId> --out /tmp/convo.json --account user@gmail.com`
3. Parse: `python3 ~/.claude/skills/gemini-convo/scripts/parse.py /tmp/convo.json --output /tmp/convo.md`
4. Read: use the Read tool on `/tmp/convo.md`

## File Format

JSON with mime type `application/vnd.google-makersuite.prompt`:
- `runSettings` — model config
- `chunkedPrompt.chunks[]` — messages with `role` (user/model), `text`, `isThought`, `parts[]`, `driveDocument.id`
