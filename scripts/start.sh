#!/usr/bin/env bash
# One-click startup: creates the venv on first run, installs deps, launches Kukku.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=${PY:-python3.12}
command -v "$PY" >/dev/null || PY=python3

if [ ! -d .venv ]; then
  echo "▸ Creating virtualenv with $PY …"
  "$PY" -m venv .venv
  ./.venv/bin/pip install --upgrade pip -q
  echo "▸ Installing dependencies (first run takes a few minutes) …"
  ./.venv/bin/pip install -r requirements.txt
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "✋ Created .env — fill in TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS and ANTHROPIC_API_KEY, then rerun."
  exit 1
fi

exec ./.venv/bin/python -m app.main
