"""
Shared helpers for mm.py. Auth, pagination, tag resolution, diagnostics.

All state lives inside the skill folder — nothing in $HOME.
"""
import asyncio
import json
import os
import sys
from collections import defaultdict

# Skill paths (self-contained — no ~/.mm, no external state)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(SKILL_DIR, "state")
SESSION_FILE = os.path.join(STATE_DIR, "session.json")
TAG_RULES_FILE = os.path.join(STATE_DIR, "tag_rules.json")
CONFIG_FILE = os.path.join(STATE_DIR, "config.json")

VENV_PYTHON = os.path.expanduser("~/.config/config-venv/bin/python3")

# Intent-based tag taxonomy. IDs resolved dynamically from the API.
TAG_INTENTS = {
    "Housing": "Keeping a roof over my head — rent, renters insurance, housing-related utilities.",
    "Transportation": "Cost of mobility itself — gas, EV charging, car insurance, auto loan, transit, rideshare.",
    "Essential Expenses": "Spending required for basic well-being (food I need to eat, laundry). Not for fun, not for friends.",
    "Parental Support": "For my parents / supporting them — Wise transfers home, flights to visit parents, money helping them directly.",
    "Discretionary Spending": "Solo wants for myself — leisure purchases driven by desire, not need and not for others.",
    "Subscription": "Recurring services (Apple, domains, SaaS).",
    "Receipt Import": "Tracking artifact for manually imported receipts — not an intent tag.",
    "Krishna Consciousness / Charity / RAK": "Giving to others with no return expected — charity, random acts of kindness, spiritual/temple-related.",
    "Relationships & Social Connection": "Intent of being *with* people I care about — meals with friends, Venmo/Zelle to people, group outings.",
    "Experiences / Travel": "Deliberate experiences/trips. Rarely used — most travel falls under Discretionary (solo) or Parental (visiting parents).",
    "Health & Wellness": "Investing in physical/mental health — supplements, gym, health tracking.",
    "HSA": "Qualifies for HSA reimbursement — medical, pharmacy, some wellness.",
}

TAG_ALIASES = {
    "rak": "Krishna Consciousness / Charity / RAK",
    "charity": "Krishna Consciousness / Charity / RAK",
    "krishna": "Krishna Consciousness / Charity / RAK",
    "social": "Relationships & Social Connection",
    "relationships": "Relationships & Social Connection",
    "discretionary": "Discretionary Spending",
    "essential": "Essential Expenses",
    "parental": "Parental Support",
    "travel": "Experiences / Travel",
    "experiences": "Experiences / Travel",
    "health": "Health & Wellness",
    "wellness": "Health & Wellness",
    "sub": "Subscription",
    "transport": "Transportation",
    "house": "Housing",
    "housing": "Housing",
}


def _extract_csrf(cookie_str: str) -> str:
    """Pull csrftoken value out of a `Cookie:` header string."""
    if not cookie_str:
        return ""
    for part in cookie_str.split(";"):
        k, _, v = part.strip().partition("=")
        if k.lower() == "csrftoken":
            return v
    return ""


def parse_curl_to_session(curl_text: str) -> dict:
    """Parse a `curl 'https://api.monarch.com/...'` (Chrome 'Copy as cURL') and
    return a session dict ready to write to session.json."""
    import re
    out = {}
    # cookie: header
    m = re.search(r"-H ['\"]cookie: ([^'\"]+)['\"]", curl_text, re.I)
    if m:
        out["cookie"] = m.group(1)
        csrf = _extract_csrf(out["cookie"])
        if csrf:
            out["csrftoken"] = csrf
    # explicit -b 'cookies'
    m = re.search(r"-b ['\"]([^'\"]+)['\"]", curl_text)
    if m and "cookie" not in out:
        out["cookie"] = m.group(1)
        csrf = _extract_csrf(out["cookie"])
        if csrf:
            out["csrftoken"] = csrf
    # device-uuid
    m = re.search(r"-H ['\"]device-uuid: ([0-9a-f-]+)['\"]", curl_text, re.I)
    if m:
        out["device_uuid"] = m.group(1)
    # x-csrftoken (override the cookie-extracted one if present)
    m = re.search(r"-H ['\"]x-csrftoken: ([^'\"]+)['\"]", curl_text, re.I)
    if m:
        out["csrftoken"] = m.group(1)
    return out


def reexec_in_venv():
    if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)


async def get_client():
    from monarchmoney import MonarchMoney
    from monarchmoney.monarchmoney import RequireMFAException

    mm = MonarchMoney(session_file=SESSION_FILE)
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            raw = f.read().strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            # New auth (post-2026): cookie + csrftoken (HttpOnly sessionid).
            # session.json shape:
            #   {"cookie": "sessionid=...; csrftoken=...", "csrftoken": "...",
            #    "device_uuid": "..."}  (csrftoken + device_uuid optional but recommended)
            cookie = data.get("cookie") or data.get("cookies")
            if cookie:
                csrf = data.get("csrftoken") or _extract_csrf(cookie)
                device = data.get("device_uuid") or data.get("deviceUuid")
                # Strip any default Token auth — Monarch no longer accepts it
                mm._headers.pop("Authorization", None)
                mm._headers["Cookie"] = cookie
                if csrf:
                    mm._headers["X-CSRFToken"] = csrf
                if device:
                    mm._headers["device-uuid"] = device
                mm._headers.setdefault("client-platform", "web")
                mm._headers.setdefault("monarch-client", "monarch-core-web-app-graphql")
                mm._headers.setdefault("origin", "https://app.monarch.com")
                mm._headers.setdefault("referer", "https://app.monarch.com/")
                return mm
            # Legacy auth: Authorization: Token XXXXX (pre-2026)
            token = data.get("token") or data.get("authToken")
            if token:
                mm.set_token(token)
                mm._headers["Authorization"] = f"Token {token}"
                return mm
        mm.load_session(SESSION_FILE)
        return mm

    email = os.environ.get("MONARCH_EMAIL")
    password = os.environ.get("MONARCH_PASSWORD")
    mfa_secret = os.environ.get("MONARCH_MFA_SECRET")
    if not email or not password:
        print(f"ERROR: No session at {SESSION_FILE}. Run `mm.py doctor` for setup.", file=sys.stderr)
        sys.exit(1)
    try:
        await mm.login(email, password, mfa_secret_key=mfa_secret)
    except RequireMFAException:
        if not mfa_secret:
            print("ERROR: MFA required — set MONARCH_MFA_SECRET env var", file=sys.stderr)
            sys.exit(1)
        mfa_code = input("Enter MFA code: ")
        await mm.multi_factor_authenticate(email, password, mfa_code)
    os.makedirs(STATE_DIR, exist_ok=True)
    mm.save_session(SESSION_FILE)
    return mm


async def fetch_all_transactions(mm, start_date=None, end_date=None, page_size=500):
    all_t = []
    offset = 0
    while True:
        kwargs = {"limit": page_size, "offset": offset}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        r = await mm.get_transactions(**kwargs)
        batch = r["allTransactions"]["results"]
        total = r["allTransactions"]["totalCount"]
        all_t.extend(batch)
        if len(all_t) >= total or not batch:
            break
        offset += page_size
    return all_t


_TAG_ID_CACHE = None


async def resolve_tag_map(mm):
    global _TAG_ID_CACHE
    if _TAG_ID_CACHE is not None:
        return _TAG_ID_CACHE
    tags = await mm.get_transaction_tags()
    name_to_id, id_to_name = {}, {}
    for t in tags["householdTransactionTags"]:
        name_to_id[t["name"]] = t["id"]
        id_to_name[t["id"]] = t["name"]
    _TAG_ID_CACHE = {"name_to_id": name_to_id, "id_to_name": id_to_name}
    return _TAG_ID_CACHE


async def resolve_tag(mm, name_or_id: str) -> str:
    s = name_or_id.strip()
    if not s:
        raise ValueError("empty tag")
    if s.isdigit():
        return s
    tags = await resolve_tag_map(mm)
    if s in tags["name_to_id"]:
        return tags["name_to_id"][s]
    alias = TAG_ALIASES.get(s.lower())
    if alias and alias in tags["name_to_id"]:
        return tags["name_to_id"][alias]
    for name, tid in tags["name_to_id"].items():
        if name.lower() == s.lower():
            return tid
    matches = [n for n in tags["name_to_id"] if n.lower().startswith(s.lower())]
    if len(matches) == 1:
        return tags["name_to_id"][matches[0]]
    raise ValueError(
        f"Unknown tag '{name_or_id}'. Available: {', '.join(sorted(tags['name_to_id']))}"
    )


def build_confidence(txns):
    """Per-merchant tag confidence: {merchant: {top_tag_id, top_tag_name, confidence, sample_size}}"""
    merchant_tags = defaultdict(lambda: defaultdict(int))
    for t in txns:
        if not t.get("tags"):
            continue
        merchant = (t.get("merchant") or {}).get("name", "Unknown")
        for tag in t["tags"]:
            merchant_tags[merchant][(tag["id"], tag["name"])] += 1

    result = {}
    for merchant, counts in merchant_tags.items():
        total = sum(counts.values())
        top_key, top_count = max(counts.items(), key=lambda kv: kv[1])
        result[merchant] = {
            "top_tag_id": top_key[0],
            "top_tag_name": top_key[1],
            "confidence": round(top_count / total, 3),
            "sample_size": total,
        }
    return result


def detect_clusters(txns, day_gap=2, min_size=3):
    """Detect temporal clusters of transactions within `day_gap` days of each other."""
    from datetime import date as Date

    sorted_txns = sorted(txns, key=lambda t: t["date"])
    clusters = []
    current = []

    for t in sorted_txns:
        t_date = Date.fromisoformat(t["date"])
        if not current:
            current.append(t)
        else:
            last_date = Date.fromisoformat(current[-1]["date"])
            if (t_date - last_date).days <= day_gap:
                current.append(t)
            else:
                if len(current) >= min_size:
                    clusters.append(current)
                current = [t]
    if len(current) >= min_size:
        clusters.append(current)

    result = {}
    for i, cluster in enumerate(clusters):
        dates = [Date.fromisoformat(t["date"]) for t in cluster]
        min_d, max_d = min(dates), max(dates)
        merchants = sorted(set(
            (t.get("merchant") or {}).get("name", "Unknown") for t in cluster
        ))
        if min_d == max_d:
            date_str = min_d.strftime("%b %-d")
        elif min_d.month == max_d.month:
            date_str = f"{min_d.strftime('%b %-d')}-{max_d.day}"
        else:
            date_str = f"{min_d.strftime('%b %-d')}-{max_d.strftime('%b %-d')}"

        info = {
            "cluster_id": i + 1,
            "size": len(cluster),
            "date_range": date_str,
            "merchants": merchants,
        }
        for t in cluster:
            result[t["id"]] = info

    return result


def load_tag_rules():
    if not os.path.exists(TAG_RULES_FILE):
        return {"rules": []}
    with open(TAG_RULES_FILE) as f:
        return json.load(f)


def save_tag_rules(data):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(TAG_RULES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


SEED_RULES = [
    {"merchant": "ChargePoint", "tag": "Transportation"},
    {"merchant": "Geico", "tag": "Transportation"},
    {"merchant": "Volkswagen Credit", "tag": "Transportation"},
    {"merchant": "Volkswagen", "tag": "Transportation"},
    {"merchant": "ExxonMobil", "tag": "Transportation"},
    {"merchant": "Fastrak", "tag": "Transportation"},
    {"merchant": "Express Car Wash", "tag": "Transportation"},
    {"merchant": "O'Reilly Auto Parts", "tag": "Transportation"},
    {"merchant": "Hertz", "tag": "Transportation"},
    {"merchant": "Hertz Rent-A-Car", "tag": "Transportation"},
    {"merchant": "Hertz Car Rental", "tag": "Transportation"},
    {"merchant": "California Department of Motor Vehicles", "tag": "Transportation"},
    {"merchant": "top fuel", "tag": "Transportation"},
    {"merchant": "Evgo", "tag": "Transportation"},
    {"merchant": "Rose Family Limi", "tag": "Housing"},
    {"merchant": "Rose Family Limi Web", "tag": "Housing"},
    {"merchant": "AppFolio", "tag": "Housing"},
    {"merchant": "Lemonade", "tag": "Housing"},
    {"merchant": "Check #107", "tag": "Housing"},
    {"merchant": "Sweetgreen", "tag": "Essential Expenses"},
    {"merchant": "Taco Bell", "tag": "Essential Expenses"},
    {"merchant": "Chipotle", "tag": "Essential Expenses"},
    {"merchant": "DoorDash", "tag": "Essential Expenses"},
    {"merchant": "Lucky Supermarkets", "tag": "Essential Expenses"},
    {"merchant": "Lucky", "tag": "Essential Expenses"},
    {"merchant": "Costco", "tag": "Essential Expenses"},
    {"merchant": "Whole Foods", "tag": "Essential Expenses"},
    {"merchant": "WASH", "tag": "Essential Expenses"},
    {"merchant": "Walmart", "tag": "Essential Expenses"},
    {"merchant": "Vitality Bowls", "tag": "Essential Expenses"},
    {"merchant": "Fresh Healthy Cafe", "tag": "Essential Expenses"},
    {"merchant": "Merit Vegan Restaurant", "tag": "Essential Expenses"},
    {"merchant": "Santa Clara Grocery", "tag": "Essential Expenses"},
    {"merchant": "Courtesy Pay Withdrawal", "tag": "Essential Expenses"},
]


# ---------------- Doctor diagnostics ----------------

def _pip_install(packages):
    import subprocess
    pip = os.path.join(os.path.dirname(VENV_PYTHON), "pip")
    subprocess.run([pip, "install", "--quiet", "--upgrade"] + packages, check=True)


def _patch_base_url():
    """Ensure installed monarchmoney uses api.monarch.com (not api.monarchmoney.com)."""
    import monarchmoney
    lib_path = os.path.join(os.path.dirname(monarchmoney.__file__), "monarchmoney.py")
    with open(lib_path) as f:
        src = f.read()
    if "api.monarchmoney.com" in src:
        src = src.replace("https://api.monarchmoney.com", "https://api.monarch.com")
        with open(lib_path, "w") as f:
            f.write(src)
        # Invalidate bytecode cache
        import shutil
        cache = os.path.join(os.path.dirname(lib_path), "__pycache__")
        if os.path.isdir(cache):
            shutil.rmtree(cache, ignore_errors=True)
        return True
    return False


async def run_doctor(fix=False):
    """
    Diagnose (and optionally fix) the skill's environment.
    Returns exit code: 0 = healthy, 1 = fixable issues found, 2 = manual action required.
    """
    issues = []  # (severity, message, fix_fn or None)

    # 1. Python venv
    if not os.path.exists(VENV_PYTHON):
        issues.append(("fatal", f"No Python at {VENV_PYTHON}. Create a venv first: python3 -m venv ~/.config/config-venv", None))
    else:
        print(f"✅ venv: {VENV_PYTHON}")

    # 2. monarch library installed + which package
    #    Prefer the community fork (monarchmoneycommunity) — it has ongoing fixes.
    #    Both ship the `monarchmoney` module, so import path is identical.
    pkg_dist = None
    try:
        try:
            from importlib.metadata import distribution
        except ImportError:
            from importlib_metadata import distribution
        for name in ("monarchmoneycommunity", "monarchmoney"):
            try:
                d = distribution(name)
                pkg_dist = (name, d.version)
                break
            except Exception:
                continue
    except Exception:
        pass

    if pkg_dist is None:
        def _install_mm():
            _pip_install(["monarchmoneycommunity"])
        issues.append(("fixable", "monarch library not installed", _install_mm))
    else:
        pkg_name, pkg_ver = pkg_dist
        print(f"✅ {pkg_name} installed (version {pkg_ver})")
        if pkg_name == "monarchmoney":
            def _switch_to_community():
                _pip_install(["--upgrade", "--force-reinstall", "monarchmoneycommunity"])
            issues.append(("fixable",
                           "Using legacy monarchmoney — community fork (monarchmoneycommunity) is actively maintained and fixes get_budgets",
                           _switch_to_community))

    # 3. gql version — community fork needs >=4; legacy needs <4
    on_community = pkg_dist is not None and pkg_dist[0] == "monarchmoneycommunity"
    try:
        import gql
        ver = gql.__version__
        if on_community:
            if ver.startswith(("0.", "1.", "2.", "3.")):
                def _bump_gql():
                    _pip_install(["gql>=4,<5"])
                issues.append(("fixable", f"gql {ver} too old for monarchmoneycommunity (need >=4)", _bump_gql))
            else:
                print(f"✅ gql {ver} (compatible with community fork)")
        else:
            if ver.startswith("4"):
                def _pin_gql():
                    _pip_install(["gql>=3.5,<4"])
                issues.append(("fixable", f"gql {ver} is incompatible with legacy monarchmoney (need <4)", _pin_gql))
            else:
                print(f"✅ gql {ver} (compatible)")
    except ImportError:
        def _install_gql():
            _pip_install(["gql>=4,<5"] if on_community else ["gql>=3.5,<4"])
        issues.append(("fixable", "gql not installed", _install_gql))

    # 4. BASE_URL patch
    try:
        import monarchmoney  # re-import in case it was just installed
        lib_path = os.path.join(os.path.dirname(monarchmoney.__file__), "monarchmoney.py")
        if os.path.exists(lib_path):
            with open(lib_path) as f:
                src = f.read()
            if "api.monarchmoney.com" in src:
                issues.append(("fixable", "monarchmoney library points at api.monarchmoney.com (wrong domain)", _patch_base_url))
            else:
                print(f"✅ BASE_URL → api.monarch.com")
    except ImportError:
        pass  # Already flagged above

    # 5. Session file
    if not os.path.exists(SESSION_FILE):
        issues.append(("manual",
                       f"No session at {SESSION_FILE}. Grab browser session (see SKILL.md) and save as JSON.",
                       None))
    else:
        try:
            with open(SESSION_FILE) as f:
                data = json.load(f)
            has_token = bool(data.get("token") or data.get("authToken"))
            has_cookie = bool(data.get("cookie") or data.get("cookies"))
            if has_cookie:
                print(f"✅ Session file present (cookie auth)")
            elif has_token:
                print(f"✅ Session file present (legacy token auth — may be rejected by current API)")
            else:
                issues.append(("manual", "session.json exists but has no cookie/token field", None))
        except json.JSONDecodeError:
            issues.append(("manual", "session.json is not valid JSON", None))

    # 6. State dir
    os.makedirs(STATE_DIR, exist_ok=True)

    # Apply fixes
    fixable = [i for i in issues if i[0] == "fixable"]
    manual = [i for i in issues if i[0] == "manual"]
    fatal = [i for i in issues if i[0] == "fatal"]

    for sev, msg, _ in fatal:
        print(f"❌ {msg}")
    for sev, msg, _ in manual:
        print(f"⚠️  {msg}")
    for sev, msg, _ in fixable:
        print(f"{'🔧' if fix else '⚠️ '} {msg}")

    if fix and fixable:
        print("\n-- Applying fixes --")
        for sev, msg, fn in fixable:
            if fn:
                try:
                    fn()
                    print(f"✅ Fixed: {msg}")
                except Exception as e:
                    print(f"❌ Fix failed for '{msg}': {e}")
                    return 2

    # 7. API smoke test (only if no fatal/manual issues)
    if fatal or manual:
        return 2
    if fixable and not fix:
        print("\nRun `mm.py doctor --fix` to auto-repair.")
        return 1

    print("\n-- API smoke test --")
    try:
        mm = await get_client()
        accounts = await mm.get_accounts()
        n = len(accounts.get("accounts", []))
        print(f"✅ API reachable — {n} accounts")
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print("   Token may be expired. Grab a fresh one from the browser (see SKILL.md).")
        return 2

    # 8. Seed tag_rules if missing
    if not os.path.exists(TAG_RULES_FILE):
        save_tag_rules({"rules": SEED_RULES})
        print(f"✅ Seeded {len(SEED_RULES)} default tag rules → {TAG_RULES_FILE}")

    print("\n✅ Healthy.")
    return 0
