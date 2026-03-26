#!/bin/bash
# gemini-smart.sh — discover available Gemini models and print recommended IDs
#
# Usage: gemini-smart.sh
#
# Requires GEMINI_API_KEY to query live models.
# Without it, prints hardcoded known-latest fallbacks.

FALLBACK_PRO="gemini-3.1-pro-preview"
FALLBACK_FLASH="gemini-3-flash-preview"
FALLBACK_LITE="gemini-3.1-flash-lite-preview"

if [[ -z "$GEMINI_API_KEY" ]]; then
  echo "No GEMINI_API_KEY set — showing hardcoded fallbacks:"
  echo ""
  echo "  flash (default): $FALLBACK_FLASH"
  echo "  pro:             $FALLBACK_PRO"
  echo "  lite:            $FALLBACK_LITE"
  echo ""
  echo "Set GEMINI_API_KEY to query live available models."
  exit 0
fi

MODELS_JSON=$(curl -sf \
  "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY&pageSize=200" \
  2>/dev/null)

if [[ -z "$MODELS_JSON" ]]; then
  echo "API query failed — showing hardcoded fallbacks:"
  echo ""
  echo "  flash (default): $FALLBACK_FLASH"
  echo "  pro:             $FALLBACK_PRO"
  echo "  lite:            $FALLBACK_LITE"
  exit 1
fi

python3 - "$FALLBACK_PRO" "$FALLBACK_FLASH" "$FALLBACK_LITE" <<'PYEOF'
import json, sys, re, os

fallback_pro, fallback_flash, fallback_lite = sys.argv[1], sys.argv[2], sys.argv[3]
data = json.loads(os.environ.get("MODELS_JSON", "{}"))

def pick_latest(models, keyword, exclude=""):
    filtered = [
        m["name"].replace("models/", "") for m in models
        if re.search(r"gemini-\d", m["name"])
        and keyword in m["name"]
        and (not exclude or exclude not in m["name"])
        and "image" not in m["name"]
        and "vision" not in m["name"]
    ]
    def sort_key(n):
        preview = 1 if "preview" in n else 0
        nums = [int(x) for x in re.findall(r"\d+", n)]
        return (preview, [-v for v in nums])
    filtered.sort(key=sort_key)
    return filtered

all_models = data.get("models", [])
pro_models   = pick_latest(all_models, "pro",   exclude="lite")
flash_models = pick_latest(all_models, "flash", exclude="lite")
lite_models  = pick_latest(all_models, "lite")

best_pro   = pro_models[0]   if pro_models   else fallback_pro
best_flash = flash_models[0] if flash_models else fallback_flash
best_lite  = lite_models[0]  if lite_models  else fallback_lite

print("=== Recommended models (use these with: gemini -m <model> -p ...) ===")
print()
print(f"  flash (default):  {best_flash}")
print(f"  pro:              {best_pro}")
print(f"  lite:             {best_lite}")
print()
print("=== All available Gemini models ===")
print()
for m in all_models:
    name = m["name"].replace("models/", "")
    if re.search(r"gemini-\d", name):
        tag = ""
        if name == best_flash: tag = "  ← latest flash"
        if name == best_pro:   tag = "  ← latest pro"
        if name == best_lite:  tag = "  ← latest lite"
        print(f"  {name}{tag}")
PYEOF
