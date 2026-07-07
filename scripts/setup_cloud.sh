#!/usr/bin/env bash
# One-command cloud relay setup: deploys the Cloudflare Worker, wires secrets,
# points the Telegram webhook at it, and restarts Kukku in bridge mode.
#
# Prereqs: a free Cloudflare account (https://dash.cloudflare.com/sign-up —
# email only, no card). The script opens a browser for login on first run.
set -euo pipefail
trap 'echo "✗ setup failed at line $LINENO — paste this output to Claude to debug"' ERR
cd "$(dirname "$0")/../cloud"

W="npx -y wrangler@3"
CF_API="https://api.cloudflare.com/client/v4"

command -v npx >/dev/null || { echo "✗ Node.js/npx required (nvm install 20)"; exit 1; }
# No tunnel needed — the Mac long-polls the Worker (outbound only).

ENV_FILE="../.env"
# tolerant of missing keys: a var with no line in .env yields empty, not a crash
get_env() { { grep "^$1=" "$ENV_FILE" 2>/dev/null || true; } | head -1 | cut -d= -f2-; }

BOT_TOKEN=$(get_env TELEGRAM_BOT_TOKEN)
GEMINI_KEY=$(get_env GEMINI_API_KEY)
ALLOWED=$(get_env ALLOWED_USER_IDS)
[ -n "$BOT_TOKEN" ] || { echo "✗ TELEGRAM_BOT_TOKEN missing in .env"; exit 1; }
[ -n "$GEMINI_KEY" ] || { echo "✗ GEMINI_API_KEY missing in .env"; exit 1; }

echo "▸ Checking Cloudflare login…"
if ! $W whoami >/dev/null 2>&1; then
  echo "  (browser opens — click Allow)"
  $W login
fi

ACCOUNT_ID=$($W whoami 2>/dev/null | grep -oE '[a-f0-9]{32}' | head -1)
[ -n "$ACCOUNT_ID" ] || { echo "✗ Could not determine Cloudflare account id"; exit 1; }

# wrangler's own OAuth token, used only against the Cloudflare API on your behalf
CFG="$HOME/Library/Preferences/.wrangler/config/default.toml"
[ -f "$CFG" ] || CFG="$HOME/.wrangler/config/default.toml"
TOKEN=$(grep -m1 'oauth_token' "$CFG" | cut -d'"' -f2)
[ -n "$TOKEN" ] || { echo "✗ Could not read wrangler oauth token from $CFG"; exit 1; }

cf() { curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$@"; }

echo "▸ Ensuring workers.dev subdomain…"
SUB=$(cf "$CF_API/accounts/$ACCOUNT_ID/workers/subdomain" \
  | python3 -c 'import json,sys; print((json.load(sys.stdin).get("result") or {}).get("subdomain") or "")')
if [ -z "$SUB" ]; then
  for cand in "manish-jarvis" "manish-jarvis-$((RANDOM % 9000 + 1000))"; do
    OK=$(cf -X PUT "$CF_API/accounts/$ACCOUNT_ID/workers/subdomain" -d "{\"subdomain\":\"$cand\"}" \
      | python3 -c 'import json,sys; print("yes" if json.load(sys.stdin).get("success") else "no")')
    if [ "$OK" = "yes" ]; then SUB="$cand"; break; fi
  done
fi
[ -n "$SUB" ] || { echo "✗ Could not register a workers.dev subdomain. Do it once at:"; \
  echo "  https://dash.cloudflare.com/$ACCOUNT_ID/workers/onboarding  — then rerun this script."; exit 1; }
echo "  subdomain: $SUB.workers.dev ✓"

# KV namespace for the Mac's tunnel URL
if grep -q "KV_NAMESPACE_ID_PLACEHOLDER" wrangler.toml; then
  echo "▸ Creating KV namespace…"
  KV_ID=$($W kv namespace create JARVIS_KV 2>/dev/null | grep -oE '[a-f0-9]{32}' | head -1)
  [ -n "$KV_ID" ] || { echo "✗ Could not create/parse KV namespace id"; exit 1; }
  sed -i '' "s/KV_NAMESPACE_ID_PLACEHOLDER/$KV_ID/" wrangler.toml
fi

echo "▸ Deploying worker…"
$W deploy
WORKER_URL="https://jarvis-relay.$SUB.workers.dev"
echo "  $WORKER_URL"

BRIDGE_SECRET=$(get_env BRIDGE_SECRET)
[ -n "$BRIDGE_SECRET" ] || BRIDGE_SECRET=$(openssl rand -hex 24)
WEBHOOK_SECRET=$(get_env WEBHOOK_SECRET)
[ -n "$WEBHOOK_SECRET" ] || WEBHOOK_SECRET=$(openssl rand -hex 24)

echo "▸ Setting worker secrets…"
printf '%s' "$BOT_TOKEN"      | $W secret put BOT_TOKEN
printf '%s' "$GEMINI_KEY"     | $W secret put GEMINI_API_KEY
printf '%s' "$BRIDGE_SECRET"  | $W secret put BRIDGE_SECRET
printf '%s' "$WEBHOOK_SECRET" | $W secret put WEBHOOK_SECRET
printf '%s' "$ALLOWED"        | $W secret put ALLOWED_USER_IDS

echo "▸ Updating .env…"
for kv in "WORKER_URL=$WORKER_URL" "BRIDGE_SECRET=$BRIDGE_SECRET" "WEBHOOK_SECRET=$WEBHOOK_SECRET"; do
  key=${kv%%=*}
  if grep -q "^$key=" "$ENV_FILE"; then
    sed -i '' "s|^$key=.*|$kv|" "$ENV_FILE"
  else
    printf '\n%s\n' "$kv" >> "$ENV_FILE"
  fi
done

echo "▸ Waiting for the worker to come alive…"
for _ in $(seq 1 20); do
  if curl -s --max-time 5 "$WORKER_URL/health" | grep -q '"ok":true'; then ALIVE=1; break; fi
  sleep 3
done
[ "${ALIVE:-}" = "1" ] || echo "  (worker not responding yet — new subdomains can take a minute; continuing)"

echo "▸ Pointing Telegram webhook at the worker…"
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${WORKER_URL}/webhook" -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message","edited_message"]' | grep -q '"ok":true' \
  && echo "  webhook set ✓" || { echo "✗ setWebhook failed"; exit 1; }

echo "▸ Restarting Kukku in bridge mode…"
launchctl kickstart -k "gui/$(id -u)/com.manish.jarvis" 2>/dev/null || echo "  (start manually: ./scripts/start.sh)"

echo
echo "✅ Cloud relay live at $WORKER_URL"
echo "   Mac ON  → full Kukku (files, commands, voice)"
echo "   Mac OFF → general questions answered from the cloud"
echo "   To undo: ./scripts/disable_cloud.sh"
