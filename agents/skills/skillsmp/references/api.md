# SkillsMP API Reference

Detailed technical documentation for searching the SkillsMP marketplace.

## API Configuration

- **API Key:** Set `SKILLSMP_API_KEY` in `~/.config/.env` (git-crypt encrypted) — never
  hardcode the key in this file or in `SKILL.md`.
- **Base URL:** `https://skillsmp.com/api/v1`
- **Auth Header:** `Authorization: Bearer $SKILLSMP_API_KEY`

## Endpoints

### 1. Keyword Search
`GET /skills/search`

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `q` | string | Yes | The search query. |
| `page` | number | No | Page number (default: 1). |
| `limit` | number | No | Results per page (default: 20, max: 100). |
| `sortBy` | string | No | `stars` or `recent`. |

### 2. AI Semantic Search
`GET /skills/ai-search`

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `q` | string | Yes | Natural language query (URL-encoded). |

## Rate Limits
- **Daily Limit:** 500 requests per API key.
- **Reset:** Midnight UTC.
- **Headers:** `X-RateLimit-Daily-Limit` and `X-RateLimit-Daily-Remaining`.

## Error Codes
- `401 MISSING_API_KEY / INVALID_API_KEY`
- `400 MISSING_QUERY`
- `429 DAILY_QUOTA_EXCEEDED`
- `500 INTERNAL_ERROR`
