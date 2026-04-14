# fli CLI reference

Full flag list and semantics, pulled from `fli --help`, `fli flights --help`, and `fli dates --help`. Load this only when SKILL.md is not enough.

## `fli flights ORIGIN DEST DEPARTURE_DATE`

| Flag | Short | Values | Default | Notes |
|---|---|---|---|---|
| `--return` | `-r` | `YYYY-MM-DD` | none | Presence makes it a round trip. |
| `--time` | `-t` | `HH-HH` (24h) | any | Departure window. Whole hours only. |
| `--airlines` | `-a` | IATA codes, space-separated | any | e.g. `-a BA KL`. Accepts one or more. |
| `--class` | `-c` | `ECONOMY`, `PREMIUM_ECONOMY`, `BUSINESS`, `FIRST` | `ECONOMY` | |
| `--stops` | `-s` | `ANY`, `NON_STOP`, `ONE_STOP`, `TWO_PLUS_STOPS` (or `0`, `1`, `2+`) | `ANY` | |
| `--sort` | `-o` | `TOP_FLIGHTS`, `BEST`, `CHEAPEST`, `DEPARTURE_TIME`, `ARRIVAL_TIME`, `DURATION`, `EMISSIONS` | `CHEAPEST` | |
| `--exclude-basic` | `-e` | flag | off | Drops basic-economy fares. |
| `--layover` | `-l` | IATA, repeatable | none | Restrict allowed connection airports. |
| `--emissions` | | `ALL`, `LESS` | `ALL` | `LESS` shows only lower-emission itineraries. |
| `--bags` | `-b` | `0`, `1`, `2` | `0` | Includes checked-bag fees in displayed price. |
| `--carry-on` | | flag | off | Includes carry-on fee in displayed price. |
| `--all` / `--no-all` | | flag | `--all` | `--no-all` trims to ~30 curated results. |
| `--format` | | `text`, `json` | `text` | Always use `json` for agent consumption. |
| `--currency` | | ISO code | `USD` | Fallback only; does not convert. |

## `fli dates ORIGIN DEST`

| Flag | Short | Values | Default | Notes |
|---|---|---|---|---|
| `--from` | | `YYYY-MM-DD` | tomorrow | Inclusive start. |
| `--to` | | `YYYY-MM-DD` | ~60 days out | Inclusive end. |
| `--duration` | `-d` | int (days) | `3` | Trip length; meaningful only with `--round`. |
| `--round` | `-R` | flag | off | Round-trip mode. |
| `--airlines` | `-a` | IATA codes | any | |
| `--stops` | `-s` | same as flights | `ANY` | |
| `--class` | `-c` | same as flights | `ECONOMY` | |
| `--time` | `-time` | `HH-HH` | any | |
| `--sort` | | flag (no arg) | off | Sorts output ascending by price. |
| `--monday` | `-mon` | flag | | Include this weekday. Repeatable across days. |
| `--tuesday` | `-tue` | flag | | |
| `--wednesday` | `-wed` | flag | | |
| `--thursday` | `-thu` | flag | | |
| `--friday` | `-fri` | flag | | |
| `--saturday` | `-sat` | flag | | |
| `--sunday` | `-sun` | flag | | |
| `--format` | | `text`, `json` | `text` | |
| `--currency` | | ISO code | `USD` | Fallback only. |

If no weekday flags are passed, all days are included.

## Sort options explained

- `CHEAPEST` — strict ascending price.
- `BEST` — Google's "Best" heuristic (price + duration + convenience).
- `TOP_FLIGHTS` — Google's "Top departing flights" ranking (similar to BEST).
- `DURATION` — shortest total trip time.
- `DEPARTURE_TIME` — earliest departure first.
- `ARRIVAL_TIME` — earliest arrival first.
- `EMISSIONS` — lowest CO2 first.

## JSON output shape

### `fli flights` top-level

```
{
  "success": bool,
  "data_source": "google_flights",
  "search_type": "flights",
  "trip_type": "ONE_WAY" | "ROUND_TRIP",
  "query": { ...echo of inputs... },
  "count": int,
  "flights": [ Flight, ... ]
}
```

### `Flight`

```
{
  "duration": int,          # total minutes across all legs incl. layovers
  "stops": int,
  "price": float,
  "currency": str,          # e.g. "USD"
  "legs": [ Leg, ... ]
}
```

### `Leg`

```
{
  "departure_airport": {"code": "JFK", "name": "..."},
  "arrival_airport":   {"code": "LAX", "name": "..."},
  "departure_time": "YYYY-MM-DDTHH:MM:SS",
  "arrival_time":   "YYYY-MM-DDTHH:MM:SS",
  "duration": int,          # minutes for this leg only
  "airline": {"code": "AA", "name": "American Airlines"},
  "flight_number": "100"
}
```

### `fli dates` top-level

```
{
  "success": bool,
  "search_type": "dates",
  "trip_type": "ONE_WAY" | "ROUND_TRIP",
  "query": { ... },
  "count": int,
  "dates": [
    {
      "departure_date": "YYYY-MM-DD",
      "return_date": "YYYY-MM-DD" | null,
      "price": float,
      "currency": str
    }
  ]
}
```

Dates with no published fares are silently omitted. `count` reflects returned entries, not requested days.

## Error behavior

- Invalid IATA code, malformed date, or past date returns a non-zero exit and prints an error to stderr. When scripting a fan-out, always check `success` in each JSON file (and handle missing files for hard failures).
- Google Flights can rate-limit. The CLI retries with backoff internally, but under heavy parallel load some calls may still fail. Back off and retry on failure rather than treating it as "no flights exist".

## Airline code quick hints (IATA, 2-char)

US: AA American, DL Delta, UA United, WN Southwest, AS Alaska, B6 JetBlue, F9 Frontier, NK Spirit, HA Hawaiian, SY Sun Country, G4 Allegiant.

Europe: BA British Airways, LH Lufthansa, AF Air France, KL KLM, IB Iberia, AZ ITA, LX Swiss, OS Austrian, SN Brussels, TP TAP, EI Aer Lingus, VS Virgin Atlantic, FR Ryanair, U2 easyJet.

Asia/ME: JL JAL, NH ANA, SQ Singapore, CX Cathay, KE Korean, OZ Asiana, CI China Airlines, BR EVA, TG Thai, EK Emirates, EY Etihad, QR Qatar, TK Turkish.

Americas: AC Air Canada, WS WestJet, AM Aeromexico, LA LATAM, AV Avianca, CM Copa, G3 GOL, AD Azul.

Oceania: QF Qantas, VA Virgin Australia, NZ Air New Zealand.

If unsure, run a search without `--airlines` first and read the codes off the returned results.

## City-to-airport hints (common ambiguous cases)

- New York: JFK, LGA, EWR
- Los Angeles: LAX, BUR, LGB, SNA, ONT
- Chicago: ORD, MDW
- Washington DC: DCA, IAD, BWI
- Houston: IAH, HOU
- Dallas-Fort Worth: DFW, DAL
- San Francisco Bay: SFO, OAK, SJC
- Miami area: MIA, FLL, PBI
- London: LHR, LGW, STN, LTN, LCY
- Paris: CDG, ORY, BVA
- Tokyo: HND, NRT
- Milan: MXP, LIN, BGY
- Moscow: SVO, DME, VKO
- Seoul: ICN, GMP
- Shanghai: PVG, SHA
- Toronto: YYZ, YTZ
- Montreal: YUL
- Sao Paulo: GRU, CGH, VCP
- Rome: FCO, CIA
- Stockholm: ARN, BMA, NYO
- Berlin: BER
- Istanbul: IST, SAW

When the user says a city with multiple airports, either confirm or fan out across all of them in parallel (see the SKILL.md "Parallel scans" section).
