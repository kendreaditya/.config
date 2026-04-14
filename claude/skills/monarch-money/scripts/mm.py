#!/usr/bin/env python3
"""
Monarch Money helper (mm). Uses the monarchmoney Python library.

Usage: python3 mm.py <command> [args...]

SETUP:
  doctor [--fix]                         Diagnose env (and fix if --fix)

READ:
  accounts                               List all accounts
  holdings                               List account holdings
  account-history                        Daily account balance history
  transactions [--all] [limit] [start] [end]
                                         List transactions (--all auto-paginates)
  transaction <id>                       Get single transaction details
  transaction-categories                 List all categories
  transaction-tags                       List all tags (raw JSON)
  tags                                   Pretty-print tags + intent descriptions
  budgets [year] [month]                 Get budgets (default: current month)
  cashflow [start] [end]                 Cashflow by category/merchant
  cashflow-summary [year] [month]        Income/expense/savings summary
  recurring                              Upcoming recurring transactions
  subscription                           Account subscription status

ANALYSIS:
  month-review [yyyy-mm]                 Summary + anomaly flags + untagged count
  untagged [start] [end]                 List untagged expenses with live suggestions
  analyze                                Full confusion matrix → ~/Downloads/
  match-email <txn_id>                   Cross-reference Gmail for Amazon/merchant order

WRITE:
  refresh                                Refresh all accounts and wait
  update-transaction <id> <field> <value>
                                         fields: category_id, notes, reviewed, merchant
  set-tags <id> <tag>[,<tag>...]         Set tags (names/aliases/IDs). "" clears.
  bulk-tag [--rules PATH] [--apply]      Apply rules from state/tag_rules.json
  bulk-tag --seed-rules                  Seed default rules file
  set-budget <cat_id> <amount> [year] [month]
  logout                                 Clear session

All state lives in the skill folder under state/. See SKILL.md for setup.
"""
import asyncio
import datetime
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from statistics import mean, stdev

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mm_common import (  # noqa: E402
    CONFIG_FILE, SESSION_FILE, SEED_RULES, STATE_DIR,
    TAG_ALIASES, TAG_INTENTS, TAG_RULES_FILE,
    build_confidence, fetch_all_transactions, get_client,
    load_config, load_tag_rules, reexec_in_venv,
    resolve_tag, resolve_tag_map, run_doctor, save_tag_rules,
)


def out(data):
    print(json.dumps(data, indent=2, default=str))


def month_bounds(year, month):
    import calendar
    last = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def prior_months(year, month, n=3):
    result = []
    for _ in range(n):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        result.append((year, month))
    return result


# ---------------- Commands ----------------

async def cmd_tags(mm):
    tag_map = await resolve_tag_map(mm)
    print(f"{'TAG':<42} {'ID':<22} INTENT")
    print("-" * 90)
    for name, tid in sorted(tag_map["name_to_id"].items()):
        intent = TAG_INTENTS.get(name, "(no description)")
        print(f"{name:<42} {tid:<22} {intent}")


async def cmd_set_tags(mm, txn_id, tag_spec):
    tag_ids = []
    for raw in tag_spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            tag_ids.append(await resolve_tag(mm, raw))
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    try:
        result = await mm.set_transaction_tags(transaction_id=txn_id, tag_ids=tag_ids)
        out(result)
    except Exception as e:
        print(f"ERROR setting tags on {txn_id}: {e}", file=sys.stderr)
        sys.exit(2)


async def cmd_transactions(mm, args):
    all_flag = "--all" in args
    positional = [a for a in args if a != "--all"]
    if all_flag:
        start = positional[0] if len(positional) > 0 else None
        end = positional[1] if len(positional) > 1 else None
        txns = await fetch_all_transactions(mm, start_date=start, end_date=end)
        out({"totalCount": len(txns), "results": txns})
    else:
        limit = int(positional[0]) if positional else 100
        start = positional[1] if len(positional) > 1 else None
        end = positional[2] if len(positional) > 2 else None
        kwargs = {"limit": limit}
        if start:
            kwargs["start_date"] = start
        if end:
            kwargs["end_date"] = end
        out(await mm.get_transactions(**kwargs))


async def cmd_untagged(mm, start=None, end=None):
    """
    List untagged expenses in range, with live tag suggestions.
    Suggestions computed from last 6 months of tagged history (no cached file).
    """
    EXCLUDE_CAT = {"Transfer", "Credit Card Payment", "Buy", "Sell"}

    # Pull the window the user asked about
    target_txns = await fetch_all_transactions(mm, start_date=start, end_date=end)

    # Pull last 6mo of history for live confidence — ending at `end` or today
    ref_end = end or datetime.date.today().isoformat()
    ref_end_dt = datetime.date.fromisoformat(ref_end)
    ref_start_dt = ref_end_dt - datetime.timedelta(days=180)
    history = await fetch_all_transactions(mm, start_date=ref_start_dt.isoformat(),
                                           end_date=ref_end_dt.isoformat())
    confidence = build_confidence(history)

    untagged = [
        t for t in target_txns
        if not t.get("tags") and t["amount"] < 0
        and (t.get("category") or {}).get("name") not in EXCLUDE_CAT
        and not t.get("hideFromReports", False)
    ]
    untagged.sort(key=lambda t: t["date"])
    total = sum(t["amount"] for t in untagged)

    print(f"# {len(untagged)} untagged expense txns, total ${total:,.2f}  (suggestions from trailing 6mo, n={len(history)})")
    print(f"{'ID':<20}\t{'DATE':<11}\t{'AMOUNT':>10}\t{'CATEGORY':<28}\t{'MERCHANT':<32}\tSUGGESTION")
    for t in untagged:
        merchant = (t.get("merchant") or {}).get("name", "")
        category = (t.get("category") or {}).get("name", "")
        sug = confidence.get(merchant)
        sug_str = f"{sug['top_tag_name']} ({int(sug['confidence']*100)}%, n={sug['sample_size']})" if sug else "-"
        print(f"{t['id']:<20}\t{t['date']:<11}\t{t['amount']:>10,.2f}\t{category[:28]:<28}\t{merchant[:32]:<32}\t{sug_str}")


async def cmd_analyze(mm):
    txns = await fetch_all_transactions(mm, start_date="2020-01-01",
                                        end_date=datetime.date.today().isoformat())
    confidence = build_confidence(txns)
    tagged = sum(1 for t in txns if t.get("tags"))
    untagged = len(txns) - tagged

    print(f"\nSummary: {len(txns)} txns, {tagged} tagged ({tagged/len(txns)*100:.1f}%), {untagged} untagged\n")
    print(f"{'MERCHANT':<40} {'N':>4} {'CONF':>6}  TOP TAG")
    print("-" * 95)
    for merchant, data in sorted(confidence.items(), key=lambda kv: (-kv[1]["sample_size"], kv[0])):
        if data["sample_size"] < 2:
            continue
        print(f"{merchant[:40]:<40} {data['sample_size']:>4} {data['confidence']*100:>5.0f}%  {data['top_tag_name']}")

    out_path = os.path.expanduser("~/Downloads/mm_tag_analysis.json")
    with open(out_path, "w") as f:
        json.dump({"total": len(txns), "tagged": tagged, "untagged": untagged,
                   "confidence": confidence}, f, indent=2)
    print(f"\nFull data → {out_path}")


async def cmd_month_review(mm, year, month):
    start, end = month_bounds(year, month)
    summary_raw = await mm.get_cashflow_summary(start_date=start, end_date=end)
    s = summary_raw["summary"][0]["summary"]
    income, expense, savings = s["sumIncome"], s["sumExpense"], s["savings"]

    prior = []
    for (py, pm) in prior_months(year, month, 3):
        ps, pe = month_bounds(py, pm)
        pd = await mm.get_cashflow_summary(start_date=ps, end_date=pe)
        prior.append(pd["summary"][0]["summary"]["sumExpense"])
    avg_expense = mean(prior) if prior else 0

    print(f"\n== {year}-{month:02d} Month Review ==")
    print(f"  Income:   ${income:>12,.2f}")
    print(f"  Expense:  ${expense:>12,.2f}   (trailing 3mo avg: ${avg_expense:,.2f})")
    print(f"  Savings:  ${savings:>12,.2f}")

    anomalies = []
    if expense > 0:
        anomalies.append(f"🚨 sumExpense is POSITIVE (${expense:,.2f}) — check for refunds miscategorized as expenses")

    if len(prior) >= 2:
        sd = stdev(prior)
        if sd > 0 and abs(expense - avg_expense) > 2 * sd:
            anomalies.append(f"⚠️  Expense deviates >2σ from baseline (σ=${sd:,.2f}, Δ=${expense-avg_expense:,.2f})")

    txns = await fetch_all_transactions(mm, start_date=start, end_date=end)
    big_flags = [t for t in txns
                 if abs(t["amount"]) > 5000
                 and (t.get("needsReview") or (t.get("category") or {}).get("name") == "Uncategorized")]
    for t in big_flags:
        anomalies.append(f"🚨 Large txn flagged: {t['date']} ${t['amount']:,.2f} {t['merchant']['name']} (category: {t['category']['name']}, needsReview: {t.get('needsReview')})")

    cf = await mm.get_cashflow(start_date=start, end_date=end)
    cats = [(c["groupBy"]["category"]["name"], c["summary"]["sum"],
             c["groupBy"]["category"]["group"]["type"]) for c in cf["byCategory"]]
    expense_cats = [(n, v) for n, v, t in cats if t == "expense"]
    top5 = sorted(expense_cats, key=lambda x: x[1])[:5]

    print("\n  Top 5 expense categories:")
    for name, val in top5:
        print(f"    {name:<32} ${val:>10,.2f}")

    flipped = [(n, v) for n, v, t in cats if t == "expense" and v > 0]
    for n, v in flipped:
        anomalies.append(f"🚨 Expense category has POSITIVE sum: {n} = ${v:,.2f} (refund miscategorized?)")

    EXCLUDE = {"Transfer", "Credit Card Payment", "Buy", "Sell"}
    untagged = [t for t in txns
                if not t.get("tags") and t["amount"] < 0
                and (t.get("category") or {}).get("name") not in EXCLUDE
                and not t.get("hideFromReports", False)]
    untagged_total = sum(t["amount"] for t in untagged)
    print(f"\n  Untagged expense txns: {len(untagged)} (${untagged_total:,.2f})")

    if anomalies:
        print("\n  Anomalies:")
        for a in anomalies:
            print(f"    {a}")
    else:
        print("\n  ✅ No anomalies detected")
    print()


async def cmd_bulk_tag(mm, args):
    if "--seed-rules" in args:
        save_tag_rules({"rules": SEED_RULES})
        print(f"Seeded {len(SEED_RULES)} rules → {TAG_RULES_FILE}")
        return

    apply = "--apply" in args
    rules_path = TAG_RULES_FILE
    if "--rules" in args:
        i = args.index("--rules")
        rules_path = args[i + 1]

    if not os.path.exists(rules_path):
        print(f"No rules file at {rules_path}. Run with --seed-rules first.", file=sys.stderr)
        sys.exit(1)

    with open(rules_path) as f:
        rules_data = json.load(f)
    rules = rules_data.get("rules", [])

    txns = await fetch_all_transactions(mm, start_date="2020-01-01",
                                        end_date=datetime.date.today().isoformat())
    to_tag = []
    for t in txns:
        if t.get("tags"):
            continue
        merchant = (t.get("merchant") or {}).get("name", "")
        category = (t.get("category") or {}).get("name", "")
        for rule in rules:
            if rule.get("category") and rule["category"] != category:
                continue
            match = False
            if rule.get("merchant") == merchant:
                match = True
            elif rule.get("merchant_regex") and re.match(rule["merchant_regex"], merchant):
                match = True
            if match:
                to_tag.append((t, rule["tag"]))
                break

    grouped = defaultdict(list)
    for t, tag in to_tag:
        grouped[tag].append(t)

    print(f"{'=' * 70}")
    print(f"  {'DRY RUN — ' if not apply else ''}BULK TAG PLAN: {len(to_tag)} txns")
    print(f"{'=' * 70}")
    for tag, txns_in in sorted(grouped.items()):
        print(f"\n  [{tag}] — {len(txns_in)} txns")
        merchant_counts = defaultdict(int)
        for t in txns_in:
            merchant_counts[t["merchant"]["name"]] += 1
        for m, c in sorted(merchant_counts.items(), key=lambda kv: -kv[1]):
            print(f"    {m:<40} {c:>3}")

    if not apply:
        print("\n  Run with --apply to actually tag.")
        return

    resolved_cache = {}
    for _, tag in to_tag:
        if tag not in resolved_cache:
            try:
                resolved_cache[tag] = await resolve_tag(mm, tag)
            except ValueError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)

    ok = fail = 0
    for t, tag in to_tag:
        try:
            await mm.set_transaction_tags(transaction_id=t["id"], tag_ids=[resolved_cache[tag]])
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  ERROR {t['id']}: {e}", file=sys.stderr)
    print(f"\n  Done: {ok} tagged, {fail} errors")


async def cmd_match_email(mm, txn_id):
    cfg = load_config()
    gmail_account = cfg.get("gmail_account", "kendreaditya@gmail.com")

    detail = await mm.get_transaction_details(txn_id)
    t = detail["getTransaction"]
    amount = abs(t["amount"])
    date = t["date"]
    merchant = t["merchant"]["name"]

    domain_map = {"Amazon": "amazon.com", "Apple": "apple.com",
                  "DoorDash": "doordash.com", "Uber": "uber.com"}
    domain = None
    for k, v in domain_map.items():
        if k.lower() in merchant.lower():
            domain = v
            break
    if not domain:
        domain = merchant.lower().replace(" ", "") + ".com"

    from datetime import datetime as dt, timedelta
    dt_obj = dt.strptime(date, "%Y-%m-%d")
    after = (dt_obj - timedelta(days=5)).strftime("%Y/%m/%d")
    before = (dt_obj + timedelta(days=5)).strftime("%Y/%m/%d")

    query = f"from:{domain} after:{after} before:{before}"
    print(f"# Searching Gmail ({gmail_account}): {query}", file=sys.stderr)

    proc = subprocess.run(
        ["gog", "-a", gmail_account, "gmail", "search", query, "--limit", "30", "-p"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"gog failed: {proc.stderr}", file=sys.stderr)
        sys.exit(1)

    lines = proc.stdout.strip().split("\n")
    if len(lines) < 2:
        print(f"No emails from {domain} near {date}")
        return
    header = lines[0].split("\t")
    id_idx = header.index("ID")
    subj_idx = header.index("SUBJECT")

    print(f"# Checking {len(lines)-1} emails for total matching ${amount:.2f}")
    for line in lines[1:]:
        cols = line.split("\t")
        email_id = cols[id_idx]
        subject = cols[subj_idx]
        body_proc = subprocess.run(
            ["gog", "-a", gmail_account, "gmail", "get", email_id, "--format", "full"],
            capture_output=True, text=True,
        )
        if body_proc.returncode != 0:
            continue
        body = body_proc.stdout
        matches = re.findall(r"(?:Total|Grand Total|Order Total)[^\d\-]{0,30}\$?\s*([\d,]+\.\d{2})", body, re.IGNORECASE)
        for m in matches:
            val = float(m.replace(",", ""))
            if abs(val - amount) < 0.02:
                print(f"\n✅ MATCH: {subject}")
                for i, l in enumerate(body.split("\n")):
                    if l.strip().startswith("*") and i + 1 < len(body.split("\n")):
                        if "Quantity" in body.split("\n")[i + 1]:
                            print(f"  {l.strip()}")
                return
    print(f"No matching email found (checked {len(lines)-1} messages)")


# ---------------- Main dispatcher ----------------

async def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    # Doctor runs without re-exec (checks venv itself)
    if cmd == "doctor":
        fix = "--fix" in args
        sys.exit(await run_doctor(fix=fix))

    reexec_in_venv()

    if cmd == "logout":
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            print("Session cleared.")
        else:
            print("No session to clear.")
        return

    mm = await get_client()
    now = datetime.date.today()

    if cmd == "accounts":
        out(await mm.get_accounts())
    elif cmd == "holdings":
        out(await mm.get_account_holdings())
    elif cmd == "account-history":
        out(await mm.get_account_history())
    elif cmd == "transactions":
        await cmd_transactions(mm, args[1:])
    elif cmd == "transaction":
        if len(args) < 2:
            print("Usage: transaction <id>", file=sys.stderr)
            sys.exit(1)
        out(await mm.get_transaction_details(args[1]))
    elif cmd == "transaction-categories":
        out(await mm.get_transaction_categories())
    elif cmd == "transaction-tags":
        out(await mm.get_transaction_tags())
    elif cmd == "tags":
        await cmd_tags(mm)
    elif cmd == "budgets":
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
        year = int(args[1]) if len(args) > 1 else now.year
        month = int(args[2]) if len(args) > 2 else now.month
        start, end = month_bounds(year, month)
        out(await mm.get_cashflow_summary(start_date=start, end_date=end))
    elif cmd == "recurring":
        out(await mm.get_recurring_transactions())
    elif cmd == "subscription":
        out(await mm.get_subscription_details())
    elif cmd == "refresh":
        print("Requesting account refresh...")
        await mm.request_accounts_refresh_and_wait()
        print("Refresh complete.")
    elif cmd == "month-review":
        if len(args) > 1:
            ym = args[1]
            year, month = int(ym[:4]), int(ym[5:7])
        else:
            year, month = now.year, now.month
        await cmd_month_review(mm, year, month)
    elif cmd == "untagged":
        start = args[1] if len(args) > 1 else None
        end = args[2] if len(args) > 2 else None
        await cmd_untagged(mm, start, end)
    elif cmd == "analyze":
        await cmd_analyze(mm)
    elif cmd == "match-email":
        if len(args) < 2:
            print("Usage: match-email <txn_id>", file=sys.stderr)
            sys.exit(1)
        await cmd_match_email(mm, args[1])
    elif cmd == "update-transaction":
        if len(args) < 4:
            print("Usage: update-transaction <id> <field> <value>", file=sys.stderr)
            sys.exit(1)
        txn_id, field, value = args[1], args[2], args[3]
        if field == "reviewed":
            value = value.lower() in ("true", "1", "yes")
        out(await mm.update_transaction(txn_id, **{field: value}))
    elif cmd == "set-tags":
        if len(args) < 3:
            print("Usage: set-tags <txn_id> <tag>[,<tag>...]", file=sys.stderr)
            print('       Tags may be names, aliases (RAK, social, essential...), or IDs.', file=sys.stderr)
            sys.exit(1)
        await cmd_set_tags(mm, args[1], args[2])
    elif cmd == "bulk-tag":
        await cmd_bulk_tag(mm, args[1:])
    elif cmd == "set-budget":
        if len(args) < 3:
            print("Usage: set-budget <category_id> <amount> [year] [month]", file=sys.stderr)
            sys.exit(1)
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
