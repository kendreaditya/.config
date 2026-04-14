#!/bin/bash
# Fetch AstroBin's Image of the Day and set it as the macOS wallpaper.
# Picks the IOTD from the last ~10 days whose aspect ratio is closest to the
# primary display, to minimize letterboxing.

set -euo pipefail

FEED="https://www.astrobin.com/iotd/rss/iotd"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DEST_DIR="$HOME/Pictures/AstroBinIOTD"
LOG="$DEST_DIR/astrobin-wallpaper.log"

mkdir -p "$DEST_DIR"
exec >> "$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="

screen_ratio=$(
  system_profiler SPDisplaysDataType 2>/dev/null \
    | awk '/Resolution:/ {print $2, $4; exit}' \
    | awk '{ if ($2>0) printf "%.6f", $1/$2; else print "1.777778" }'
)
echo "display ratio: $screen_ratio"

feed_file=$(mktemp -t astrobin-feed)
trap 'rm -f "$feed_file"' EXIT
curl -sLA "$UA" "$FEED" -o "$feed_file"

picked=$(/usr/bin/python3 - "$screen_ratio" "$feed_file" <<'PY'
import sys, re, urllib.request, xml.etree.ElementTree as ET
target = float(sys.argv[1])
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
root = ET.parse(sys.argv[2]).getroot()
best = None
for item in root.findall(".//item"):
    enc = item.find("enclosure")
    if enc is None:
        continue
    url = enc.attrib.get("url", "")
    m = re.search(r"_(\d+)x(\d+)_", url)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if h == 0:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=10) as r:
                    head = r.read(65536)
                import struct
                if head[:3] == b"\xff\xd8\xff":
                    i = 2
                    while i < len(head):
                        while head[i] == 0xff: i += 1
                        marker = head[i]; i += 1
                        if 0xc0 <= marker <= 0xcf and marker not in (0xc4, 0xc8, 0xcc):
                            h = struct.unpack(">H", head[i+3:i+5])[0]
                            w = struct.unpack(">H", head[i+5:i+7])[0]
                            break
                        seg = struct.unpack(">H", head[i:i+2])[0]
                        i += seg
            except Exception:
                continue
    else:
        continue
    if not h:
        continue
    ratio = w / h
    score = abs(ratio - target)
    title = (item.findtext("title") or "").strip()
    if best is None or score < best[0]:
        best = (score, url, title, w, h)
if best:
    print(f"{best[1]}\t{best[2]}\t{best[3]}x{best[4]}")
PY
)

if [ -z "$picked" ]; then
  echo "failed to parse feed"
  exit 1
fi

url=$(printf '%s' "$picked" | cut -f1)
title=$(printf '%s' "$picked" | cut -f2)
dims=$(printf '%s' "$picked" | cut -f3)
echo "picked: $title ($dims) -> $url"

fname=$(basename "${url%%\?*}")
outfile="$DEST_DIR/$(date +%Y-%m-%d)_$fname"

if [ ! -s "$outfile" ]; then
  curl -sLA "$UA" -o "$outfile" "$url"
fi

osascript -e "tell application \"System Events\" to tell every desktop to set picture to \"$outfile\""
echo "wallpaper set: $outfile"
