<div align="center">

<img src="assets/brand/logo-mark.svg" width="112" height="112" alt="Kukku" />

# Kukku

### Local by design. Personal by default.

**A private, local-first personal AI that lives on your Mac — and answers on Telegram and a beautiful web dashboard.**
It finds your files by *meaning*, reads your screenshots, transcribes your voice, remembers what matters, and runs on free model tiers. Your data never leaves home.

<br/>

[![CI](https://github.com/manishsinghks/Kukku/actions/workflows/ci.yml/badge.svg)](https://github.com/manishsinghks/Kukku/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-6A5AF9.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-6A5AF9.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6.svg?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-0B0B0F.svg?style=flat-square&logo=nextdotjs)](https://nextjs.org)
[![Local-first](https://img.shields.io/badge/data-100%25%20local-FF9E64.svg?style=flat-square)](#-faq)

[**Quick Start**](#-quick-start) · [**Features**](#-why-kukku) · [**Architecture**](#-architecture) · [**Config**](#environment-variables) · [**Roadmap**](#-roadmap) · [**FAQ**](#-faq)

<!-- TODO: add a hero screenshot at docs/images/hero-chat.png and uncomment:
<br/><img src="docs/images/hero-chat.png" alt="Kukku dashboard — AI chat" width="820" />
-->

</div>

---

## ✨ Why Kukku

> Cloud assistants can't see your files and won't keep your data private.
> **Kukku runs on your own machine** — ask it in plain language, from your phone
> or a local dashboard, and it works *where your files already live*.

<table>
<tr>
<td width="33%" valign="top">

### 🔍 Finds anything
Semantic + keyword + OCR search across your Mac. *"the screenshot where Docker failed"* just works.

</td>
<td width="33%" valign="top">

### 🧠 Remembers you
A shared memory and conversation history across Telegram and the dashboard — your second brain.

</td>
<td width="33%" valign="top">

### 🔒 Stays private
Everything runs on `127.0.0.1`. Free model tiers, no cloud tax, fully self-hosted and open-source.

</td>
</tr>
<tr>
<td valign="top">

### 🎙 Speaks your language
Voice notes transcribed locally; replies in English, Hindi, or Hinglish — mirroring how you wrote.

</td>
<td valign="top">

### 📱 Answers anywhere
One brain, two front doors: a Telegram bot in your pocket and a premium Next.js dashboard.

</td>
<td valign="top">

### ⚡ Never gives up
Gemini → Groq → OpenRouter failover (or fully-local Ollama), with retries and cooldowns.

</td>
</tr>
</table>

---

## 🏗 Architecture

Two clients, one brain, one database — messages sync live between both.

```
   📱 Telegram                 🖥️  Web Dashboard (Next.js · localhost:3000)
        │                              │
        ▼                              ▼
 ☁️  Cloudflare relay (optional)   JWT auth · SSE chat
        │  long-poll (outbound)        │
        ▼                              ▼
 🐍  Python backend · 127.0.0.1:8788 — one source of truth
      Agent (shared brain) · EventBus (live sync) · Scheduler · Indexer
      LLM failover: Gemini → Groq → OpenRouter → Ollama
      Data: SQLite (history + memory) · ChromaDB (embeddings)
```

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/WEB_DASHBOARD.md`](docs/WEB_DASHBOARD.md)

---

## 📸 Screenshots

> _Screenshots live in `docs/images/`. Add your own (dark theme, 1440×900) and uncomment the grid below._

<!--
<div align="center">
<img src="docs/images/dashboard-chat.png" width="49%" alt="AI Chat" />
<img src="docs/images/dashboard-monitor.png" width="49%" alt="System Monitor" />
<img src="docs/images/dashboard-search.png" width="49%" alt="Universal Search" />
<img src="docs/images/mobile-drawer.png" width="49%" alt="Responsive on mobile" />
</div>
-->

---

## 🚀 Quick Start

```bash
git clone https://github.com/manishsinghks/Kukku.git
cd Kukku
./scripts/start.sh              # creates venv + installs deps on first run
cp .env.example .env            # add a bot token + one free LLM key
```

1. Set `TELEGRAM_BOT_TOKEN` (from [@BotFather](https://t.me/BotFather)) and **one** LLM key — a free [Gemini key](https://aistudio.google.com/apikey) needs no card. (Full list of options: [Environment variables](#environment-variables).)
2. Message your bot once → it replies with your Telegram ID → put it in `ALLOWED_USER_IDS`, restart.
3. Dashboard: `./.venv/bin/python scripts/set_password.py` then `./scripts/web.sh` → **http://localhost:3000**

Optional: `brew install tesseract` (OCR). Full guide: [`docs/INSTALL.md`](docs/INSTALL.md).

---

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

---

## Docker

```bash
docker compose up -d
```

The backend API is published on `127.0.0.1:8788`, and the folders in
`docker-compose.yml` are mounted read-only. Note: on macOS a container **cannot**
open apps or lock the screen and only sees the folders you mount — native
(launchd) is the recommended way to run Kukku on a Mac.

---

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
[`docs/WEB_DASHBOARD.md`](docs/WEB_DASHBOARD.md).

---

## Always-online mode (optional, free)

By default Kukku lives and dies with your Mac. Run `./scripts/setup_cloud.sh` to
deploy a free Cloudflare Worker relay (no credit card):

- **Mac on** → messages flow through a free tunnel to full Kukku (files, commands, voice).
- **Mac off/asleep** → the Worker answers general questions with Gemini and tells
  you the file features are offline.

Revert anytime with `./scripts/disable_cloud.sh`.

---

## 🆚 How it compares

| | Kukku | ChatGPT | Cursor | Raycast | Telegram bots |
|---|:---:|:---:|:---:|:---:|:---:|
| Runs locally / private | ✅ | ❌ | partial | ✅ | ❌ |
| Sees your files (semantic) | ✅ | ❌ | code only | ❌ | ❌ |
| OCR on screenshots | ✅ | ❌ | ❌ | ❌ | ❌ |
| Persistent memory | ✅ | partial | ❌ | ❌ | rare |
| On your phone | ✅ | ✅ | ❌ | ❌ | ✅ |
| Free to run | ✅ | ❌ | ❌ | partial | ✅ |
| Open source | ✅ | ❌ | ❌ | ❌ | varies |

---

## Development

```bash
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/pytest                 # unit + integration tests (all must pass)
./.venv/bin/ruff check app tests   # lint
cd web && npm install && npm run build   # dashboard build
```

See [`docs/EXTENDING.md`](docs/EXTENDING.md) to add a new tool or module — a change
to the shared agent benefits both Telegram and the dashboard automatically.

---

## 🗺 Roadmap

- [ ] ⌘K command palette
- [ ] Image vision in chat (Gemini multimodal)
- [ ] PWA (installable dashboard)
- [ ] Settings write-through from the UI
- [ ] Calendar + Gmail modules

Full list: [`docs/ROADMAP.md`](docs/ROADMAP.md) · Changes: [`CHANGELOG.md`](CHANGELOG.md)

---

## ❓ FAQ

<details><summary><b>Is it really free?</b></summary>
Yes — it runs on free LLM tiers (Gemini/Groq/OpenRouter) or fully-local Ollama. No subscription.
</details>
<details><summary><b>Where does my data go?</b></summary>
Nowhere. The backend binds to <code>127.0.0.1</code>, data lives in a local SQLite + ChromaDB, and only your Telegram ID can talk to the bot.
</details>
<details><summary><b>Does it work when my Mac is asleep?</b></summary>
With the optional free Cloudflare relay, the bot answers general questions while your Mac is off; file/command features resume when it wakes.
</details>
<details><summary><b>macOS only?</b></summary>
Local commands and indexing are tuned for macOS today; the backend and dashboard are portable. Docker is supported.
</details>

More in [`docs/FAQ.md`](docs/FAQ.md).

---

## 🤝 Contributing & Security

PRs welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md); please run the tests and
linter first. Found a vulnerability? Report it privately per
[`docs/SECURITY.md`](docs/SECURITY.md#reporting-a-vulnerability). Only your Telegram
ID is accepted, and the dashboard binds to `127.0.0.1` with Argon2 + JWT.

## 📄 License

[MIT](LICENSE) — © Kukku contributors.

---

## More docs

[Architecture](docs/ARCHITECTURE.md) ·
[Web Dashboard](docs/WEB_DASHBOARD.md) ·
[Features](docs/FEATURES.md) ·
[API reference](docs/API_REFERENCE.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md) ·
[Recovery](docs/RECOVERY.md) ·
[CI](docs/CI.md) ·
[Changelog](CHANGELOG.md) ·
[Brand guide](docs/brand/BRAND_GUIDE.md)

<div align="center"><br/><sub><b>Kukku</b> · Always on. Always yours.</sub></div>
