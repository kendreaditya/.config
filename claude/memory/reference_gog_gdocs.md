---
name: Google Docs via gog CLI
description: Patterns for creating, editing, and managing Google Docs with gog CLI and direct API fallbacks
type: reference
---

**Account:** `kendreaditya@gmail.com` (full scopes: docs, drive, gmail, calendar, etc.)

**Key gog docs commands:**
- `gog docs create "Title" --file input.md --pageless --parent FOLDER_ID` — create from markdown
- `gog docs find-replace DOC_ID "find" "[text](url)" --format=markdown --first` — add hyperlinks (markdown format)
- `gog docs cat DOC_ID --all-tabs` — read all tabs (use `--tab "Tab Name"` for specific tab)
- `gog docs write DOC_ID --file input.md --tab-id TAB_ID` — write content to specific tab
- `gog docs list-tabs DOC_ID` — list tab IDs and titles

**Tab creation:** `gog` v0.12.0 can't create tabs natively. Use Google Docs API directly:
- Get access token via `gog auth tokens export` → exchange refresh token at `https://oauth2.googleapis.com/token`
- `POST /v1/documents/{docId}:batchUpdate` with `addDocumentTab` request
- NEVER use macOS Keychain directly for tokens

**Gotcha:** `--tab-id` flag doesn't work with `--format=markdown` in find-replace. For markdown edits on non-default tabs, use the direct API with `UpdateTextStyle` for link formatting.
