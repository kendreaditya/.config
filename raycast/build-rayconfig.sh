#!/usr/bin/env bash
# Build a Raycast.rayconfig from settings.json.
#
# Output is a plain gzipped JSON in Raycast's internal schema.
# Raycast accepts this directly via "Import Settings & Data" — no
# encryption, no header, no password required (verified 2026-04-17).
#
# Format reverse-engineered from:
# https://gist.github.com/jeremy-code/50117d5b4f29e04fcbbb1f55e301b893
#
# Usage:
#   ./build-rayconfig.sh [-i settings.json] [-o Raycast.rayconfig]

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IN="$DIR/settings.json"
OUT="$DIR/Raycast.rayconfig"
JQ_FILTER="$DIR/build-rayconfig.jq"

while getopts "i:o:" opt; do
  case "$opt" in
    i) IN="$OPTARG" ;;
    o) OUT="$OPTARG" ;;
    *) echo "usage: $0 [-i in.json] [-o out.rayconfig]"; exit 2 ;;
  esac
done

[[ -f "$IN" ]] || { echo "ERROR: input not found: $IN"; exit 2; }
[[ -f "$JQ_FILTER" ]] || { echo "ERROR: jq filter not found: $JQ_FILTER"; exit 2; }

jq 'del(._note)' "$IN" | jq -f "$JQ_FILTER" | gzip -nc > "$OUT"

echo "Wrote: $OUT ($(wc -c <"$OUT") bytes)"
