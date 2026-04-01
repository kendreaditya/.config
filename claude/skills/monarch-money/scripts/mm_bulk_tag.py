#!/usr/bin/env python3
"""
Bulk tag untagged Monarch Money transactions by merchant.
Applies Transportation, Housing, and Essential Expenses tags.
Dry-run by default — pass --apply to actually tag.
"""
import asyncio
import json
import os
import sys

VENV_PYTHON = os.path.expanduser("~/.config/config-venv/bin/python3.14")
if sys.executable != VENV_PYTHON:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

from monarchmoney import MonarchMoney

SESSION_FILE = os.path.expanduser("~/.mm/session.json")

# Tag IDs from Monarch Money
TAG_IDS = {
    "Transportation":       "209377965282950221",
    "Housing":              "209377996017761359",
    "Essential Expenses":   "209378009181584471",
}

# Merchant → Tag mapping (100% or near-100% confidence from historical data)
MERCHANT_RULES = {
    # Transportation
    "ChargePoint":                              "Transportation",
    "Geico":                                    "Transportation",
    "Volkswagen Credit":                        "Transportation",
    "Volkswagen":                               "Transportation",
    "ExxonMobil":                               "Transportation",
    "Fastrak":                                  "Transportation",
    "Express Car Wash":                         "Transportation",
    "O'Reilly Auto Parts":                      "Transportation",
    "Hertz":                                    "Transportation",
    "Hertz Rent-A-Car":                         "Transportation",
    "Hertz Car Rental":                         "Transportation",
    "California Department of Motor Vehicles":  "Transportation",
    "top fuel":                                 "Transportation",
    "Evgo":                                     "Transportation",

    # Housing
    "Rose Family Limi":                         "Housing",
    "Rose Family Limi Web":                     "Housing",
    "AppFolio":                                 "Housing",
    "Lemonade":                                 "Housing",
    "Check #107":                               "Housing",

    # Essential Expenses
    "Sweetgreen":                               "Essential Expenses",
    "Taco Bell":                                "Essential Expenses",
    "Chipotle":                                 "Essential Expenses",
    "DoorDash":                                 "Essential Expenses",
    "Lucky Supermarkets":                       "Essential Expenses",
    "Lucky":                                    "Essential Expenses",
    "Costco":                                   "Essential Expenses",
    "Whole Foods":                              "Essential Expenses",
    "WASH":                                     "Essential Expenses",
    "Walmart":                                  "Essential Expenses",
    "Vitality Bowls":                           "Essential Expenses",
    "Fresh Healthy Cafe":                       "Essential Expenses",
    "Merit Vegan Restaurant":                   "Essential Expenses",
    "Santa Clara Grocery":                      "Essential Expenses",
    "Courtesy Pay Withdrawal":                  "Essential Expenses",
}


async def get_client():
    mm = MonarchMoney(session_file=SESSION_FILE)
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            raw = f.read().strip()
        try:
            data = json.loads(raw)
            token = data.get("token") or data.get("authToken")
            if token:
                mm.set_token(token)
                mm._headers["Authorization"] = f"Token {token}"
                return mm
        except json.JSONDecodeError:
            pass
        mm.load_session(SESSION_FILE)
    return mm


async def fetch_all_transactions(mm):
    all_txns = []
    limit = 500
    offset = 0
    print("Fetching all transactions...", file=sys.stderr)
    while True:
        result = await mm.get_transactions(
            limit=limit,
            offset=offset,
            start_date="2020-01-01",
            end_date="2026-03-22",
        )
        batch = result["allTransactions"]["results"]
        total = result["allTransactions"]["totalCount"]
        all_txns.extend(batch)
        print(f"  Fetched {len(all_txns)}/{total}", file=sys.stderr)
        if len(all_txns) >= total or len(batch) == 0:
            break
        offset += limit
    return all_txns


async def main():
    dry_run = "--apply" not in sys.argv

    mm = await get_client()
    txns = await fetch_all_transactions(mm)

    # Find untagged transactions that match a merchant rule
    to_tag = []
    for t in txns:
        tags = t.get("tags") or []
        if tags:
            continue  # already tagged

        merchant = t.get("merchant") or {}
        merchant_name = merchant.get("name", "") if isinstance(merchant, dict) else str(merchant)

        if merchant_name in MERCHANT_RULES:
            tag_name = MERCHANT_RULES[merchant_name]
            to_tag.append({
                "id": t["id"],
                "date": t.get("date"),
                "merchant": merchant_name,
                "amount": t.get("amount"),
                "category": (t.get("category") or {}).get("name", ""),
                "tag": tag_name,
                "tag_id": TAG_IDS[tag_name],
            })

    # Group for preview
    by_tag = {}
    for t in to_tag:
        by_tag.setdefault(t["tag"], []).append(t)

    print(f"\n{'='*70}")
    print(f"  {'DRY RUN — ' if dry_run else ''}BULK TAGGING PLAN")
    print(f"{'='*70}")
    print(f"  Total to tag: {len(to_tag)}\n")

    for tag_name, txns_in_group in sorted(by_tag.items()):
        print(f"  [{tag_name}] — {len(txns_in_group)} transactions")
        # Show per-merchant counts
        merchant_counts = {}
        for t in txns_in_group:
            merchant_counts[t["merchant"]] = merchant_counts.get(t["merchant"], 0) + 1
        for merchant, count in sorted(merchant_counts.items(), key=lambda x: -x[1]):
            print(f"    {merchant:<40} {count:>3} txns")
        print()

    if dry_run:
        print("  Run with --apply to apply these tags.")
        return

    # Apply tags
    print(f"\n  Applying tags...")
    success = 0
    errors = 0
    for i, t in enumerate(to_tag):
        try:
            await mm.set_transaction_tags(
                transaction_id=t["id"],
                tag_ids=[t["tag_id"]],
            )
            success += 1
            print(f"  [{i+1}/{len(to_tag)}] {t['tag']:<22} {t['merchant']:<35} ${abs(t['amount']):.2f}  {t['date']}")
        except Exception as e:
            errors += 1
            print(f"  ERROR on {t['id']}: {e}", file=sys.stderr)

    print(f"\n  Done. {success} tagged, {errors} errors.")


asyncio.run(main())
