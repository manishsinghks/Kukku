#!/usr/bin/env bash
# Run the Kukku OS web dashboard (Next.js) in dev mode on http://localhost:3000
# The Python backend (launchd service) must be running for the app to work.
set -euo pipefail
cd "$(dirname "$0")/../web"

# use nvm's node if the shell PATH doesn't have a recent one
if ! command -v npm >/dev/null 2>&1; then
  export PATH="$HOME/.nvm/versions/node/v20.16.0/bin:$PATH"
fi

if [ ! -d node_modules ]; then
  echo "▸ Installing web dependencies (first run)…"
  npm install
fi

echo "▸ Starting Kukku OS at http://localhost:3000"
echo "  (Backend must be running: launchctl list | grep jarvis)"
exec npm run dev
