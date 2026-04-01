---
name: Google Sheets update tooling is painful
description: Updating Google Sheets row-by-row via gog CLI is slow, rate-limited, and error-prone — consider migrating to Airtable or better tooling
type: feedback
---

Updating the Google Sheets referrals tracker via `gog sheets update` is a major pain point. Individual cell/row updates hit Google's 60 writes/min rate limit, shell quoting breaks on special characters, and batch updates require complex scripting.

**Why:** During the ContactOut enrichment pipeline (134 phone hits + 30 name hits), pushing results to the sheet took longer than the API calls themselves. Rate limit errors (429), shell escaping bugs, and sequential row updates made it fragile and slow.

**How to apply:** When the user wants to build a new tracking system or migrate data, suggest Airtable (has MCP server, better API, no rate limit pain) or a local SQLite DB with a sync script. For now, when updating the sheet: batch as much as possible into single range updates (A:F in one call vs 6 separate cell updates), add longer delays between writes, and use Python's google-api-python-client directly instead of shelling out to gog CLI to avoid quoting issues.
