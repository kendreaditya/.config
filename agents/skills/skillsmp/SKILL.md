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
- **Authentication**: Pass the Bearer token via `-H` flag. Set `SKILLSMP_API_KEY` in
  `~/.config/.env` (git-crypt encrypted) — never hardcode the key in this file.
- **Search Logic**:
  - Keyword: `https://skillsmp.com/api/v1/skills/search?q={query}&sortBy=stars`
  - AI Semantic: `https://skillsmp.com/api/v1/skills/ai-search?q={url_encoded_query}`

### Bash curl template

```bash
curl -s "https://skillsmp.com/api/v1/skills/search?q=QUERY&sortBy=stars" \
  -H "Authorization: Bearer $SKILLSMP_API_KEY" | \
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

## Required: track anything you install

Searching is only half the job. If the user installs a skill found here, you **must** record its
provenance with the `upstream` skill before or immediately after copying it in. Marketplace
results are by definition someone else's work, and the `githubUrl` above is exactly the pointer
needed — so there is no excuse for landing an untracked copy.

Without it, a later upstream fix cannot be pulled without clobbering local edits, and nobody can
tell which lines were the original author's.

```bash
# 1. Find SKILL.md inside the repo — often NOT at the root
gh api "repos/OWNER/REPO/git/trees/main?recursive=1" \
  --jq '.tree[] | select(.path|test("SKILL.md$")) | .path'

# 2. Pin the sha for that exact path
gh api "repos/OWNER/REPO/commits" -X GET -f "path=PATH" -f "sha=main" -f per_page=1 \
  --jq '.[0].sha'
```

Then add an `upstream:` block to the installed skill's frontmatter (`repo`, `path`, `ref`, `sha`,
`license`, `checked`, `content_hash`). Never record the user's own repo as the upstream, and don't
create frontmatter just to hold the block — see the `upstream` skill for the schema and the
four-case sync rules.

Afterwards `upstream.sh status` will report whether that skill has drifted from its source.
