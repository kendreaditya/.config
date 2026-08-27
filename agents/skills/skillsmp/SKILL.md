---
name: find-skills
description: Search the SkillsMP marketplace (25,000+ Agent Skills) for Claude Code, Codex CLI, and ChatGPT skills. Use when the user asks for "skills", "tools", "capabilities", or "how to" do something that might require an external tool or a new Claude Code skill. Supports keyword search, AI semantic search, flexible sorting, and pagination.
version: 3.0.0
---

# Find Skills (SkillsMP)

Search for Claude Code skills and agent capabilities from the SkillsMP marketplace.

## Quick Start Strategy

1. **Keyword Search**: For specific terms like "python", "kubernetes", "git".
2. **AI Semantic Search**: For natural language queries like "how to manage docker containers".

## Execution

- Use `Bash` with `curl` — **never** `WebFetch` (it cannot send custom headers, causing 401).
- **Authentication**: Pass the Bearer token via `-H` flag.
- **Search Logic**:
  - Keyword: `https://skillsmp.com/api/v1/skills/search?q={query}&sortBy=stars`
  - AI Semantic: `https://skillsmp.com/api/v1/skills/ai-search?q={url_encoded_query}`

### Bash curl template

```bash
curl -s "https://skillsmp.com/api/v1/skills/search?q=QUERY&sortBy=stars" \
  -H "Authorization: Bearer sk_live_skillsmp_XluxGQvRNlyDKs0Edv8OaXsxC3U6RBfmuYMU8WQvdQ0" | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
skills = d['data']['skills']
print(f'Total: {len(skills)}\n')
for s in skills:
    print(f\"★ {s.get('stars',0):6}  {s['name']} by {s['author']}\")
    print(f\"         {s['description'][:160]}\")
    print(f\"         {s['githubUrl']}\")
    print()
"
```

## Detailed Documentation

For full details on parameters, pagination, and rate limits, see:
- [references/api.md](references/api.md) — Endpoints, parameters, and error codes.

## Output Format

Present results in a clean list including:
- **Name**, **Author**, **Stars** (★)
- **Description**
- **GitHub URL**

If multiple pages exist, mention how to fetch the next page using the `page` parameter.
