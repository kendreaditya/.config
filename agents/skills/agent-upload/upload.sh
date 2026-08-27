#!/usr/bin/env bash
# Upload a local file to R2 and print its public URL.
# Usage: upload.sh <file> [remote-name]
set -euo pipefail

BUCKET="${AGENT_UPLOAD_BUCKET:-}"
BASE_URL="${AGENT_UPLOAD_BASE_URL:-}"

die() { printf 'agent-upload: %s\n' "$1" >&2; exit 1; }

[ $# -ge 1 ] || die "usage: upload.sh <file> [remote-name]"

SRC="$1"
[ -f "$SRC" ] || die "no such file: $SRC"

if [ -z "$BUCKET" ] || [ -z "$BASE_URL" ]; then
  die "AGENT_UPLOAD_BUCKET and AGENT_UPLOAD_BASE_URL must be set. Tell the user to run setup (see SKILL.md), do not guess a bucket."
fi

command -v wrangler >/dev/null || die "wrangler not installed (brew install cloudflare-wrangler2)"

# Slugify the base name and add a short random suffix so names need not be unique.
RAW_NAME="${2:-$(basename "$SRC")}"
STEM="${RAW_NAME%.*}"
EXT="${RAW_NAME##*.}"
[ "$EXT" = "$RAW_NAME" ] && EXT=""

SLUG=$(printf '%s' "$STEM" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' \
  | cut -c1-60)
[ -n "$SLUG" ] || SLUG="file"

SUFFIX=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n' | cut -c1-6)

KEY="$SLUG-$SUFFIX"
[ -n "$EXT" ] && KEY="$KEY.$EXT"

wrangler r2 object put "$BUCKET/$KEY" --file="$SRC" --remote >/dev/null 2>&1 \
  || die "upload failed. Run: wrangler r2 object put $BUCKET/$KEY --file=$SRC --remote"

printf '%s/%s\n' "${BASE_URL%/}" "$KEY"
