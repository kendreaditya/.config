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

## Tool

This skill is powered by the `bestbuy` CLI tool (installed at `~/.local/bin/bestbuy`, source at `~/.config/scripts/bestbuy`).

```bash
bestbuy --help                                          # show subcommands
bestbuy stores 33620                                    # nearest Best Buy stores
bestbuy search "macbook pro 14" --zip 33620 --brand Apple   # search + open box prices
bestbuy stock "macbook pro 14" --zip 33620              # per-store physical inventory
bestbuy stock --skus 6602748,6615860 --zip 33620        # check specific SKUs
```

The `stock` subcommand is the killer feature — it tells you which specific store has each open box unit physically on the shelf vs which need ship-to-store.

## Required setup

- **Best Buy API key** — free from [developer.bestbuy.com](https://developer.bestbuy.com), set as `BBY_API_KEY` env var
- **Python venv** with `requests`, `click`, and `playwright` (auto-loaded via `_utils.ensure_config_venv()`)
- **Chromium for Playwright** — uses `/opt/pw-browsers/chromium-1194/...` if available, else default

## Critical gotchas — learned the hard way

These are the specific bugs and limitations that wasted hours. The `bestbuy` CLI handles all of these correctly. Don't rewrite the logic without understanding them:

### 1. Beta Open Box API: query SKUs INDIVIDUALLY, not in batches

The endpoint `beta/products/openBox(sku in(SKU1,SKU2,...))` is supposed to accept up to 100 SKUs in one call, but **silently drops most results** when batched. Out of 27 MacBook SKUs in one batch query, only 10 came back. Querying each SKU individually returned 20+. Always loop:

```python
for sku in skus:
    r = requests.get(f"https://api.bestbuy.com/beta/products/openBox(sku in({sku}))",
                     params={"apiKey": API_KEY, "format": "json"}, timeout=10)
    time.sleep(0.5)  # rate limit
```

### 2. Open Box conditions: `OPEN_BOX_EXCELLENT` vs `excellent`

The beta API returns conditions as lowercase: `"excellent"`, `"good"`, `"fair"`.
The GraphQL fulfillment endpoint requires uppercase with prefix: `"OPEN_BOX_EXCELLENT"`, `"OPEN_BOX_GOOD"`, `"OPEN_BOX_FAIR"`.

```python
graphql_cond = f"OPEN_BOX_{api_cond.upper()}"  # excellent -> OPEN_BOX_EXCELLENT
```

If you forget this, the GraphQL endpoint returns errors silently and every store shows as "unavailable." This was a subtle bug that hid real per-store data.

### 3. Per-store open box inventory: use the GET fulfillment endpoint correctly

Two ways to query the GraphQL fulfillment endpoint return different things:

**Wrong way** — `searchNearby: true, showNearbyLocations: true` returns the same `instoreInventoryAvailable` value for ALL stores. Just a global "exists in network" flag.

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

Check `data.fulfillmentOptions.ispuDetails[0].ispuAvailability[0].instoreInventoryAvailable`. When `true`, the unit is physically at THAT store. When `false` but `pickupEligible: true`, ship-to-store works.

Button state interpretation:
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

- ~2 requests/second across endpoints — `time.sleep(0.3-0.5)` between calls
- Pagination breaks past page 3 — use `pageSize=100, page=1` and filter locally
- Stores call + product call back-to-back: add 0.5s delay between

### 7. Playwright in proxied environments

If `HTTPS_PROXY` env var is set (cloud sandboxes), pass it to Chromium:
```python
proxy_url = os.environ.get("HTTPS_PROXY")
if proxy_url:
    pp = urlparse(proxy_url)
    proxy_cfg = {"server": f"http://{pp.hostname}:{pp.port}",
                 "username": pp.username or "", "password": pp.password or ""}
browser = p.chromium.launch(headless=True, proxy=proxy_cfg, ...)
```

Without this, you get `ERR_INVALID_AUTH_CREDENTIALS` on every page load.

### 8. "Ghost listings" — API price exists but no inventory anywhere

The beta API caches prices and may show open box deals that are actually sold out everywhere. **Always verify availability via the per-store check before recommending a deal.** A $706 M3 MacBook Pro that's sold out nationwide is misleading. The `bestbuy stock` subcommand handles this by showing real button states (SOLD vs STOCK vs ship).

## Workflow patterns

### Find best deals on a specific product line

Just run `bestbuy stock`. It does:
1. Get nearest stores via `v1/stores(area(ZIP,100))`
2. Search products via `v1/products(search=...&active=true)`, filter to keyword matches
3. For each SKU individually, query open box prices from beta endpoint
4. For each (sku, condition, store) combo, query GraphQL fulfillment
5. Print per-store grid + summary of what's physically on shelves

### Compare with other retailers

If the user shares Amazon prices (screenshots, copy/paste), build a side-by-side table. Best Buy usually wins on:
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
