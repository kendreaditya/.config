#!/usr/bin/env python3
"""recall — an SM-2 spaced-repetition store for things the user decided or learned with Claude.

Stdlib only. Cards are one JSON file each under ~/.claude/recall/cards/, so they
diff cleanly in git and stay readable without this script.

  recall.py add --q "..." --a "..." [--tag t]... [--source path] [--why "..."]
  recall.py due [--limit N] [--json]
  recall.py grade <id> <0-5>
  recall.py list [--tag t] [--all] [--json]
  recall.py show <id>
  recall.py edit <id> [--q ...] [--a ...] [--why ...] [--add-tag t] [--rm-tag t]
  recall.py rm <id>
  recall.py stats
"""

import argparse
import json
import os
import pathlib
import re
import sys
import unicodedata
from datetime import date, timedelta

STORE = pathlib.Path(
    os.environ.get("RECALL_HOME", pathlib.Path.home() / ".claude" / "recall")
)
CARDS = STORE / "cards"

# SM-2 defaults. EF is clamped to [1.3, 2.8]; below 1.3 intervals collapse.
EF_MIN, EF_MAX, EF_START = 1.3, 2.8, 2.5


def today():
    """Today, overridable via RECALL_TODAY=YYYY-MM-DD for deterministic tests."""
    override = os.environ.get("RECALL_TODAY")
    return date.fromisoformat(override) if override else date.today()


def slug(text, maxlen=48):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (text[:maxlen].rstrip("-")) or "card"


def card_path(cid):
    return CARDS / f"{cid}.json"


def load_all():
    CARDS.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(CARDS.glob("*.json")):
        try:
            c = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"warning: skipping unreadable card {p.name}: {e}", file=sys.stderr)
            continue
        c["id"] = p.stem
        out.append(c)
    return out


def save(cid, card):
    CARDS.mkdir(parents=True, exist_ok=True)
    body = {k: v for k, v in card.items() if k != "id"}
    tmp = card_path(cid).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(card_path(cid))


def resolve(cid):
    """Accept a full id or an unambiguous prefix."""
    if card_path(cid).exists():
        return cid
    hits = [c["id"] for c in load_all() if c["id"].startswith(cid)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"no card matching {cid!r}")
    sys.exit(f"{cid!r} is ambiguous ({len(hits)}): " + ", ".join(hits[:8]))


def cmd_add(a):
    cid = slug(a.q)
    if card_path(cid).exists():
        n = 2
        while card_path(f"{cid}-{n}").exists():
            n += 1
        cid = f"{cid}-{n}"
    save(
        cid,
        {
            "q": a.q,
            "a": a.a,
            "why": a.why or "",
            "tags": sorted(set(a.tag or [])),
            "source": a.source or "",
            "created": today().isoformat(),
            "due": today().isoformat(),  # due immediately; first review is the encoding
            "interval": 0,
            "ef": EF_START,
            "reps": 0,
            "lapses": 0,
            "history": [],
        },
    )
    print(cid)


def cmd_due(a):
    now = today().isoformat()
    cards = [c for c in load_all() if c["due"] <= now]
    # Most overdue first, then hardest (lowest ease).
    cards.sort(key=lambda c: (c["due"], c.get("ef", EF_START)))
    if a.limit:
        cards = cards[: a.limit]
    if a.json:
        print(json.dumps(cards, indent=2, ensure_ascii=False))
        return
    if not cards:
        print("nothing due")
        return
    for c in cards:
        overdue = (today() - date.fromisoformat(c["due"])).days
        late = f"  ({overdue}d overdue)" if overdue > 0 else ""
        tags = " ".join(f"#{t}" for t in c.get("tags", []))
        print(f"[{c['id']}]{late} {tags}\n  Q: {c['q']}\n")


def sm2(card, grade):
    """SM-2 (Wozniak). grade 0-5; <3 is a lapse and resets the interval."""
    ef = card.get("ef", EF_START)
    ef = max(EF_MIN, min(EF_MAX, ef + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))))
    if grade < 3:
        card["lapses"] = card.get("lapses", 0) + 1
        card["reps"] = 0
        interval = 1
    else:
        reps = card.get("reps", 0) + 1
        card["reps"] = reps
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = max(1, round(card.get("interval", 1) * ef))
    card["ef"] = round(ef, 3)
    card["interval"] = interval
    card["due"] = (today() + timedelta(days=interval)).isoformat()
    card.setdefault("history", []).append(
        {"date": today().isoformat(), "grade": grade, "interval": interval}
    )
    return card


def cmd_grade(a):
    if not 0 <= a.grade <= 5:
        sys.exit("grade must be 0-5")
    cid = resolve(a.id)
    card = json.loads(card_path(cid).read_text())
    save(cid, sm2(card, a.grade))
    print(f"{cid}: next in {card['interval']}d (due {card['due']}, ef {card['ef']})")


def cmd_list(a):
    cards = load_all()
    if a.tag:
        cards = [c for c in cards if a.tag in c.get("tags", [])]
    if not a.all:
        cards = [c for c in cards if c.get("reps", 0) > 0 or c["due"] <= today().isoformat()]
    cards.sort(key=lambda c: c["due"])
    if a.json:
        print(json.dumps(cards, indent=2, ensure_ascii=False))
        return
    for c in cards:
        tags = " ".join(f"#{t}" for t in c.get("tags", []))
        print(f"{c['due']}  [{c['id']}] {tags}\n    {c['q']}")
    print(f"\n{len(cards)} card(s)")


def cmd_show(a):
    cid = resolve(a.id)
    c = json.loads(card_path(cid).read_text())
    print(f"id:      {cid}")
    print(f"Q:       {c['q']}")
    print(f"A:       {c['a']}")
    if c.get("why"):
        print(f"why:     {c['why']}")
    if c.get("source"):
        print(f"source:  {c['source']}")
    print(f"tags:    {' '.join(c.get('tags', [])) or '-'}")
    print(f"due:     {c['due']}  (interval {c.get('interval', 0)}d, ef {c.get('ef')})")
    print(f"reps:    {c.get('reps', 0)}  lapses: {c.get('lapses', 0)}")
    for h in c.get("history", []):
        print(f"  {h['date']}  grade {h['grade']}  -> {h['interval']}d")


def cmd_edit(a):
    cid = resolve(a.id)
    c = json.loads(card_path(cid).read_text())
    for field in ("q", "a", "why"):
        val = getattr(a, field)
        if val is not None:
            c[field] = val
    tags = set(c.get("tags", []))
    tags |= set(a.add_tag or [])
    tags -= set(a.rm_tag or [])
    c["tags"] = sorted(tags)
    save(cid, c)
    print(f"updated {cid}")


def cmd_rm(a):
    cid = resolve(a.id)
    card_path(cid).unlink()
    print(f"removed {cid}")


def cmd_stats(a):
    cards = load_all()
    if not cards:
        print("no cards yet")
        return
    now = today().isoformat()
    due = [c for c in cards if c["due"] <= now]
    reviewed = [c for c in cards if c.get("reps", 0) > 0 or c.get("lapses", 0) > 0]
    mature = [c for c in cards if c.get("interval", 0) >= 21]
    grades = [h["grade"] for c in cards for h in c.get("history", [])]
    tags = {}
    for c in cards:
        for t in c.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    print(f"cards:    {len(cards)}")
    print(f"due now:  {len(due)}")
    print(f"reviewed: {len(reviewed)}   never reviewed: {len(cards) - len(reviewed)}")
    print(f"mature:   {len(mature)}  (interval >= 21d)")
    if grades:
        print(f"reviews:  {len(grades)}   mean grade: {sum(grades) / len(grades):.2f}")
        print(f"recall:   {100 * sum(g >= 3 for g in grades) / len(grades):.0f}% graded >= 3")
    if tags:
        top = sorted(tags.items(), key=lambda kv: -kv[1])[:10]
        print("tags:     " + ", ".join(f"{t}({n})" for t, n in top))
    weak = sorted(
        (c for c in cards if c.get("lapses", 0) > 0), key=lambda c: -c["lapses"]
    )[:5]
    if weak:
        print("\nweakest:")
        for c in weak:
            print(f"  {c['lapses']} lapse(s)  [{c['id']}] {c['q'][:60]}")


def main():
    p = argparse.ArgumentParser(prog="recall", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add", help="add a card")
    s.add_argument("--q", required=True, help="question (asks for one retrievable fact)")
    s.add_argument("--a", required=True, help="answer")
    s.add_argument("--why", help="why it mattered / what it unblocked")
    s.add_argument("--tag", action="append", help="repeatable")
    s.add_argument("--source", help="file path, PR, or session id")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("due", help="cards due today (questions only)")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_due)

    s = sub.add_parser("grade", help="record a review")
    s.add_argument("id")
    s.add_argument("grade", type=int)
    s.set_defaults(func=cmd_grade)

    s = sub.add_parser("list", help="list cards")
    s.add_argument("--tag")
    s.add_argument("--all", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="full card incl. answer and history")
    s.add_argument("id")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("edit", help="edit a card")
    s.add_argument("id")
    s.add_argument("--q")
    s.add_argument("--a")
    s.add_argument("--why")
    s.add_argument("--add-tag", action="append")
    s.add_argument("--rm-tag", action="append")
    s.set_defaults(func=cmd_edit)

    s = sub.add_parser("rm", help="delete a card")
    s.add_argument("id")
    s.set_defaults(func=cmd_rm)

    s = sub.add_parser("stats", help="store health")
    s.set_defaults(func=cmd_stats)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
