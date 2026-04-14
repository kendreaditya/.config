#!/usr/bin/env python3
"""
Best Buy per-store open box inventory checker.

Queries each (SKU, condition, store) combo individually to find which specific
store has each open box unit physically on the shelf RIGHT NOW.

Usage:
  BBY_API_KEY=key ZIP=33620 SEARCH="macbook pro 14" [BRAND=Apple] python3 bestbuy_store_inventory.py

Or pass SKUs directly (bypasses search):
  BBY_API_KEY=key ZIP=33620 SKUS="6602748,6615860,6565873" python3 bestbuy_store_inventory.py

Env vars:
  BBY_API_KEY  — required
  ZIP          — your zip code (default 33620)
  SEARCH       — product search query (e.g., "macbook pro 14")
  BRAND        — optional manufacturer filter
  SKUS         — comma-separated SKUs (skips search if set)
  N_STORES     — number of nearest stores to check (default 8)
  RADIUS       — store search radius in miles (default 100)
"""

import json, time, os, sys, urllib.parse, requests
from playwright.sync_api import sync_playwright

API_KEY = os.environ.get("BBY_API_KEY", "")
ZIP_CODE = os.environ.get("ZIP", "33620")
SEARCH_QUERY = os.environ.get("SEARCH", "")
BRAND = os.environ.get("BRAND", "")
SKUS_OVERRIDE = os.environ.get("SKUS", "")
N_STORES = int(os.environ.get("N_STORES", "8"))
RADIUS = int(os.environ.get("RADIUS", "100"))


def nearest_stores(n):
    time.sleep(0.5)
    data = requests.get(
        f"https://api.bestbuy.com/v1/stores(area({ZIP_CODE},{RADIUS}))",
        params={"apiKey": API_KEY, "format": "json", "pageSize": n},
        timeout=15,
    ).json()
    return data.get("stores", [])


def search_products():
    if SKUS_OVERRIDE:
        skus = [s.strip() for s in SKUS_OVERRIDE.split(",")]
        print(f"  Using {len(skus)} SKUs from SKUS env var")
        products = {}
        for sku in skus:
            time.sleep(0.4)
            try:
                r = requests.get(
                    f"https://api.bestbuy.com/v1/products/{sku}.json",
                    params={"apiKey": API_KEY, "show": "sku,name,salePrice,regularPrice"},
                    timeout=10,
                ).json()
                products[sku] = r.get("name", f"SKU {sku}")
            except Exception:
                products[sku] = f"SKU {sku}"
        return products

    encoded = urllib.parse.quote(SEARCH_QUERY)
    filters = f"search={encoded}&active=true"
    if BRAND:
        filters += f"&manufacturer={urllib.parse.quote(BRAND)}"

    time.sleep(0.5)
    data = requests.get(
        f"https://api.bestbuy.com/v1/products({filters})",
        params={"apiKey": API_KEY, "format": "json", "pageSize": 100, "page": 1,
                "show": "sku,name,salePrice,regularPrice"},
        timeout=15,
    ).json()

    keywords = SEARCH_QUERY.lower().split()
    products = {}
    for p in data.get("products", []):
        name_lower = p.get("name", "").lower()
        if all(kw in name_lower for kw in keywords):
            if any(skip in name_lower for skip in ["applecare", "refurbished", "case for", "cover for"]):
                continue
            products[str(p["sku"])] = p["name"]
    return products


def fetch_ob_prices(skus):
    """Get open box prices per SKU. Individual queries — batch silently drops results."""
    prices = {}
    for sku in skus:
        try:
            r = requests.get(
                f"https://api.bestbuy.com/beta/products/openBox(sku in({sku}))",
                params={"apiKey": API_KEY, "format": "json"}, timeout=10,
            )
            if r.status_code != 200:
                print(f"  [warn] SKU {sku}: HTTP {r.status_code}")
                time.sleep(1.0)
                continue
            for item in r.json().get("results", []):
                for o in item.get("offers", []):
                    prices[(sku, o["condition"])] = o["prices"]["current"]
        except Exception as e:
            print(f"  [warn] SKU {sku}: {e}")
        time.sleep(0.5)
    return prices


def check_store(page, sku, condition, store_id):
    """Check single SKU/condition at single store. Condition MUST be OPEN_BOX_X format."""
    variables = {
        "fulfillmentOptionsInput": {
            "sku": sku,
            "condition": condition,
            "inStorePickup": {"storeId": store_id},
            "shipping": {"destinationZipCode": ZIP_CODE, "effectivePlanPaidMembership": "NULL"},
            "buttonState": {"context": "PDP", "destinationZipCode": ZIP_CODE,
                          "storeId": store_id, "effectivePlanPaidMembership": "NULL"},
        }
    }
    url = f"https://www.bestbuy.com/gateway/graphql/fulfillment?variables={urllib.parse.quote(json.dumps(variables))}"
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=10000)
        if resp and resp.status == 200:
            data = resp.json()
            fo = data.get("data", {}).get("fulfillmentOptions", {})
            btn = fo.get("buttonStates", [{}])[0].get("buttonState", "?")
            inv = False
            for ispu in fo.get("ispuDetails", []):
                for a in (ispu.get("ispuAvailability") or []):
                    if a.get("instoreInventoryAvailable"):
                        inv = True
            return btn, inv
    except Exception:
        pass
    return "ERROR", False


def main():
    if not API_KEY:
        print("ERROR: export BBY_API_KEY=your_key"); sys.exit(1)
    if not SEARCH_QUERY and not SKUS_OVERRIDE:
        print("ERROR: set SEARCH or SKUS env var"); sys.exit(1)

    print(f"\nStep 1: Get nearest {N_STORES} stores to zip {ZIP_CODE}...")
    stores = nearest_stores(N_STORES)
    if not stores:
        print("  No stores found"); sys.exit(1)
    print(f"  {len(stores)} stores found")

    print(f"\nStep 2: Find products...")
    products = search_products()
    print(f"  {len(products)} products found")
    if not products:
        sys.exit(0)

    print(f"\nStep 3: Get open box prices (individual per-SKU queries)...")
    prices = fetch_ob_prices(list(products.keys()))
    print(f"  {len(prices)} open box offers across {len(set(s for s,c in prices))} SKUs")
    if not prices:
        print("  No open box deals available for these products.")
        sys.exit(0)

    # Convert lowercase to OPEN_BOX_X format for GraphQL
    to_check = [(sku, f"OPEN_BOX_{cond.upper()}") for (sku, cond) in prices.keys()]
    total = len(to_check) * len(stores)
    print(f"\nStep 4: Check {len(to_check)} offers × {len(stores)} stores = {total} queries...")

    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    proxy_cfg = None
    if proxy_url:
        from urllib.parse import urlparse
        pp = urlparse(proxy_url)
        proxy_cfg = {"server": f"http://{pp.hostname}:{pp.port}",
                     "username": pp.username or "", "password": pp.password or ""}

    chromium_path = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
    if not os.path.exists(chromium_path):
        chromium_path = None

    results = {}
    with sync_playwright() as p:
        launch_args = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-gpu"],
            "proxy": proxy_cfg,
        }
        if chromium_path:
            launch_args["executable_path"] = chromium_path

        browser = p.chromium.launch(**launch_args)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        try:
            page.goto("https://www.bestbuy.com/", wait_until="domcontentloaded", timeout=20000)
            time.sleep(1)
        except Exception:
            pass

        done = 0
        for sku, cond in to_check:
            for s in stores:
                btn, inv = check_store(page, sku, cond, str(s["storeId"]))
                results[(sku, cond, str(s["storeId"]))] = (btn, inv)
                done += 1
                if done % 20 == 0:
                    print(f"  {done}/{total}...", end="\r")
                time.sleep(0.2)

        browser.close()

    print(f"  {done}/{total} done.                ")

    # Per-store grid
    print()
    header = f'{"SKU":<8} {"Model":<35} {"Cond":<5} {"Price":>7}'
    for s in stores:
        sn = s["name"][:9]
        header += f' {sn:<10}'
    print(header)
    print("─" * len(header))

    for sku in products:
        for cond in ["excellent", "good", "fair"]:
            price = prices.get((sku, cond))
            if not price:
                continue
            full_cond = f"OPEN_BOX_{cond.upper()}"
            row = f'{sku:<8} {products[sku][:35]:<35} {cond[:4]:<5} ${price:>6,.0f}'
            for s in stores:
                btn, inv = results.get((sku, full_cond, str(s["storeId"])), ("?", False))
                if inv:           cell = "STOCK"
                elif btn == "ADD_TO_CART":  cell = "ship"
                elif btn == "CHECK_STORES": cell = "—"
                elif btn == "SOLD_OUT":     cell = "SOLD"
                else:                       cell = btn[:5]
                row += f' {cell:<10}'
            print(row)

    # Summary: items physically IN STOCK
    print(f"\n{'═'*90}")
    print("  ITEMS PHYSICALLY IN STOCK AT SPECIFIC STORES")
    print(f"{'═'*90}\n")

    in_stock = []
    for (sku, cond, sid), (btn, inv) in results.items():
        if inv:
            cond_short = cond.replace("OPEN_BOX_", "").lower()
            price = prices.get((sku, cond_short), 0)
            store = next((s for s in stores if str(s["storeId"]) == sid), None)
            sname = store["name"] if store else f"Store {sid}"
            label = products.get(sku, "?")
            in_stock.append((price, label, cond_short, sname, sid))

    in_stock.sort()
    if in_stock:
        for price, label, cond, sname, sid in in_stock:
            print(f"  ${price:>8,.2f}  {label[:50]:<50} {cond:<10} @ {sname} [{sid}]")
    else:
        print("  No items physically on shelves in this area.")
        print("  (Items marked 'ship' can be ordered for delivery or ship-to-store pickup.)")

    print()


if __name__ == "__main__":
    main()
