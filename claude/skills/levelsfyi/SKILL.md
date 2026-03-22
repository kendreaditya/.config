---
name: levelsfyi
description: Query levels.fyi salary data, company info, job listings, benefits, leaderboard, and more via a CLI script. Use when the user asks about tech salaries, compensation data, job levels, company comparisons, benefits, or anything involving levels.fyi data. Triggers on: "levels.fyi", "salary data", "tech compensation", "what does X pay", "compare salaries", "job leaderboard", "company benefits comparison".
---

# Levelsfyi

Query levels.fyi salary data, companies, jobs, benefits, and leaderboard via the CLI.

## Setup

```bash
source ~/.config/config-venv/bin/activate && python3 ~/.config/scripts/levels.py <command> [args]
```

Requires `pycryptodome` (already in `~/.config/config-venv`).

## Commands

### Search Companies
```bash
python3 ~/.config/scripts/levels.py search-company "google"
```

### Job Listings
```bash
python3 ~/.config/scripts/levels.py jobs --location san-francisco-bay-area --limit 20
python3 ~/.config/scripts/levels.py jobs --location new-york-city seattle --sort recent
```

### Company Salaries (levels, TC percentiles, titles)
```bash
python3 ~/.config/scripts/levels.py company-salaries google
python3 ~/.config/scripts/levels.py company-salaries meta --job-family software-engineer --country 254
```
Returns: per-level averages, TC/base/bonus/stock percentiles, titles with counts.

### Job Family Info (companies with levels, median comp)
```bash
python3 ~/.config/scripts/levels.py job-family software-engineer
python3 ~/.config/scripts/levels.py job-family product-manager --country 254
```

### Leaderboard (top paying companies)
```bash
python3 ~/.config/scripts/levels.py leaderboard
python3 ~/.config/scripts/levels.py leaderboard --job-family Software-Engineer --level Entry-Level-Engineer --location United-States
python3 ~/.config/scripts/levels.py leaderboard --location-type metro --location San-Francisco-Bay-Area
```

### Benefits Comparison
```bash
python3 ~/.config/scripts/levels.py benefits --companies Google Meta Microsoft
python3 ~/.config/scripts/levels.py benefits --companies Apple Amazon Netflix
```
Returns estimated total value and per-category benefit items per company.

### List / Browse
```bash
python3 ~/.config/scripts/levels.py list-companies --search anthropic
python3 ~/.config/scripts/levels.py job-families
python3 ~/.config/scripts/levels.py industries
python3 ~/.config/scripts/levels.py locations --job-family "Software Engineer"
```

## Notes

- All output is JSON. Pipe to `jq` for filtering: `| jq '.averages'`
- `--country 254` = United States (default)
- Company slugs are lowercase hyphenated: `google`, `meta`, `jane-street`
- Job family slugs: `software-engineer`, `product-manager`, `data-scientist`, etc.
- Level slugs for leaderboard: `Entry-Level-Engineer`, `Senior-Engineer`, `Staff-Engineer`, `Principal-Engineer`
- Location slugs for jobs: `san-francisco-bay-area`, `new-york-city`, `seattle`, `remote`
