#!/usr/bin/env bash
# Revert to plain polling mode: remove the webhook and blank the relay config.
set -euo pipefail
cd "$(dirname "$0")/.."

BOT_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d= -f2-)
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook" >/dev/null && echo "webhook removed ✓"
sed -i '' 's|^WORKER_URL=.*|WORKER_URL=|' .env
launchctl kickstart -k "gui/$(id -u)/com.manish.jarvis" 2>/dev/null || true
echo "✅ Back to polling mode (cloud relay dormant; re-enable with setup_cloud.sh)"
