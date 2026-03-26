---
name: monarch-money
description: "Monarch Money personal finance API. Query accounts, transactions, budgets, cashflow, recurring expenses, and net worth. Mutate transactions (create/update/delete), set budgets, and refresh accounts. Use when user asks about: Monarch Money, my budget, my transactions, my accounts, my spending, cashflow, net worth, recurring expenses, financial summary."
---

# Monarch Money

Access and manage Monarch Money via the `monarchmoney` Python library.

## Setup (One-Time)

**Email/password login is blocked by Cloudflare** — must use a browser session token instead.

**Step 1** — Run this in browser console on app.monarch.com (Cmd+Option+J):
```js
const u = JSON.parse(JSON.parse(localStorage['persist:root']).user); copy(JSON.stringify({token: u.token}))
```

**Step 2** — Run in terminal:
```bash
mkdir -p ~/.mm && pbpaste > ~/.mm/session.json
```

Token is now cached at `~/.mm/session.json` and reused automatically. When it expires, repeat these two steps.

## Running the Helper Script

```bash
~/.config/config-venv/bin/python3.14 ~/.config/claude/skills/monarch-money/scripts/mm.py <command> [args]
```

Output is always JSON — pipe to `jq` for filtering.

## Commands

### Read

```bash
mm.py accounts                           # all linked accounts
mm.py holdings                           # brokerage securities
mm.py account-history                    # daily balance history
mm.py transactions [limit] [start] [end] # e.g. transactions 50 2026-03-01 2026-03-31
mm.py transaction <id>                   # single transaction detail
mm.py transaction-categories             # configured categories (use IDs for updates)
mm.py transaction-tags                   # configured tags
mm.py budgets [year] [month]             # budget vs actual (default: current month)
mm.py cashflow [start] [end]             # cashflow by category/merchant
mm.py cashflow-summary [year] [month]    # income / expenses / savings rollup
mm.py recurring                          # upcoming recurring transactions
mm.py subscription                       # account status (paid/trial)
```

### Write

```bash
mm.py update-transaction <id> category_id <category_id>
mm.py update-transaction <id> notes "lunch with team"
mm.py update-transaction <id> reviewed true
mm.py update-transaction <id> merchant "New Merchant Name"
mm.py set-budget <category_id> <amount> [year] [month]
mm.py refresh                            # trigger + wait for account sync
mm.py logout                             # clear cached session
```

### Tagging Transactions

The `mm.py` script does not expose a tag command — use the Python API directly:

```python
# Set tags on a transaction (overwrites existing tags)
await mm.set_transaction_tags(transaction_id="<id>", tag_ids=["<tag_id>"])

# Multiple tags
await mm.set_transaction_tags(transaction_id="<id>", tag_ids=["<id1>", "<id2>"])

# Remove all tags
await mm.set_transaction_tags(transaction_id="<id>", tag_ids=[])

# Get tag IDs
tags = await mm.get_transaction_tags()
# → tags["householdTransactionTags"][i]["id"], ["name"]
```

Use the `get_client()` helper from any script (see scripts below) — it handles JSON token auth correctly.

**Tag IDs (Aditya's account):**
```python
TAG_IDS = {
    "Housing":                              "209377996017761359",
    "Transportation":                       "209377965282950221",
    "Essential Expenses":                   "209378009181584471",
    "Parental Support":                     "209378020670831705",
    "Discretionary Spending":               "209378014914149464",
    "Subscription":                         "139957970043403485",
    "Receipt Import":                       "235299914760585080",
    "Krishna Consciousness / Charity / RAK":"238987622751141176",
    "Relationships & Social Connection":    "238987623734705465",
    "Experiences / Travel":                 "238987624010480954",
    "Health & Wellness":                    "238987624317713723",
}
```

### Fetching All Transactions (Pagination)

`mm.py transactions` is limited to a single page. To fetch all transactions use offset pagination:

```python
all_txns = []
offset = 0
while True:
    result = await mm.get_transactions(limit=500, offset=offset,
                                       start_date="2020-01-01", end_date="2026-12-31")
    batch = result["allTransactions"]["results"]
    total = result["allTransactions"]["totalCount"]
    all_txns.extend(batch)
    if len(all_txns) >= total or not batch:
        break
    offset += 500
```

### Helper Scripts

Two reusable scripts live in `scripts/`:

**`mm_analysis.py`** — Confusion matrix across all transactions. Shows which merchants always map to the same tag (100% confidence), which are ambiguous, and how many are untagged. Saves full JSON output to `~/Downloads/mm_tag_analysis.json`.
```bash
~/.config/config-venv/bin/python3.14 ~/.config/claude/skills/monarch-money/scripts/mm_analysis.py
```

**`mm_bulk_tag.py`** — Bulk-tags untagged transactions by merchant using a hardcoded rule table. Dry-run by default.
```bash
~/.config/config-venv/bin/python3.14 ~/.config/claude/skills/monarch-money/scripts/mm_bulk_tag.py          # preview
~/.config/config-venv/bin/python3.14 ~/.config/claude/skills/monarch-money/scripts/mm_bulk_tag.py --apply  # apply
```

### Common Patterns

**All accounts with balances:**
```bash
mm.py accounts | jq '.accounts[] | {name: .displayName, balance: .displayBalance, type: .type.display}'
```

**Last 20 transactions:**
```bash
mm.py transactions 20 | jq '.allTransactions.results[] | {date: .date, merchant: .merchant.name, amount: .amount, category: .category.name}'
```

**Net worth:**
```bash
mm.py accounts | jq '[.accounts[] | select(.includeInNetWorth) | .currentBalance] | add'
```

**This month's spending summary:**
```bash
mm.py cashflow-summary | jq '{income: .summary.incomeSum, expenses: .summary.expenseSum, savings: .summary.savingsSum}'
```

**Find category ID before updating:**
```bash
mm.py transaction-categories | jq '.categories[] | select(.name | test("groceries"; "i")) | {id, name}'
```

## Known Issues / Gotchas

- **Cloudflare blocks email/password login** — always use the browser token method above.
- **API domain:** Library was patched from `api.monarchmoney.com` → `api.monarch.com` (PyPI v0.1.15 has wrong domain; patch applied to installed file).
- **Python version:** The venv has two Pythons — `python3` = 3.12 (Anaconda), `python3.14` = Homebrew. `monarchmoney` is installed under 3.14. Always use `python3.14` explicitly.
- **Session format:** `~/.mm/session.json` stores `{"token": "..."}` as JSON (not pickle). The script handles both formats.
- **Token expiry:** If you get auth errors, repeat the browser console → pbpaste steps to refresh the token.
- **`set_transaction_tags` fails on some transactions** — certain transactions (likely split transactions) reject the `setTransactionTags` mutation server-side with a `TransportQueryError`. Always wrap in try/except when bulk-tagging and continue on failure:
  ```python
  try:
      await mm.set_transaction_tags(transaction_id=txn_id, tag_ids=[tag_id])
  except Exception:
      pass  # skip — likely a split transaction
  ```

See `references/api.md` for full Python method signatures.
