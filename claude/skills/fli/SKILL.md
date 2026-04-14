---
name: fli
description: Search Google Flights from the shell using the `fli` CLI. Use when the user asks about flights, airfare, flight search, cheapest day to fly, cheap flights, nonstop options, business/first class fares, travel between two cities or airports, scanning multiple dates or origins, or otherwise wants live flight pricing and schedules. Handles single-date searches (`fli flights`), flexible date-range / cheapest-day scans (`fli dates`), filtering by airline, stops, cabin, layover airport, departure window, bags, and emissions. Always prefer `--format json` so results can be parsed reliably.
---

# fli

Google Flights search via the `fli` CLI (installed via `pipx install flights`). Two subcommands: `fli flights` (one specific date) and `fli dates` (cheapest day across a range).

Always pass `--format json` and parse with python3. The default text output is pretty-printed tables meant for humans, not for the agent.

## Quick start

```bash
# single date, cheapest first
fli flights JFK LAX 2026-06-15 --format json

# cheapest day in a window
fli dates JFK LAX --from 2026-06-01 --to 2026-06-30 --format json
```

IATA airport codes are required (JFK, LAX, LHR, etc.). Resolve ambiguous city names to an IATA code before calling. If the user names a city with multiple airports (NYC -> JFK/LGA/EWR, LON -> LHR/LGW/STN, CHI -> ORD/MDW, WAS -> DCA/IAD/BWI), either ask or fan out across all of them in parallel (see "Parallel scans" below).

## `fli flights` — single date

```
fli flights ORIGIN DEST YYYY-MM-DD [options] --format json
```

Useful flags (short form in parens):

- `--return YYYY-MM-DD` (`-r`) — makes it a round trip
- `--time 6-20` (`-t`) — departure window in 24h hours, `HH-HH`
- `--airlines BA KL` (`-a`) — one or more IATA airline codes, space-separated
- `--class ECONOMY|PREMIUM_ECONOMY|BUSINESS|FIRST` (`-c`)
- `--stops ANY|NON_STOP|ONE_STOP|TWO_PLUS_STOPS` (`-s`). Also accepts `0`, `1`, `2+`.
- `--sort TOP_FLIGHTS|BEST|CHEAPEST|DEPARTURE_TIME|ARRIVAL_TIME|DURATION|EMISSIONS` (`-o`, default CHEAPEST)
- `--exclude-basic` (`-e`) — drop basic-economy fares
- `--layover ORD --layover MDW` (`-l`, repeatable) — restrict connection airports
- `--emissions ALL|LESS`
- `--bags 0|1|2` (`-b`) — include checked-bag fees in the price
- `--carry-on` — include carry-on fee
- `--no-all` — return only ~30 curated results instead of every result
- `--currency CAD` — fallback currency when Google does not return one

Running example (live):

```bash
fli flights TPA PHL 2026-05-15 --airlines F9 --stops NON_STOP --format json
```

## `fli dates` — cheapest-day scan

```
fli dates ORIGIN DEST [options] --format json
```

- `--from YYYY-MM-DD` / `--to YYYY-MM-DD` — inclusive range (defaults to ~next 60 days)
- `--duration N` (`-d`) — trip length in days (requires round-trip)
- `--round` (`-R`) — round-trip mode
- `--airlines`, `--stops`, `--class`, `--time`, `--currency` — same as above
- `--sort` — sort output by price ascending (flag, no argument)
- `--monday` / `--tuesday` / ... / `--sunday` (`-mon`, `-tue`, ...) — restrict to specific weekdays. Repeatable. No day flag = all days.

Example — cheapest Friday-out, 3-day round trip to MIA, nonstop only:

```bash
fli dates LAX MIA --round --duration 3 --friday --stops NON_STOP --sort --format json
```

## JSON schema and parsing

`fli flights` JSON shape:

```json
{
  "success": true,
  "search_type": "flights",
  "query": { "origin": "...", "destination": "...", "departure_date": "...", "...": "..." },
  "count": 42,
  "flights": [
    {
      "duration": 323,
      "stops": 1,
      "price": 70.0,
      "currency": "USD",
      "legs": [
        {
          "departure_airport": {"code": "TPA", "name": "..."},
          "arrival_airport":   {"code": "RDU", "name": "..."},
          "departure_time": "2026-05-15T12:29:00",
          "arrival_time":   "2026-05-15T14:27:00",
          "duration": 118,
          "airline": {"code": "F9", "name": "Frontier Airlines"},
          "flight_number": "2730"
        }
      ]
    }
  ]
}
```

`fli dates` returns `dates: [{departure_date, return_date, price, currency}, ...]`.

Parsing recipe (keep it this short unless the user asks for more):

```bash
fli flights JFK LAX 2026-06-15 --format json | python3 -c '
import json, sys
d = json.load(sys.stdin)
for f in d["flights"][:10]:
    legs = f["legs"]
    route = "-".join([legs[0]["departure_airport"]["code"]] + [l["arrival_airport"]["code"] for l in legs])
    airlines = "/".join(sorted({l["airline"]["code"] for l in legs}))
    h, m = divmod(f["duration"], 60)
    dep = legs[0]["departure_time"][11:16]
    arr = legs[-1]["arrival_time"][11:16]
    print(f"${f[\"price\"]:>6.0f}  {airlines:6}  {f[\"stops\"]}stop  {h}h{m:02d}m  {dep}->{arr}  {route}")
'
```

## Common recipes

Cheapest nonstop on a date:
```bash
fli flights SFO JFK 2026-07-04 --stops NON_STOP --sort CHEAPEST --format json
```

Frontier-only, exclude basic economy, one checked bag priced in:
```bash
fli flights TPA PHL 2026-05-15 -a F9 --exclude-basic --bags 1 --format json
```

Business class, morning departures, sorted by duration:
```bash
fli flights SFO NRT 2026-09-10 -c BUSINESS -t 6-12 -o DURATION --format json
```

Cheapest weekday to fly in a month (nonstop):
```bash
fli dates JFK LAX --from 2026-06-01 --to 2026-06-30 --stops NON_STOP --sort --format json
```

Round-trip, 3-day weekend, Fri out / Sun back, over a full quarter:
```bash
fli dates SEA DEN --round -d 3 --friday --from 2026-07-01 --to 2026-09-30 --sort --format json
```

Layover only through specific hubs:
```bash
fli flights BOS HNL 2026-08-20 -l LAX -l SFO --format json
```

## Parallel scans

When the user asks "cheapest from any NYC airport to any LA airport in July" or similar (origin x destination x date fan-out), run the calls in parallel. Use multiple Bash tool calls in a single message, write each JSON to a temp file, then aggregate.

```bash
OUT=$(mktemp -d)
for O in JFK LGA EWR; do
  for D in LAX BUR SNA; do
    fli dates "$O" "$D" --from 2026-07-01 --to 2026-07-31 --stops NON_STOP \
      --format json > "$OUT/$O-$D.json" &
  done
done
wait

OUT="$OUT" python3 -c '
import json, glob, os
rows = []
for p in glob.glob(os.environ["OUT"] + "/*.json"):
    o, d = os.path.basename(p)[:-5].split("-")
    try:
        data = json.load(open(p))
    except Exception:
        continue
    for entry in data.get("dates", []):
        rows.append((entry["price"], o, d, entry["departure_date"]))
rows.sort()
for r in rows[:15]:
    print(f"${r[0]:>6.0f}  {r[1]}->{r[2]}  {r[3]}")
'
```

Keep the fan-out reasonable (under ~20 concurrent calls) — Google Flights will rate limit. The CLI retries internally, but a wide scan may still have individual failures; check `success` per file.

## Gotchas

- **Southwest (WN) on Google Flights**: Southwest does not fully publish fares to Google Flights. The CLI can return WN itineraries where the schedule is accurate but the price is unreliable — sometimes $0, sometimes stale. If a result has price 0 or a suspiciously low WN fare, surface it as "Southwest schedule only — price not published to Google; check southwest.com" rather than as a real fare. Non-WN $0 results are almost always errors; skip them.
- **No-result days**: `fli dates` silently omits dates with no fares. If the returned `count` is lower than the day range, the missing dates had no published fares (often far-future dates or tiny airports).
- **Airline codes are IATA, 2 char**: F9 = Frontier, NK = Spirit, B6 = JetBlue, WN = Southwest, UA = United, AA = American, DL = Delta, AS = Alaska, HA = Hawaiian, BA = British Airways, LH = Lufthansa, AF = Air France, KL = KLM, VS = Virgin Atlantic. If unsure, search once without the filter and read the codes off the results.
- **Currency**: `price` is a float in the currency returned by Google (usually USD). `--currency EUR` sets a fallback when Google does not return one — it does **not** convert.
- **Stops syntax**: `NON_STOP` / `ONE_STOP` / `TWO_PLUS_STOPS` (with underscores) or the shortcuts `0` / `1` / `2+`. `NONSTOP` without the underscore is rejected.
- **Departure window** is `HH-HH` with 24h hours only, no minutes (`6-20` not `06:00-20:00`).
- **Date format** is always `YYYY-MM-DD`. Past dates or malformed dates error out.
- **`--all` vs `--no-all`**: default is `--all` (every result, often 100+). Use `--no-all` when the user only wants a curated top-~30.
- **Round trips**: for `fli flights`, pass `--return`. For `fli dates`, pass `--round` and `--duration`.

## More reference material

If the user needs the full flag list, every sort option explained, or an exhaustive airline/airport hint table, read `references/cli-reference.md`.
