---
name: bestbuy
description: Search Best Buy for products, find open box deals, and check per-store inventory at nearby Best Buy locations. Use whenever the user asks about Best Buy prices, open box deals, store availability, finding products at Best Buy, comparing Best Buy with Amazon or other retailers, MacBook Pro/laptop/camera/TV deals at Best Buy, or whether specific items are physically in stock at nearby Best Buy stores. Also use when user mentions "open box" without specifying a retailer (Best Buy is the major US retailer with a real open box program).
---

# Best Buy Search

A skill for finding the best deals at Best Buy — combining new prices, open box prices across all conditions (Fair/Good/Excellent), and **real per-store physical inventory** at user's nearby stores.

## What this skill does

1. **Product search** — find SKUs matching what the user wants
2. **New pricing** — current sale + MSRP from public API
3. **Open box pricing** — Excellent/Good/Fair condition prices
4. **Per-store inventory** — which specific stores have the open box unit physically on the shelf RIGHT NOW
5. **Best deal comparison** — ranked by savings, with availability

## Required setup

- **Best Buy API key** — free from [developer.bestbuy.com](https://developer.bestbuy.com), set as `BBY_API_KEY` env var
- **Python venv** with `requests` and `playwright` installed
- **Chromium** for Playwright (uses `/opt/pw-browsers/chromium-1194/...` if available, else default)

## Quick workflow

```python
# Run the bundled script:
BBY_API_KEY=yourkey ZIP=33620 SEARCH="macbook pro 14" python3 scripts/bestbuy_search.py
```

For per-store open box inventory specifically:
```python
BBY_API_KEY=yourkey ZIP=33620 python3 scripts/bestbuy_store_inventory.py
```

## Critical gotchas — learned the hard way

These are the specific bugs and limitations you'll hit if you don't know them. Don't skip:

### 1. Beta Open Box API: query SKUs INDIVIDUALLY, not in batches

The endpoint `beta/products/openBox(sku in(SKU1,SKU2,...))` is supposed to accept up to 100 SKUs in one call, but **it silently drops most results** when batched. Out of 27 MacBook SKUs in one batch query, only 10 came back. Querying each SKU individually returned 20+. Always loop:

```python
for sku in skus:
    r = requests.get(f"https://api.bestbuy.com/beta/products/openBox(sku in({sku}))",
                     params={"apiKey": API_KEY, "format": "json"}, timeout=10)
    time.sleep(0.5)  # rate limit
```

### 2. Open Box conditions: `OPEN_BOX_EXCELLENT` vs `excellent`

The beta API returns conditions as lowercase: `"excellent"`, `"good"`, `"fair"`.
The GraphQL fulfillment endpoint requires uppercase with prefix: `"OPEN_BOX_EXCELLENT"`, `"OPEN_BOX_GOOD"`, `"OPEN_BOX_FAIR"`.

When converting between them:
```python
graphql_cond = f"OPEN_BOX_{api_cond.upper()}"  # excellent -> OPEN_BOX_EXCELLENT
```

If you forget this, the GraphQL endpoint returns errors silently and every store shows as "unavailable." This was a subtle bug that hid real per-store data.

### 3. Per-store open box inventory: use the GET fulfillment endpoint correctly

There are TWO ways to query the GraphQL fulfillment endpoint, and they return different things:

**Wrong way** — `searchNearby: true, showNearbyLocations: true` returns the same `instoreInventoryAvailable` value for ALL stores. This is just a global "exists in network" flag, not per-store inventory.

**Right way** — query each store INDIVIDUALLY without `searchNearby`:
```python
variables = {
    "fulfillmentOptionsInput": {
        "sku": sku,
        "condition": "OPEN_BOX_EXCELLENT",  # MUST be the OPEN_BOX_X format
        "inStorePickup": {"storeId": store_id},  # NO searchNearby
        "shipping": {"destinationZipCode": zip, "effectivePlanPaidMembership": "NULL"},
        "buttonState": {"context": "PDP", "destinationZipCode": zip,
                        "storeId": store_id, "effectivePlanPaidMembership": "NULL"},
    }
}
url = f"https://www.bestbuy.com/gateway/graphql/fulfillment?variables={urllib.parse.quote(json.dumps(variables))}"
```

Then check `data.fulfillmentOptions.ispuDetails[0].ispuAvailability[0].instoreInventoryAvailable`. When it's `true`, the unit is physically at THAT specific store. When `false` but `pickupEligible: true`, it can be ship-to-store.

The button state interprets:
- `ADD_TO_CART` = available for purchase (likely on shelf or shippable)
- `CHECK_STORES` = exists somewhere but NOT at this specific store
- `SOLD_OUT` = no units anywhere
- `NOT_AVAILABLE` = condition doesn't exist

### 4. Akamai blocks POST to `/gateway/graphql`, but GET to `/gateway/graphql/fulfillment` works

The richer `MarketplaceBuyingOptions` query is a POST and gets blocked by Akamai TLS fingerprinting (especially through proxies). Stick with the GET fulfillment endpoint — it's enough to determine per-store availability via the `instoreInventoryAvailable` flag.

### 5. Product search: URL-encode spaces as `%20`, not `+`

```python
# Bad — returns 400 errors:
url = "https://api.bestbuy.com/v1/products(search=macbook+pro+14)"

# Good:
url = "https://api.bestbuy.com/v1/products(search=macbook%20pro%2014)"
```

### 6. Free tier rate limits

- ~2 requests/second across endpoints — add `time.sleep(0.3-0.5)` between calls
- Pagination breaks past page 3 — use `pageSize=100, page=1` and filter locally
- Stores call + product call back-to-back: add a 0.5s delay between

### 7. Playwright in proxied environments

If `HTTPS_PROXY` env var is set (e.g., cloud sandboxes), pass it to Chromium:
```python
proxy_url = os.environ.get("HTTPS_PROXY")
proxy_cfg = None
if proxy_url:
    pp = urlparse(proxy_url)
    proxy_cfg = {"server": f"http://{pp.hostname}:{pp.port}",
                 "username": pp.username or "", "password": pp.password or ""}
browser = p.chromium.launch(headless=True, proxy=proxy_cfg, ...)
```

Without this, you get `ERR_INVALID_AUTH_CREDENTIALS` on every page load.

### 8. "Ghost listings" — API price exists but no inventory anywhere

The beta API caches prices and may show open box deals that are actually sold out everywhere. ALWAYS verify availability via the per-store check before recommending a deal. A $706 M3 MacBook Pro that's sold out nationwide is misleading.

## Workflow patterns

### Find best deals on a specific product line

1. Get user's zip code (default to user's known location if mentioned)
2. Get nearest stores: `v1/stores(area(ZIP,100))`, sort by distance, take 5-8
3. Search products: `v1/products(search=QUERY&active=true&manufacturer=BRAND)`
4. Filter results in Python (the API search is loose — match on name keywords)
5. For EACH SKU individually, query open box prices from beta endpoint
6. Build (sku, condition) tuples with prices
7. For EACH (sku, condition, store) combo, query GraphQL fulfillment endpoint
8. Aggregate: which units are physically IN STOCK at which specific stores
9. Present as table sorted by either price or savings

### Compare with other retailers

If the user shares Amazon/other retailer prices (screenshots, copy/paste), build a side-by-side table. Best Buy usually wins on:
- High-end Pro/Max configs (open box discounts)
- Configurations Amazon doesn't carry (e.g., 18-core M5 Pro)

Amazon usually wins on:
- Base model new prices
- Used/3rd party offers ($150-300 below Best Buy new)

### Output format

For per-store inventory results, present as:

```
| Price | Model | Condition | Store(s) with unit on shelf |
|-------|-------|-----------|------------------------------|
| $1,587 | M4 Pro 24GB/512GB | Fair | Wesley Chapel [1405] |
```

Include the store ID in brackets — useful if user wants to call.

## Best Buy API endpoints reference

| Endpoint | Method | What it returns |
|----------|--------|-----------------|
| `v1/stores(area(ZIP,MILES))` | GET | Nearby stores (id, name, distance, hours, phone) |
| `v1/products(search=QUERY&...)` | GET | Product catalog search |
| `v1/products/{sku}.json` | GET | Single product full details |
| `v1/categories(name=PATTERN)` | GET | Category tree |
| `beta/products/openBox(sku in(SKU))` | GET | Open box prices + conditions |
| `gateway/graphql/fulfillment?variables=...` | GET | Per-store fulfillment + inventory |

## Tampa-area store IDs (saved for reference)

Common stores users in Tampa Bay area might want to check:

| ID | Name | City |
|----|------|------|
| 561 | South Tampa | Tampa |
| 462 | Citrus Park | Tampa |
| 560 | Brandon | Brandon |
| 564 | Clearwater | Clearwater |
| 565 | St. Petersburg | St Pete |
| 1405 | Wesley Chapel | Wesley Chapel |
| 885 | Port Richey | Port Richey |
| 563 | Lakeland | Lakeland |

## Bundled scripts

- `scripts/bestbuy_search.py` — full product + open box price report
- `scripts/bestbuy_store_inventory.py` — per-store inventory checker (the most useful one)

Both accept `BBY_API_KEY` env var. Read them when adapting for new product searches — the patterns are reusable.
