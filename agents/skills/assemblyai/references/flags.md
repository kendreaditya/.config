# AssemblyAI CLI Flags Reference

## Transcription Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--poll` | `-p` | `true` | Poll until transcription completes |
| `--json` | `-j` | `false` | Output raw JSON |
| `--srt` | | `false` | Generate SRT subtitle file |
| `--format_text` | `-f` | `true` | Enable text formatting |
| `--punctuate` | `-u` | `true` | Auto punctuation |
| `--disfluencies` | `-D` | `false` | Include filler words (um, uh) |

## Audio Intelligence Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--speaker_labels` | `-l` | Speaker diarization (default true) |
| `--auto_highlights` | `-a` | Detect important phrases/keywords |
| `--auto_chapters` | `-s` | Generate chapter summaries |
| `--entity_detection` | `-e` | Identify named entities |
| `--sentiment_analysis` | `-x` | Per-sentence sentiment |
| `--topic_detection` | `-t` | IAB topic categories |
| `--content_moderation` | `-c` | Detect sensitive content |

## PII Redaction

| Flag | Short | Description |
|------|-------|-------------|
| `--redact_pii` | `-r` | Enable PII redaction |
| `--redact_pii_policies` | `-i` | Comma-separated policies (default: `drug,number_sequence,person_name`) |

**Available policies:** banking_information, blood_type, credit_card_cvv, credit_card_expiration, credit_card_number, date, drivers_license, drug, email_address, event, injury, language, location, medical_condition, medical_process, money_amount, nationality, number_sequence, occupation, organization, person_age, person_name, phone_number, political_affiliation, religion, us_social_security_number

## Summarization

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--summarization` | `-m` | `false` | Generate summary |
| `--summary_type` | `-y` | `bullets` | `paragraph`, `headline`, `gist`, `bullets`, `bullets_verbose` |
| `--summary_model` | `-q` | `informative` | `informative`, `conversational`, `catchy` |

## Language

| Flag | Short | Description |
|------|-------|-------------|
| `--language_detection` | `-n` | Auto-detect language |
| `--language_code` | `-g` | Specify: en, es, fr, de, it, pt, nl, hi, ja, zh, fi, ko, pl, ru, tr, uk, vi |

## Audio Channel & Boost

| Flag | Short | Description |
|------|-------|-------------|
| `--dual_channel` | `-d` | Dual channel processing |
| `--word_boost` | `-k` | CSV of terms to boost |
| `--boost_param` | `-z` | `low`, `default`, `high` |
| `--custom_spelling` | | JSON or file path for custom spelling |

## Webhooks

| Flag | Short | Description |
|------|-------|-------------|
| `--webhook_url` | `-w` | Completion webhook URL |
| `--webhook_auth_header_name` | `-b` | Webhook auth header name |
| `--webhook_auth_header_value` | `-o` | Webhook auth header value |

## Supported Audio/Video Formats

**Audio:** 3ga, 8svx, aac, ac3, aif, aiff, alac, amr, ape, au, dss, flac, m4a, m4b, m4p, m4r, mp3, mpga, ogg, oga, mogg, opus, qcp, tta, voc, wav, wma, wv, webm

**Video:** flv, mov, mp2, mp4, m4v, mxf, MTS, M2TS, TS
