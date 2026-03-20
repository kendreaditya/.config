# Monarch Money Python API Reference

All methods are `async`. Use `asyncio.run()` or `await` inside an async context.

```python
from monarchmoney import MonarchMoney
import asyncio

mm = MonarchMoney()
asyncio.run(mm.login("email", "password", mfa_secret_key="BASE32SECRET"))
mm.save_session()  # cache to ~/.mm/session.json by default
```

## Auth

| Method | Description |
|--------|-------------|
| `await mm.login(email, password, mfa_secret_key=None)` | Login; raises `RequireMFAException` if MFA needed without key |
| `await mm.multi_factor_authenticate(email, password, code)` | Login with TOTP code |
| `await mm.interactive_login()` | Interactive prompt (Jupyter/iPython) |
| `mm.save_session(filepath)` | Persist session |
| `mm.load_session(filepath)` | Restore session |

## Read Methods

```python
await mm.get_accounts()
await mm.get_account_holdings()
await mm.get_account_history()
await mm.get_institutions()
await mm.get_subscription_details()

await mm.get_transactions(
    limit=100,
    start_date="YYYY-MM-DD",  # optional
    end_date="YYYY-MM-DD",    # optional
    search="",                # optional text search
    category_ids=[],          # optional filter
    account_ids=[],           # optional filter
)
await mm.get_transaction_details(transaction_id)
await mm.get_transactions_summary()
await mm.get_transaction_categories()
await mm.get_transaction_category_groups()
await mm.get_transaction_tags()
await mm.get_transaction_splits(transaction_id)

await mm.get_budgets(start_date="YYYY-MM-DD")
await mm.get_cashflow(start_date="YYYY-MM-DD", end_date="YYYY-MM-DD")
await mm.get_cashflow_summary(
    start_month, start_year, end_month, end_year
)
await mm.get_recurring_transactions()
await mm.is_accounts_refresh_complete()
```

## Write Methods

```python
# Transactions
await mm.create_transaction(
    date="YYYY-MM-DD", merchant_name="", amount=0.0,
    category_id="", account_id="", notes=""
)
await mm.update_transaction(
    transaction_id,
    category_id=None, notes=None, reviewed=None, merchant=None
)
await mm.delete_transaction(transaction_id)
await mm.update_transaction_splits(transaction_id, splits=[])
await mm.set_transaction_tags(transaction_id, tag_ids=[])
await mm.create_transaction_tag(name)

# Categories
await mm.create_transaction_category(name, group_id)
await mm.delete_transaction_category(category_id)
await mm.delete_transaction_categories(category_ids=[])

# Budgets
await mm.set_budget_amount(
    category_id, amount,
    start_month, start_year,
    end_month=None, end_year=None  # defaults to start if omitted
)

# Accounts
await mm.create_manual_account(name, type, balance)
await mm.update_account(account_id, **fields)
await mm.delete_account(account_id)
await mm.upload_account_balance_history(account_id, history=[])

# Refresh
await mm.request_accounts_refresh()              # non-blocking
await mm.request_accounts_refresh_and_wait()     # blocks until done
```
