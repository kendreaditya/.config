---
name: monarch-money
description: "Monarch Money (mm) personal finance API. Query accounts, transactions, budgets, cashflow, recurring expenses, and net worth. Mutate transactions (create/update/delete), set budgets, and refresh accounts. Use when user asks about: Monarch Money, my budget, my transactions, my accounts, my spending, cashflow, net worth, recurring expenses, financial summary."
---

# Monarch Money

All operations go through `mm.py` — a single CLI wrapping the `monarchmoney` Python library. Everything the skill needs lives inside this folder: scripts, state (session, rules), and docs. No external state directories.

## Quick start

```bash
# Diagnose + auto-fix the environment (idempotent; safe to re-run anytime)
mm.py doctor --fix

# Most common workflow
mm.py month-review                          # summary + anomaly flags (current month)
mm.py untagged 2026-04-01 2026-04-30        # untagged expenses with live suggestions
mm.py set-tags <id> social                  # tag by name or alias
```

Let `mm.py` = `~/.config/config-venv/bin/python3 ~/.config/claude/skills/monarch-money/scripts/mm.py`.

## First-time setup

**Email/password login is blocked by Cloudflare** — must use a browser session token.

1. Open `https://app.monarch.com/dashboard`, DevTools console (⌘⌥J), run:
   ```js
   const u = JSON.parse(JSON.parse(localStorage['persist:root']).user); copy(JSON.stringify({token: u.token}))
   ```
2. Save to the skill's state folder:
   ```bash
   mkdir -p ~/.config/claude/skills/monarch-money/state && pbpaste > ~/.config/claude/skills/monarch-money/state/session.json
   ```
3. Run `mm.py doctor --fix` — installs pinned deps, patches the library's BASE_URL, verifies the API, and seeds default tag rules.

When the token expires, repeat steps 1–2 and re-run `mm.py doctor`.

## Tagging philosophy (IMPORTANT)

Tags reflect the **intent** behind a transaction, not the category or merchant. The same merchant can map to different tags depending on *why* the money was spent. `Panera Bread` can be Essential (solo "need to eat"), Relationships (with friends), or Discretionary (treat).

Never auto-tag a merchant uniformly across all transactions without checking intent. For ambiguous cases, ask the user.

Run `mm.py tags` to see all tags with their intent descriptions.

## Commands

### Setup / health
```
doctor [--fix]                      Diagnose env (install deps, patch BASE_URL, test API)
```

### Read
```
accounts                            All linked accounts
holdings                            Brokerage securities
account-history                     Daily balance history
transactions [--all] [lim] [s] [e]  --all auto-paginates
transaction <id>                    Single detail
transaction-categories              Raw categories JSON
transaction-tags                    Raw tags JSON
tags                                Pretty-printed tags + intent
budgets [year] [month]              Default: current month
cashflow [start] [end]              By category/merchant
cashflow-summary [year] [month]     Income/expense/savings
recurring                           Upcoming recurring txns
subscription                        Account status
```

### Analysis
```
month-review [yyyy-mm]              Summary + anomaly flags + untagged count
untagged [start] [end]              Untagged expenses with live merchant-based suggestions
                                    (computed from trailing 6 months — no cached file)
analyze                             Confusion matrix → ~/Downloads/mm_tag_analysis.json
match-email <txn_id>                Cross-ref Gmail for order contents (via gog)
```

### Write
```
refresh                             Trigger account sync + wait
update-transaction <id> <field> <value>   fields: category_id, notes, reviewed, merchant
set-tags <id> <tag>[,<tag>...]      Names, aliases (RAK, social, essential...), or IDs
bulk-tag [--apply]                  Apply state/tag_rules.json (dry-run default)
bulk-tag --seed-rules               Seed default rules file
set-budget <cat_id> <amount> [y] [m]
logout                              Clear session
```

## Files (all within this skill folder)

| Path | Purpose |
|---|---|
| `scripts/mm.py` | Main CLI (includes `doctor` self-diagnose) |
| `scripts/_mm_common.py` | Shared auth, pagination, tag resolution, doctor logic |
| `state/session.json` | Browser-grabbed auth token. `{"token": "..."}` |
| `state/tag_rules.json` | Deterministic merchant→tag rules for `bulk-tag`. User-editable. |
| `state/config.json` | Optional. e.g. `{"gmail_account": "you@example.com"}` |
| `references/api.md` | `monarchmoney` library method signatures |

Tag suggestions are **computed live** (no cached patterns file). `untagged` pulls the trailing 6 months of history each run and suggests the most-used tag per merchant. Slightly slower but always fresh.

## Tag aliases

Run `mm.py tags` for the live list. Aliases accepted by `set-tags`:

| Alias | Canonical |
|---|---|
| `rak`, `charity`, `krishna` | Krishna Consciousness / Charity / RAK |
| `social`, `relationships` | Relationships & Social Connection |
| `discretionary` | Discretionary Spending |
| `essential` | Essential Expenses |
| `parental` | Parental Support |
| `travel`, `experiences` | Experiences / Travel |
| `health`, `wellness` | Health & Wellness |
| `sub` | Subscription |
| `transport` | Transportation |

Tags also resolve by case-insensitive prefix (e.g. `house` → Housing).

## Common recipes

**Net worth:**
```bash
mm.py accounts | jq '[.accounts[] | select(.includeInNetWorth) | .currentBalance] | add'
```

**Tag a birthday-gift Amazon order as RAK:**
```bash
mm.py set-tags 240968462327610974 rak
```

**Identify a mystery Amazon charge:**
```bash
mm.py match-email <txn_id>
```

**Review the month and spot anomalies:**
```bash
mm.py month-review                 # sign flips, 2σ deviations, large Uncategorized txns
```

**Batch-tag known merchants:**
```bash
# Edit state/tag_rules.json to add:
# {"merchant": "Starbucks", "tag": "Discretionary Spending"}
mm.py bulk-tag                     # dry-run preview
mm.py bulk-tag --apply             # commit
```

## Known issues

- `set_transaction_tags` can fail on split transactions server-side (`TransportQueryError`). `bulk-tag` wraps in try/except and continues; individual `set-tags` prints error and exits 2.
- Monarch's Plaid feed sometimes marks routine 401(k) contributions as `needsReview: true` with category `Uncategorized`. `month-review` will flag these — verify before re-categorizing. This skill was designed to catch exactly this kind of auto-miscategorization (a positive-valued "expense" flipping `sumExpense` sign).
- Library uses `https://api.monarch.com` (not `api.monarchmoney.com`). `doctor --fix` patches the installed package automatically.
- Python venv at `~/.config/config-venv/bin/python3` (shared across skills; Python 3.12). Library needs `gql<4` — `doctor --fix` pins this.

See `references/api.md` for full Python method signatures.
