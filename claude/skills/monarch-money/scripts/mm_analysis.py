#!/usr/bin/env python3
"""
Monarch Money tag analysis script.
- Fetches all transactions
- Builds merchant → tag and category → tag confusion matrices
- Identifies 100% confident auto-tag rules
- Reports total tagged vs untagged
"""
import asyncio
import json
import os
import sys
from collections import defaultdict

VENV_PYTHON = os.path.expanduser("~/.config/config-venv/bin/python3.14")
if sys.executable != VENV_PYTHON:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

from monarchmoney import MonarchMoney

SESSION_FILE = os.path.expanduser("~/.mm/session.json")


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


async def fetch_all_transactions():
    mm = await get_client()

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


def build_matrix(txns):
    merchant_tags = defaultdict(lambda: defaultdict(int))
    merchant_total = defaultdict(int)
    category_tags = defaultdict(lambda: defaultdict(int))
    category_total = defaultdict(int)

    tagged = []
    untagged = []

    for t in txns:
        merchant = t.get("merchant") or {}
        merchant_name = merchant.get("name", "Unknown") if isinstance(merchant, dict) else str(merchant)
        category = t.get("category") or {}
        category_name = category.get("name", "Unknown") if isinstance(category, dict) else str(category)
        tags = t.get("tags") or []
        tag_names = [tag["name"] for tag in tags] if tags else []

        merchant_total[merchant_name] += 1
        category_total[category_name] += 1

        if tag_names:
            tagged.append(t)
            for tag in tag_names:
                merchant_tags[merchant_name][tag] += 1
                category_tags[category_name][tag] += 1
        else:
            untagged.append(t)

    return merchant_tags, merchant_total, category_tags, category_total, tagged, untagged


def compute_confidence(tags_dict, total_dict):
    results = []
    for key, tag_counts in tags_dict.items():
        total_tagged = sum(tag_counts.values())
        total = total_dict[key]
        top_tag = max(tag_counts, key=tag_counts.get)
        top_count = tag_counts[top_tag]
        confidence = top_count / total_tagged
        coverage = total_tagged / total

        results.append({
            "key": key,
            "total": total,
            "total_tagged": total_tagged,
            "coverage": round(coverage, 3),
            "top_tag": top_tag,
            "top_count": top_count,
            "confidence": round(confidence, 3),
            "all_tags": dict(tag_counts),
        })

    results.sort(key=lambda x: (-x["confidence"], -x["coverage"], -x["total"]))
    return results


def print_table(title, rows, min_confidence=0.0, min_total=1):
    print(f"\n{'='*90}")
    print(f"  {title}")
    print(f"{'='*90}")
    print(f"{'Key':<35} {'Total':>6} {'Tagged':>7} {'Coverage':>9} {'Top Tag':<28} {'Conf':>6}")
    print("-" * 95)
    for r in rows:
        if r["confidence"] >= min_confidence and r["total"] >= min_total:
            print(f"{r['key']:<35} {r['total']:>6} {r['total_tagged']:>7} {r['coverage']:>8.0%}  {r['top_tag']:<28} {r['confidence']:>5.0%}")


async def main():
    txns = await fetch_all_transactions()

    merchant_tags, merchant_total, category_tags, category_total, tagged, untagged = build_matrix(txns)

    print(f"\n{'='*90}")
    print(f"  SUMMARY")
    print(f"{'='*90}")
    print(f"  Total transactions:  {len(txns)}")
    print(f"  Tagged:              {len(tagged)} ({len(tagged)/len(txns)*100:.1f}%)")
    print(f"  Untagged:            {len(untagged)} ({len(untagged)/len(txns)*100:.1f}%)")

    merchant_conf = compute_confidence(merchant_tags, merchant_total)
    category_conf = compute_confidence(category_tags, category_total)

    print_table("MERCHANTS — 100% confidence (always same tag when tagged)", merchant_conf, min_confidence=1.0)
    print_table("MERCHANTS — High confidence (>=80%, at least 2 total)", merchant_conf, min_confidence=0.8, min_total=2)
    print_table("CATEGORIES — Tag confidence (>=50%)", category_conf, min_confidence=0.5)

    # Untagged breakdown
    untagged_merchants = defaultdict(int)
    untagged_categories = defaultdict(int)
    for t in untagged:
        m = t.get("merchant") or {}
        merchant_name = m.get("name", "Unknown") if isinstance(m, dict) else str(m)
        c = t.get("category") or {}
        category_name = c.get("name", "Unknown") if isinstance(c, dict) else str(c)
        untagged_merchants[merchant_name] += 1
        untagged_categories[category_name] += 1

    print(f"\n{'='*90}")
    print(f"  UNTAGGED — Top merchants (top 40, with suggested tag if known)")
    print(f"{'='*90}")
    merchant_conf_map = {r["key"]: r for r in merchant_conf}
    for merchant, count in sorted(untagged_merchants.items(), key=lambda x: -x[1])[:40]:
        suggestion = ""
        if merchant in merchant_conf_map:
            r = merchant_conf_map[merchant]
            suggestion = f"  → {r['top_tag']} ({r['confidence']:.0%} conf)"
        print(f"  {merchant:<35} {count:>4} untagged{suggestion}")

    print(f"\n{'='*90}")
    print(f"  UNTAGGED — By category (with suggested tag if known)")
    print(f"{'='*90}")
    category_conf_map = {r["key"]: r for r in category_conf}
    for cat, count in sorted(untagged_categories.items(), key=lambda x: -x[1]):
        suggestion = ""
        if cat in category_conf_map:
            r = category_conf_map[cat]
            suggestion = f"  → {r['top_tag']} ({r['confidence']:.0%} conf)"
        print(f"  {cat:<35} {count:>4} untagged{suggestion}")

    # Save full data
    out_path = os.path.expanduser("~/Downloads/mm_tag_analysis.json")
    output = {
        "total": len(txns),
        "tagged_count": len(tagged),
        "untagged_count": len(untagged),
        "merchant_confidence": merchant_conf,
        "category_confidence": category_conf,
        "untagged_transactions": [
            {
                "id": t["id"],
                "date": t.get("date"),
                "merchant": (t.get("merchant") or {}).get("name", "Unknown"),
                "amount": t.get("amount"),
                "category": (t.get("category") or {}).get("name", "Unknown"),
                "notes": t.get("notes"),
            }
            for t in untagged
        ],
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Full analysis saved to {out_path}")


asyncio.run(main())
