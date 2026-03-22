---
name: google-sheets
description: Read, write, format, and manage Google Sheets using the gog CLI. Use when the user asks to work with a Google Sheet or spreadsheet — reading/writing cell data, appending rows, formatting cells, managing tabs, creating sheets, finding and replacing text, exporting files, or any spreadsheet operation. Requires gog CLI with Sheets auth. Triggers on: "google sheets", "spreadsheet", "my sheet", "read cells", "update cells", "append rows", "clear range", "format cells", "add tab", "create spreadsheet", "export sheet", "find replace", "gog sheets".
---

# Google Sheets

All operations via `gog sheets`. Requires `gog` with Sheets auth.

## Auth setup (once)

```bash
gog auth credentials /path/to/client_secret.json
gog auth add you@gmail.com --services sheets
export GOG_ACCOUNT=you@gmail.com   # avoid repeating --account
```

## Getting the sheet ID

Extract from URL: `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

Find a sheet by name:
```bash
gog drive search "budget 2024" --json   # returns id, name, webViewLink
```

## Core data operations

### Read
```bash
gog sheets get <id> "Sheet1!A1:D10" --json        # structured JSON
gog sheets get <id> "Sheet1!A1:D10" --plain        # TSV, stable for scripting
gog sheets get <id> "Sheet1!A1:D10" --render FORMULA   # get raw formulas
gog sheets get <id> "Sheet1"                       # entire sheet
```

### Write
```bash
gog sheets update <id> "Sheet1!A1:B2" \
  --values-json '[["Name","Score"],["Alice","95"]]' \
  --input USER_ENTERED    # parses formulas/numbers (default); use RAW to store literally
```

### Append rows
```bash
gog sheets append <id> "Sheet1!A:C" \
  --values-json '[["2024-01-15","Alice","95"]]' \
  --insert INSERT_ROWS    # inserts new rows (vs OVERWRITE)
```

### Clear
```bash
gog sheets clear <id> "Sheet1!A2:Z"   # clears values, keeps formatting
```

## Tab management

```bash
gog sheets metadata <id> --json          # list tabs, dimensions, sheet IDs
gog sheets add-tab <id> "Summary"
gog sheets rename-tab <id> "OldName" "NewName"
gog sheets delete-tab <id> "TabName" --force   # --force skips confirmation
```

## Create & copy

```bash
gog sheets create "My New Sheet" --json            # returns spreadsheetId
gog sheets create "Sheet" --sheets "Tab1,Tab2"     # with named tabs
gog sheets copy <id> "Copy of Sheet" --json        # duplicate entire sheet
```

## Formatting

```bash
# Bold + background color on header row (colors are 0.0–1.0 floats, NOT 0–255)
gog sheets format <id> "Sheet1!A1:D1" \
  --format-json '{"textFormat":{"bold":true},"backgroundColor":{"red":0.2,"green":0.6,"blue":0.9}}' \
  --format-fields "userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor"

# Number format (e.g. currency)
gog sheets number-format <id> "Sheet1!B2:B100" --pattern '"$"#,##0.00'

# Merge / unmerge cells
gog sheets merge <id> "Sheet1!A1:C1"
gog sheets unmerge <id> "Sheet1!A1:C1"

# Freeze rows/columns
gog sheets freeze <id> --rows 1 --columns 1

# Resize columns (auto-fit)
gog sheets resize-columns <id> "Sheet1!A:D" --auto
```

## Utilities

```bash
# Find and replace across entire sheet
gog sheets find-replace <id> "old text" "new text"
gog sheets find-replace <id> "foo" "bar" --match-case --sheet "Sheet1"
gog sheets find-replace <id> "\bv1\b" "v2" --regex

# Insert empty rows or columns
gog sheets insert <id> "Sheet1" ROWS 2      # insert rows at index 2
gog sheets insert <id> "Sheet1" COLUMNS 0   # insert column at index 0

# Export to file
gog sheets export <id> --format xlsx --out ./export.xlsx
gog sheets export <id> --format csv --out ./data.csv
gog sheets export <id> --format pdf --out ./report.pdf

# Cell notes
gog sheets notes <id> "Sheet1!A1:B5"                    # read notes
gog sheets update-note <id> "Sheet1!A1" --note "TODO"   # set note

# Named ranges
gog sheets named-ranges list <id>
```

## Range notation

| Pattern | Meaning |
|---------|---------|
| `Sheet1!A1:D10` | Specific range |
| `Sheet1!A:C` | Full columns A–C |
| `Sheet1!1:5` | Rows 1–5 |
| `Sheet1` | Entire sheet |
| `MyNamedRange` | Named range |

Tab names with spaces: `'My Tab'!A1:B10` — single quotes required (shell: escape or use `$'My Tab\!A1:B10'`).

## Pitfalls

- **Always run `metadata` first** if you don't know the tab name — tab names are case-sensitive and locale-dependent (`Sheet1` may be `Hoja 1` in Spanish accounts)
- **Bound your ranges** on large sheets (`A1:Z10000` not `A:Z`) — unbounded reads can be slow or time out
- **Rate limits**: ~60 reads/min and ~60 writes/min per account
- **`--values-json` must be a 2D array** even for a single row: `[["val1","val2"]]`
- **Format colors are 0.0–1.0 floats**, not 0–255 integers
- **`--no-input`** flag prevents interactive prompts — use in scripts/CI
