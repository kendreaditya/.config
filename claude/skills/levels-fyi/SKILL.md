---
name: levels-fyi
description: "levels.fyi CLI — query salary, total compensation, job listings, company benefits, locations, industries, and leaderboards from levels.fyi. Unofficial but robust wrapper around their public API. No auth, no API key. Use when the user asks about: compensation, total comp, TC, salary at $company for $role, E5/L6/T4 pay, what does Meta pay, Google L6 comp, Apple ICT5 salary, comparing comp across companies, finding tech jobs by level, company benefits comparison, top paying companies, job families at a company. Triggers: 'levels.fyi', 'what does X pay', 'how much is comp at', 'salary at company', 'TC for $role', 'E5 at Meta', 'L6 at Google', 'comp at $company', 'top paying tech companies', 'levels leaderboard'."
---

# levels-fyi

Query levels.fyi compensation data, job listings, and company info from the shell. Unofficial but works via their public JSON endpoints.

## Subcommands (run `levels <cmd> --help` for each)

- `search-company <name>` — find company by name → get ID/slug
- `list-companies` — all companies (~61K universe)
- `company-overview <slug>` — ticker, public/private, valuation, HQ, vesting, tags, related companies. Use `--full` for all fields.
- `company-salaries <company> <job-family>` — salary distribution for a company + role family. Each sample includes `yearsOfExperience` so you can compute level-to-YoE mapping.
- `jobs` — search job listings (filters: company, location, level, etc.)
- `job-family <slug>` — details for a job family (e.g. `software-engineer`)
- `job-families` — all job family categories
- `industries` — all industries
- `locations` — all locations by region
- `benefits` — compare benefits across companies
- `leaderboard` — top-paying companies

## Usage examples

```bash
levels search-company "Meta"                         # find Meta's slug
levels company-salaries meta software-engineer       # all SWE comp at Meta
levels jobs --company google --level L6              # L6 jobs at Google
levels leaderboard --job-family software-engineer    # top-paying SWE companies
levels benefits meta google apple                    # compare benefits
```

All subcommands support `--json` for machine-readable output (pipe through `jq`).

## When to use

- User asks about compensation at a specific company/level.
- Compare TC across multiple offers.
- Research comp bands before negotiating.
- Pull job listings by level/company/location.

## When NOT to use

- Anything requiring login (your saved favorites, my-profile data).
- Real-time salary offers (data is crowd-sourced + lagging).
- Negotiation advice beyond raw numbers — use Blind skill for commentary.

## Pairs well with

- **blind**: for anecdotal comp/negotiation threads (`levels` = numbers, `blind` = stories)
- **jq**: all output supports `--json` for piping

## Gotchas

- Response uses AES-encrypted payloads; `pycryptodome` is required (auto-installed in config venv).
- Company slugs are normalized (spaces → hyphens, lowercase). Use `search-company` first if unsure.
- Job family slugs: `software-engineer`, `product-manager`, `data-scientist`, etc. Run `job-families` to list.
- `company-overview` returns `estimated_valuation` and `emp_count` from levels.fyi's stored snapshot — these can be **months to years stale** for fast-growing companies (e.g. Anthropic shows emp_count=45, Stripe valuation=$95B). For live valuations use yfinance (public) or external sources (private). The `ticker` and `company_type` fields ARE reliable for public/private classification.
