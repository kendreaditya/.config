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

See `references/api.md` for full Python method signatures.
