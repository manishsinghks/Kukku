# 🤖 Kukku — Personal AI Assistant

> A production-grade personal AI that runs 24/7 on your Mac. Talk to it on
> **Telegram** or a premium **web dashboard** — both share one brain, one memory,
> and one database.

<p>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12+-blue.svg">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-14-black.svg">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green.svg">
  <img alt="Tests" src="https://img.shields.io/badge/tests-140%20passing-brightgreen.svg">
</p>

Kukku finds files on your laptop (by name, content, or *meaning*), sends them to
you, reads your screenshots with OCR, transcribes voice notes, runs allowlisted
local commands, searches the web, sets reminders, and remembers things — in
English, Hindi, or Hinglish.

```
You:   find the screenshot where docker failed
Kukku: 🔍 Found it — Screenshot 2026-06-12 at 14.03.11.png
       (OCR matched: "Cannot connect to the Docker daemon")
       📎 [file attached]
```

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Environment variables](#environment-variables)
- [Docker](#docker)
- [Usage](#usage)
  - [Telegram](#telegram)
  - [Dashboard](#dashboard)
- [Always-online mode](#always-online-mode-optional-free)
- [Development](#development)
- [Roadmap](#roadmap)
- [FAQ](#faq)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## Overview

Most assistants can't see your files or run your commands. Kukku can, because it
runs **on your machine** and is reachable **through Telegram** (which you already
have on your phone) and a local **web dashboard**. It's private by design: your
data stays local, and it works entirely on free LLM tiers (Gemini, Groq, or local
Ollama) if you want zero cost.

The key idea: whether a message comes from Telegram or the dashboard, it runs
through the **same agent**, writes to the **same SQLite database**, and is
published to the **same realtime event bus** — so both clients stay in sync.

## Features

| | |
|---|---|
| 💬 **AI chat** | Tool-use agent with streaming replies, typing indicator, Markdown. Works with Claude (paid), **Gemini free tier**, **Groq free tier**, OpenRouter, or fully-local **Ollama** — all with full tool support. |
| 🔍 **File search** | Desktop, Documents, Downloads, Pictures… — by filename (fuzzy), content, and **semantic similarity** (ChromaDB + sentence-transformers), merged and ranked with recency boost. |
| 📄 **Formats** | PDF, Word, Excel, PowerPoint, TXT, Markdown, code (py/js/ts/…), JSON, images. |
| 🖼 **OCR** | Screenshots and images are text-indexed via Tesseract — "find the screenshot where Docker failed" works. |
| 🎙 **Voice** | Send a voice note; it's transcribed locally with Whisper (faster-whisper). English + Hindi auto-detected. |
| 🇮🇳 **Hindi / Hinglish** | Ask in Hindi (देवनागरी), Hinglish (Romanized), or English — replies mirror your language and script. |
| 📎 **File delivery** | Matching files are sent straight to your Telegram chat. |
| 💻 **Local commands** | Open apps/folders, lock screen, sleep, shutdown, restart — allowlisted; destructive ones require confirmation. |
| 🌐 **Web search** | Gemini Google-Search grounding (real, current results); DuckDuckGo fallback. |
| ⏰ **Reminders** | "remind me at 5pm to call mom", "har roz 9 baje standup" — one-time + daily, pushed to you. **Zero LLM cost.** |
| ⚠️ **Proactive alerts** | Warns about low battery / near-full disk before it's a problem. **Zero LLM cost.** |
| 🌦 **Weather** | "delhi ka weather" — free via Open-Meteo, no key. |
| 💾 **Auto-backup** | Daily consistent backup of the memory/history DB (keeps last 7). |
| 🧠 **Memory** | Persistent notes, aliases ("my resume" → path), full conversation history in SQLite. |
| 🔀 **Multi-provider** | Gemini → Groq → OpenRouter failover; auto-retry, cooldowns, health checks. |
| 🔒 **Security** | Only your Telegram user ID is accepted; everything else is rejected and logged. Dashboard is Argon2 + JWT. |
| 📊 **Dashboard** | Glassmorphism dark UI — AI chat, indexed files, searches, request logs, memory, CPU/RAM/disk, live sync. |
| 👀 **Live indexing** | Watchdog re-indexes files the moment they change; periodic full rescans. |

## Architecture

Two clients, one backend, one database — no duplicated logic.

```
   📱 Telegram              🖥️  Web Dashboard (Next.js @ :3000)
        │                            │
        │ webhook                    │ login (JWT) · POST /api/chat (SSE)
        ▼                            ▼
 ☁️  Cloudflare Worker + Durable Object (always-on relay, optional)
        │ long-poll (outbound from Mac)
        ▼
 🐍  Python backend @ 127.0.0.1:8788  ── one source of truth ──
        ├── FastAPI + Auth (Argon2 + JWT)
        ├── Agent (shared brain)  ── EventBus (realtime sync) ─▶ both clients
        ├── LLM failover:  Gemini → Groq → OpenRouter → Ollama
        ├── Scheduler (reminders/alerts/backup) · Indexer (watchdog)
        └── Data:  SQLite (history/memory)  +  ChromaDB (embeddings)
```

Full details, request traces, and design decisions are in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/WEB_DASHBOARD.md](docs/WEB_DASHBOARD.md).

## Screenshots

> _Placeholder — add your own images under `docs/images/` and update the links._

| Telegram | Dashboard — AI Chat | Dashboard — Monitor |
|---|---|---|
| _`docs/images/telegram.png`_ | _`docs/images/dashboard-chat.png`_ | _`docs/images/dashboard-monitor.png`_ |

## Installation

**Requirements:** macOS, Python 3.12+, and (for the dashboard) Node 20+.
Optional: Tesseract (OCR), Ollama (local LLM).

```bash
git clone <your-fork-url> Kukku
cd Kukku
./scripts/start.sh          # creates venv + installs deps on first run
```

1. Copy the env template and fill it in: `cp .env.example .env`
   - Set `TELEGRAM_BOT_TOKEN` (from [@BotFather](https://t.me/BotFather)) and
     **one** LLM key. **100% free:** a Gemini key from
     https://aistudio.google.com/apikey (no credit card) → `GEMINI_API_KEY`.
2. Message your bot once — it replies with your numeric Telegram ID.
3. Put that ID in `ALLOWED_USER_IDS`, restart. Done.

Optional extras:

```bash
brew install tesseract      # OCR for screenshots/images
```

Run 24/7 (auto-start at login, auto-restart on crash) — see
[docs/INSTALL.md](docs/INSTALL.md) for the launchd setup.

Full guide: **[docs/INSTALL.md](docs/INSTALL.md)**.

## Environment variables

Configure everything via `.env` (see [`.env.example`](.env.example) for the full,
commented template). You only need a bot token and **one** LLM key to start.

| Variable | Required | Description |
|---|:---:|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather. |
| `ALLOWED_USER_IDS` | ✅ | Comma-separated numeric Telegram IDs allowed to use the bot. |
| `GEMINI_API_KEY` | ⚠️ one LLM | Free Gemini key (recommended). |
| `GROQ_API_KEY` | ⚠️ one LLM | Free Groq key (fast Llama 70B). |
| `OPENROUTER_API_KEY` | ⚠️ one LLM | Free OpenRouter fallback. |
| `ANTHROPIC_API_KEY` | ⚠️ one LLM | Paid Claude (best quality). |
| `OLLAMA_MODEL` / `OLLAMA_URL` | ⚠️ one LLM | Fully local/offline LLM. |
| `LLM_PRIORITY` | | Failover order, e.g. `gemini,groq,openrouter`. |
| `INDEX_DIRS` | | Comma-separated folders to index (relative to `$HOME` or absolute). |
| `ENABLE_OCR` / `ENABLE_VOICE` | | Toggle OCR / voice transcription. |
| `WHISPER_MODEL` | | faster-whisper size (e.g. `base`, `small`). |
| `DASHBOARD_HOST` / `DASHBOARD_PORT` | | Bind address (default `127.0.0.1:8788`). |
| `DATA_DIR` | | Where the DB, embeddings, logs, and backups live. |
| `WORKER_URL` / `BRIDGE_SECRET` / `WEBHOOK_SECRET` | | Optional cloud relay (set by `scripts/setup_cloud.sh`). |

**Secrets never belong in git.** `.env`, `data/`, and credentials are
git-ignored — keep it that way.

## Docker

```bash
docker compose up -d
```

The dashboard is published on `127.0.0.1:8788`, and the folders in
`docker-compose.yml` are mounted read-only. Note: on macOS a container **cannot**
open apps or lock the screen and only sees the folders you mount — native
(launchd) is the recommended way to run Kukku on a Mac.

## Usage

### Telegram

Just talk to the bot. Try:
- `find my resume pdf` → it searches and offers to send the file
- `mera resume bhejo` → same, in Hinglish
- `remind me at 6pm to call the dentist`
- send a **voice note** or a **screenshot** and ask about it

### Dashboard

```bash
./.venv/bin/python scripts/set_password.py   # one-time: create your login
./scripts/web.sh                             # → http://localhost:3000
```

Sign in and use AI Chat, Universal Search, Memory, File Explorer, OCR Search,
Automation, Developer, System Monitor, Notifications, and Settings. Messages sent
on Telegram appear in the dashboard live, and vice-versa. See
[docs/WEB_DASHBOARD.md](docs/WEB_DASHBOARD.md).

## Always-online mode (optional, free)

By default Kukku lives and dies with your Mac. Run `./scripts/setup_cloud.sh` to
deploy a free Cloudflare Worker relay (no credit card):

- **Mac on** → messages flow through a free tunnel to full Kukku (files, commands, voice).
- **Mac off/asleep** → the Worker answers general questions with Gemini and tells
  you the file features are offline.

Revert anytime with `./scripts/disable_cloud.sh`.

## Development

```bash
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/pytest                 # unit + integration tests (all must pass)
./.venv/bin/ruff check app tests   # lint
cd web && npm install && npm run build   # dashboard build
```

See [docs/EXTENDING.md](docs/EXTENDING.md) to add a new tool or module — a change
to the shared agent benefits both Telegram and the dashboard automatically.

## Roadmap

Planned: ⌘K command palette, image vision in chat (Gemini multimodal), PWA
(installable dashboard), settings write-through, and Calendar/Gmail modules.
Full list in [docs/ROADMAP.md](docs/ROADMAP.md).

## FAQ

Common questions (cost, privacy, "does it work when my Mac is asleep?", resetting
the index) are answered in [docs/FAQ.md](docs/FAQ.md).

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Please run the
tests and linter before opening a PR.

## Security

Only your Telegram ID is accepted; the dashboard binds to `127.0.0.1` and uses
Argon2 + JWT. Threat model, hardening checklist, and how to **report a
vulnerability** are in [docs/SECURITY.md](docs/SECURITY.md).

## License

[MIT](LICENSE).

## More docs

[Architecture](docs/ARCHITECTURE.md) ·
[Web Dashboard](docs/WEB_DASHBOARD.md) ·
[Features](docs/FEATURES.md) ·
[API reference](docs/API_REFERENCE.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md) ·
[Recovery](docs/RECOVERY.md) ·
[Changelog](CHANGELOG.md)
