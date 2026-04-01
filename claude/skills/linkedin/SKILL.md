---
name: linkedin
description: "Fetch LinkedIn profiles, search people and companies, browse jobs, and read company posts via mcporter + linkedin-scraper-mcp. Triggers: 'linkedin', 'linkedin profile', 'search linkedin', 'linkedin jobs', 'find people on linkedin', 'company linkedin', 'linkedin posts', 'who works at', 'linkedin search'."
---

# LinkedIn (mcporter)

LinkedIn automation via `mcporter` + `linkedin-scraper-mcp`. Free, session-based auth. Each call takes 10-30s (real browser).

Requires: `mcporter`, `linkedin-scraper-mcp`

## People

### Fetch profile

```bash
# Basic profile (name, headline, about, skills, activity)
mcporter call 'linkedin.get_person_profile(linkedin_username: "username")'

# With experience and education
mcporter call 'linkedin.get_person_profile(linkedin_username: "username", sections: "experience,education")'

# With posts
mcporter call 'linkedin.get_person_profile(linkedin_username: "username", sections: "posts")'

# All sections
mcporter call 'linkedin.get_person_profile(linkedin_username: "username", sections: "experience,education,interests,honors,languages,contact_info,posts")'
```

Available sections: `experience`, `education`, `interests`, `honors`, `languages`, `contact_info`, `posts`

Only request what you need — each section adds browser load time.

### Search people

```bash
mcporter call 'linkedin.search_people(keywords: "software engineer")'

# With location
mcporter call 'linkedin.search_people(keywords: "AI engineer", location: "San Francisco")'
```

Results limited to your network reach (3rd degree without Premium).

## Companies

### Fetch company

```bash
# Basic company info (about page)
mcporter call 'linkedin.get_company_profile(company_name: "anthropic")'

# With posts and jobs
mcporter call 'linkedin.get_company_profile(company_name: "anthropic", sections: "posts,jobs")'
```

Available sections: `posts`, `jobs`

### Company posts

```bash
mcporter call 'linkedin.get_company_posts(company_name: "anthropic")'
```

## Jobs

### Search jobs

```bash
# Basic search
mcporter call 'linkedin.search_jobs(keywords: "software engineer")'

# With filters
mcporter call 'linkedin.search_jobs(keywords: "AI engineer", location: "Remote", date_posted: "past_week")'

# More filters
mcporter call 'linkedin.search_jobs(keywords: "engineer", work_type: "remote", experience_level: "entry,associate", easy_apply: true, sort_by: "date")'
```

| Filter | Values |
|--------|--------|
| `date_posted` | `past_hour`, `past_24_hours`, `past_week`, `past_month` |
| `job_type` | `full_time`, `part_time`, `contract`, `temporary`, `volunteer`, `internship` |
| `experience_level` | `internship`, `entry`, `associate`, `mid_senior`, `director`, `executive` |
| `work_type` | `on_site`, `remote`, `hybrid` |
| `easy_apply` | `true` / `false` |
| `sort_by` | `date`, `relevance` |
| `max_pages` | 1-10 (default 3) |

Returns `job_ids` — use with `get_job_details` for full info.

### Job details

```bash
mcporter call 'linkedin.get_job_details(job_id: "4252026496")'
```

## Response format

All calls return JSON with `url`, `sections` (name → raw text), and `references` (extracted links/people). Parse the raw text in sections to extract structured data.

## Auth

Session stored at `~/.linkedin-mcp/profile`. If calls fail with auth errors:

```bash
linkedin-scraper-mcp --login --no-headless
```

This opens a browser — log in manually within 5 minutes.

Check status: `linkedin-scraper-mcp --status`
