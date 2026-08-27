---
name: assemblyai
description: "Transcribe audio/video files and URLs using the AssemblyAI CLI. Supports local files, remote URLs, and YouTube videos. Features: speaker diarization, sentiment analysis, entity detection, auto highlights, auto chapters, content moderation, PII redaction, summarization, topic detection, language detection, SRT subtitles, and JSON output. Use when: (1) transcribing audio or video files, (2) generating meeting transcripts with speaker labels, (3) summarizing audio content, (4) redacting PII from transcripts, (5) analyzing sentiment or detecting entities in speech, (6) retrieving a previous transcription by ID, (7) generating subtitles/captions (SRT), (8) any speech-to-text task. Triggers: transcribe, speech to text, audio transcript, assemblyai, meeting notes, speaker diarization, subtitle generation."
---

# AssemblyAI

Transcribe audio/video via the `assemblyai` CLI (installed via Homebrew).
API key is pre-configured in `~/.config/assemblyai/config.toml`.

## Quick Start

```bash
# Basic transcription
assemblyai transcribe ./audio.mp3

# With speaker labels and summary
assemblyai transcribe ./meeting.mp4 --speaker_labels --summarization --summary_type bullets

# YouTube video
assemblyai transcribe "https://www.youtube.com/watch?v=VIDEO_ID"

# JSON output
assemblyai transcribe ./audio.mp3 --json

# SRT subtitles
assemblyai transcribe ./video.mp4 --srt

# Retrieve previous transcription
assemblyai get TRANSCRIPT_ID
```

## Commands

### `transcribe FILE_OR_URL [flags]`

Accepts local audio/video files, HTTP URLs, or YouTube URLs.
Defaults: `--poll=true`, `--speaker_labels=true`, `--punctuate=true`, `--format_text=true`.

### `get TRANSCRIPT_ID [--poll] [--json] [--srt]`

Retrieve a previously submitted transcription by ID.

## Common Recipes

**Meeting transcript with summary:**
```bash
assemblyai transcribe meeting.mp3 --speaker_labels --summarization --summary_type bullets --summary_model conversational
```

**Privacy-safe transcription (PII redacted):**
```bash
assemblyai transcribe call.mp3 --redact_pii --redact_pii_policies "person_name,phone_number,credit_card_number,email_address"
```

**Full analysis:**
```bash
assemblyai transcribe interview.mp3 --speaker_labels --sentiment_analysis --entity_detection --auto_highlights --auto_chapters
```

**Non-English audio:**
```bash
assemblyai transcribe spanish.mp3 --language_code es
# Or auto-detect:
assemblyai transcribe unknown.mp3 --language_detection
```

## Flag Restrictions

- `--speaker_labels` and `--dual_channel` are mutually exclusive
- `--auto_chapters` and `--summarization` are mutually exclusive
- `--language_detection` and `--language_code` are mutually exclusive
- `--summarization` requires `--punctuate` and `--format_text` (both default true)
- `--summary_model conversational` requires `--speaker_labels`

## Full Flag Reference

See [references/flags.md](references/flags.md) for the complete list of all flags, PII policies, supported languages, and audio formats.
