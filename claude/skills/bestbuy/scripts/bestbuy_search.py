#!/usr/bin/env python3
"""
Best Buy product search + open box deal finder.

Usage:
  BBY_API_KEY=yourkey ZIP=33620 SEARCH="macbook pro 14" [BRAND=Apple] python3 bestbuy_search.py

Env vars:
  BBY_API_KEY  — required, get free at developer.bestbuy.com
  ZIP          — your zip code (default 33620 / USF Tampa)
  SEARCH       — product search query (URL spaces ok)
  BRAND        — optional manufacturer filter (e.g., Apple, Sony)
  RADIUS       — store search radius in miles (default 100)
  N_STORES     — number of nearest stores to show (default 5)
"""

import os, sys, time, json, urllib.parse, requests
from collections import defaultdict
from datetime import datetime

API_KEY = os.environ.get("BBY_API_KEY", "")
ZIP_CODE = os.environ.get("ZIP", "33620")
SEARCH_QUERY = os.environ.get("SEARCH", "")
BRAND = os.environ.get("BRAND", "")
RADIUS = int(os.environ.get("RADIUS", "100"))
N_STORES = int(os.environ.get("N_STORES", "5"))

# ── Stores ───────────────────────────────────────────────────────────────────

def nearest_stores(n=5):
    time.sleep(0.5)
    data = requests.get(
        f"https://api.bestbuy.com/v1/stores(area({ZIP_CODE},{RADIUS}))",
        params={"apiKey": API_KEY, "format": "json", "pageSize": n},
        timeout=15,
    ).json()
    return data.get("stores", [])

# ── Products ─────────────────────────────────────────────────────────────────

def search_products():
    encoded = urllib.parse.quote(SEARCH_QUERY)
    filters = f"search={encoded}&active=true"
    if BRAND:
        filters += f"&manufacturer={urllib.parse.quote(BRAND)}"

    time.sleep(0.5)
    data = requests.get(
        f"https://api.bestbuy.com/v1/products({filters})",
        params={
            "apiKey": API_KEY, "format": "json", "pageSize": 100, "page": 1,
            "show": "sku,name,salePrice,regularPrice,onSale,inStoreAvailability,onlineAvailability,manufacturer",
        },
        timeout=15,
    ).json()

    # Filter results — search is loose, only keep matches with all keywords in name
    keywords = SEARCH_QUERY.lower().split()
    results = []
    for p in data.get("products", []):
        name_lower = p.get("name", "").lower()
        if all(kw in name_lower for kw in keywords):
            # Skip accessories: AppleCare, refurbished, cases
            if any(skip in name_lower for skip in ["applecare", "refurbished", "case for", "cover for"]):
                continue
            results.append(p)
    return results

# ── Open Box (per-SKU individual queries) ────────────────────────────────────

def fetch_open_box_prices(skus):
    """IMPORTANT: Query SKUs individually. Batch queries miss results."""
    ob_data = {}
    for sku in skus:
        try:
            r = requests.get(
                f"https://api.bestbuy.com/beta/products/openBox(sku in({sku}))",
                params={"apiKey": API_KEY, "format": "json"},
                timeout=10,
            )
            results = r.json().get("results", [])
            if results:
                item = results[0]
                offers = {}
                for o in item.get("offers", []):
                    offers[o["condition"]] = {
                        "price": o["prices"]["current"],
                        "regular": o["prices"].get("regular"),
                        "online": o.get("onlineAvailability", False),
                        "instore": o.get("inStoreAvailability", False),
                    }
                ob_data[sku] = {
                    "offers": offers,
                    "msrp": item.get("prices", {}).get("regular"),
                    "reviews": item.get("customerReviews", {}),
                }
        except Exception:
            pass
        time.sleep(0.5)
    return ob_data

# ── Output ───────────────────────────────────────────────────────────────────

def print_report(stores, products, ob_data):
    print("\n" + "═" * 100)
    print(f"  BEST BUY DEAL REPORT — {SEARCH_QUERY}")
    print(f"  Near zip {ZIP_CODE} — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 100)

    # Stores
    print(f"\n{N_STORES} NEAREST STORES:")
    for s in stores:
        print(f"  [{s['storeId']}] {s['name']:<20}  {s['city']}, {s['region']:<3}  {s.get('distance','?')} mi  {s.get('phone','')}")

    # Products with open box
    print(f"\n{'─'*100}")
    print(f"{'SKU':<8} {'Name':<55} {'New':>9} {'OB Exc':>9} {'OB Good':>9} {'OB Fair':>9} {'Best Save':>10}")
    print("─" * 100)

    sorted_products = sorted(products, key=lambda p: p.get("salePrice") or p.get("regularPrice") or 0)

    for p in sorted_products:
        sku = str(p["sku"])
        name = p["name"][:55]
        new_price = p.get("salePrice") or p.get("regularPrice") or 0

        ob = ob_data.get(sku, {})
        offers = ob.get("offers", {})
        msrp = ob.get("msrp") or new_price
        ex = offers.get("excellent", {}).get("price")
        gd = offers.get("good", {}).get("price")
        fr = offers.get("fair", {}).get("price")

        best_ob = min([p for p in [ex, gd, fr] if p], default=None)
        save = round(msrp - best_ob, 2) if best_ob else 0

        ex_s = f"${ex:,.0f}" if ex else "—"
        gd_s = f"${gd:,.0f}" if gd else "—"
        fr_s = f"${fr:,.0f}" if fr else "—"
        save_s = f"${save:,.0f}" if save > 0 else "—"

        print(f"{sku:<8} {name:<55} ${new_price:>8,.0f} {ex_s:>9} {gd_s:>9} {fr_s:>9} {save_s:>10}")

    print(f"\n{'═'*100}")
    print(f"  {len(products)} models · {sum(1 for p in products if str(p['sku']) in ob_data and ob_data[str(p['sku'])]['offers'])} with open box deals")
    print(f"  NOTE: This shows API prices only. For per-store inventory, run bestbuy_store_inventory.py")
    print(f"{'═'*100}\n")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("ERROR: export BBY_API_KEY=your_key (free at developer.bestbuy.com)")
        sys.exit(1)
    if not SEARCH_QUERY:
        print("ERROR: set SEARCH env var, e.g., SEARCH='macbook pro 14'")
        sys.exit(1)

    print(f"\nSearching '{SEARCH_QUERY}' near zip {ZIP_CODE}...")
    stores = nearest_stores(N_STORES)
    print(f"  Got {len(stores)} stores")

    products = search_products()
    print(f"  Found {len(products)} matching products")

    if not products:
        print("\n  No products matched. Try broader search terms or remove BRAND filter.")
        sys.exit(0)

    print(f"  Fetching open box prices ({len(products)} individual queries)...")
    ob_data = fetch_open_box_prices([str(p["sku"]) for p in products])
    has_ob = sum(1 for v in ob_data.values() if v["offers"])
    print(f"  {has_ob} SKUs have open box offers")

    print_report(stores, products, ob_data)

if __name__ == "__main__":
    main()
