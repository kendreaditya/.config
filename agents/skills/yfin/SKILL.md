---
name: yfin
description: "Small Yahoo Finance CLI for ticker info + N-year stock returns. Use when the user asks about: stock price, market cap, sector/industry classification, dividend yield, P/E ratio, beta, 52-week range, N-year stock return, company description for a public company. Triggers: 'yfinance', 'yfin', 'stock price', 'market cap of', 'how much has X stock returned', 'sector for ticker', 'industry classification'. Pairs with the levels-fyi skill for cross-checking public/private status (levels gives ticker, yfin returns live data)."
---

# yfin

Small wrapper around the `yfinance` Python package. Wraps `Ticker.info` and `Ticker.history` into a clean JSON CLI.

## Subcommands

- `yfin info <ticker> [--full]` — curated company info (sector, industry, market cap, description, HQ, employees, P/E, beta, 52w range)
- `yfin returns <ticker> [--years 1 2 3 4]` — N-year stock returns as percent change
- `yfin all <ticker> [--years 1 2 3 4]` — info + returns combined (the most useful call for ranking pipelines)

## Usage

```bash
yfin info META                       # Curated info
yfin info META --full                # All ~150+ yfinance fields
yfin returns META --years 1 2 3 5   # Custom year windows
yfin all GOOGL                       # info + returns
yfin all META | jq '.sector, .returns."2y_return_pct"'
```

## When to use

- Need live market cap, sector, or stock returns for a public company.
- Cross-reference levels.fyi `ticker` field → enrich with live data.
- Build company-ranking pipeline that wants `1y_return_pct`, `2y_return_pct`, etc.

## When NOT to use

- Private companies (no ticker → no data). Use `levels company-overview` for those.
- Real-time intraday ticks (yfinance is delayed; use a paid feed for that).
- Fundamentals beyond what `Ticker.info` exposes (use `--full` first; if missing, query SEC EDGAR directly).

## Output

JSON to stdout, indented. Pipe through `jq` for further filtering.

## Pairs well with

- **levels-fyi**: Get `ticker` from `levels company-overview <slug>`, then pass to `yfin all <ticker>` for live data.
- **blind**: For news/anecdotes around a stock movement (`yfin` = numbers, `blind` = stories).

## Gotchas

- Requires `yfinance` installed in `~/workspace/.venv` (already done; reinstall via `~/workspace/.venv/bin/pip install yfinance`).
- yfinance can rate-limit on bursts. For batch enrichment, sleep ~0.5s between tickers.
- Some smaller-cap tickers may have empty `info` dicts; check before parsing.
- Returns calculation uses `auto_adjust=True` and ~252 trading days per year (not exact).
