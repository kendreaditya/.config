#!/usr/bin/env bash
# Interactive one-time setup for the agent-upload skill.
# Run this yourself — it needs a browser login and a Cloudflare dashboard step.
set -euo pipefail

BUCKET="${1:-agent-files}"

echo "==> agent-upload setup"
echo

if ! wrangler whoami 2>/dev/null | grep -qi "account"; then
  echo "1. Authenticating wrangler (opens a browser)..."
  wrangler login
else
  echo "1. wrangler already authenticated."
fi

echo
echo "2. Creating bucket '$BUCKET' (ignore error if it exists)..."
wrangler r2 bucket create "$BUCKET" 2>&1 | tail -2 || true

cat <<EOF

3. MANUAL STEP — enable public access:

   Open:  https://dash.cloudflare.com/  ->  R2  ->  $BUCKET  ->  Settings
   Under "Public Development URL", click Enable.
   Copy the URL it gives you (looks like https://pub-<hash>.r2.dev)

4. Then add these two lines to ~/.config/.env :

   export AGENT_UPLOAD_BUCKET=$BUCKET
   export AGENT_UPLOAD_BASE_URL=https://pub-XXXXXXXX.r2.dev

   ...and reload:  source ~/.config/.env

5. Verify:

   echo hello > /tmp/t.txt
   ~/.config/agents/skills/agent-upload/upload.sh /tmp/t.txt

EOF
