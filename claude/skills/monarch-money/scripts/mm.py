#!/usr/bin/env python3
"""
Monarch Money helper script.
Uses the monarchmoney Python library (https://github.com/hammem/monarchmoney).

Usage:
  python3 mm.py <command> [args...]

Commands:
  accounts                          - List all accounts
  holdings                          - List account holdings
  account-history                   - Daily account balance history
  transactions [limit] [start] [end] - List transactions (default limit=100)
  transaction <id>                  - Get single transaction details
  transaction-categories            - List all categories
  transaction-tags                  - List all tags
  budgets [year] [month]            - Get budgets (default: current month)
  cashflow [start] [end]            - Cashflow by category/merchant
  cashflow-summary [year] [month]   - Income/expense/savings summary
  recurring                         - Upcoming recurring transactions
  subscription                      - Account subscription status
  refresh                           - Refresh all accounts and wait
  update-transaction <id> <field> <value>  - Update a transaction field
                                           fields: category_id, notes, reviewed, merchant
  set-budget <category_id> <amount> [year] [month]  - Set budget amount

Auth via env vars:
  MONARCH_EMAIL, MONARCH_PASSWORD, MONARCH_MFA_SECRET (base32 TOTP key)

Session is cached at ~/.mm/session.json for reuse.
"""
import asyncio
import json
import os
import sys

VENV_PYTHON = os.path.expanduser("~/.config/config-venv/bin/python3.14")
if sys.executable != VENV_PYTHON:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

from monarchmoney import MonarchMoney  # noqa: E402
from monarchmoney.monarchmoney import RequireMFAException  # noqa: E402


SESSION_FILE = os.path.expanduser("~/.mm/session.json")


async def get_client() -> MonarchMoney:
    mm = MonarchMoney(session_file=SESSION_FILE)
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            raw = f.read().strip()
        try:
            # JSON format (token grabbed from browser)
            data = json.loads(raw)
            token = data.get("token") or data.get("authToken")
            if token:
                mm.set_token(token)
                mm._headers["Authorization"] = f"Token {token}"
                return mm
        except json.JSONDecodeError:
            pass
        # Fallback: pickle format (saved by library itself)
        mm.load_session(SESSION_FILE)
        return mm

    email = os.environ.get("MONARCH_EMAIL")
    password = os.environ.get("MONARCH_PASSWORD")
    mfa_secret = os.environ.get("MONARCH_MFA_SECRET")

    if not email or not password:
        print("ERROR: Set MONARCH_EMAIL and MONARCH_PASSWORD env vars", file=sys.stderr)
        sys.exit(1)

    try:
        await mm.login(email, password, mfa_secret_key=mfa_secret)
    except RequireMFAException:
        if not mfa_secret:
            print("ERROR: MFA required — set MONARCH_MFA_SECRET env var", file=sys.stderr)
            sys.exit(1)
        mfa_code = input("Enter MFA code: ")
        await mm.multi_factor_authenticate(email, password, mfa_code)

    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    mm.save_session(SESSION_FILE)
    return mm


def out(data):
    print(json.dumps(data, indent=2, default=str))


async def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "logout":
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            print("Session cleared.")
        else:
            print("No session to clear.")
        return

    mm = await get_client()

    if cmd == "accounts":
        out(await mm.get_accounts())

    elif cmd == "holdings":
        out(await mm.get_account_holdings())

    elif cmd == "account-history":
        out(await mm.get_account_history())

    elif cmd == "transactions":
        limit = int(args[1]) if len(args) > 1 else 100
        start = args[2] if len(args) > 2 else None
        end = args[3] if len(args) > 3 else None
        kwargs = {"limit": limit}
        if start:
            kwargs["start_date"] = start
        if end:
            kwargs["end_date"] = end
        out(await mm.get_transactions(**kwargs))

    elif cmd == "transaction":
        if len(args) < 2:
            print("Usage: transaction <id>", file=sys.stderr)
            sys.exit(1)
        out(await mm.get_transaction_details(args[1]))

    elif cmd == "transaction-categories":
        out(await mm.get_transaction_categories())

    elif cmd == "transaction-tags":
        out(await mm.get_transaction_tags())

    elif cmd == "budgets":
        import datetime
        now = datetime.date.today()
        year = int(args[1]) if len(args) > 1 else now.year
        month = int(args[2]) if len(args) > 2 else now.month
        out(await mm.get_budgets(start_date=f"{year}-{month:02d}-01"))

    elif cmd == "cashflow":
        kwargs = {}
        if len(args) > 1:
            kwargs["start_date"] = args[1]
        if len(args) > 2:
            kwargs["end_date"] = args[2]
        out(await mm.get_cashflow(**kwargs))

    elif cmd == "cashflow-summary":
        import datetime
        now = datetime.date.today()
        year = int(args[1]) if len(args) > 1 else now.year
        month = int(args[2]) if len(args) > 2 else now.month
        out(await mm.get_cashflow_summary(start_month=month, start_year=year,
                                          end_month=month, end_year=year))

    elif cmd == "recurring":
        out(await mm.get_recurring_transactions())

    elif cmd == "subscription":
        out(await mm.get_subscription_details())

    elif cmd == "refresh":
        print("Requesting account refresh (waiting for completion)...")
        await mm.request_accounts_refresh_and_wait()
        print("Refresh complete.")

    elif cmd == "update-transaction":
        if len(args) < 4:
            print("Usage: update-transaction <id> <field> <value>", file=sys.stderr)
            print("Fields: category_id, notes, reviewed, merchant", file=sys.stderr)
            sys.exit(1)
        txn_id, field, value = args[1], args[2], args[3]
        if field == "reviewed":
            value = value.lower() in ("true", "1", "yes")
        kwargs = {field: value}
        out(await mm.update_transaction(txn_id, **kwargs))

    elif cmd == "set-budget":
        if len(args) < 3:
            print("Usage: set-budget <category_id> <amount> [year] [month]", file=sys.stderr)
            sys.exit(1)
        import datetime
        now = datetime.date.today()
        cat_id = args[1]
        amount = float(args[2])
        year = int(args[3]) if len(args) > 3 else now.year
        month = int(args[4]) if len(args) > 4 else now.month
        out(await mm.set_budget_amount(category_id=cat_id, amount=amount,
                                       start_month=month, start_year=year))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
