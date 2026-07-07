# Kukku OS — Web Dashboard

A premium Next.js client for Kukku. It talks to the **same Python backend** the
Telegram bot uses (`http://127.0.0.1:8788`) — one source of truth, live-synced.

## First-time setup

1. **Create your login** (on your Mac — password never leaves it):
   ```bash
   cd ~/jarvis && ./.venv/bin/python scripts/set_password.py
   ```
2. **Backend must be running** (it is, via launchd): `launchctl list | grep jarvis`
3. **Start the web app**: `~/jarvis/scripts/web.sh`  (or: `cd web && npm run dev`)
4. Open **http://localhost:3000**, log in.

## What works today
- Login (JWT + refresh)
- AI Chat: streaming, markdown, code highlight, provider badge, live Telegram sync
- System Monitor: live CPU/RAM/disk + per-provider metrics
- Universal Search: files / OCR / memory / aliases
- Memory: list / add / delete / export
- Files, OCR, Automation, Developer, Settings, Notifications: module shells (wiring next)

## Stack
Next.js 14 (App Router), React, Tailwind, Framer Motion, lucide-react,
react-markdown + highlight.js. Node 20.
