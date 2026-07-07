# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-07

The first official public release of **Kukku** — a private, local-first personal
AI that runs on your Mac and answers on Telegram and a web dashboard.

### Major features
- **Telegram bot** — tool-use agent with streaming replies, typing indicator, and
  Markdown; access is allowlisted by Telegram user ID.
- **Web dashboard** (Next.js) — Argon2 + JWT login and 10 modules: AI Chat
  (streaming, live Telegram sync, voice input, text-to-speech), Universal Search,
  Memory, File Explorer, OCR Search, Automation, Developer, System Monitor,
  Notifications, and Settings. Fully responsive (desktop → mobile drawer).
- **Hybrid file search** — filename (fuzzy) + content + semantic similarity
  (ChromaDB + sentence-transformers), merged and ranked with a recency boost.
- **OCR** — screenshots and images text-indexed via Tesseract (English + Hindi).
- **Voice** — local transcription with faster-whisper (English + Hindi).
- **Hindi / Hinglish** — understanding and replies that mirror the user's script.
- **Local commands** — allowlisted app/folder actions; destructive ones require
  explicit confirmation. No arbitrary shell execution.
- **Web search** — Gemini Google-Search grounding with a DuckDuckGo fallback.
- **Reminders, proactive alerts (battery/disk), weather, daily DB backup** — all
  at zero LLM cost.
- **Memory** — persistent notes, aliases, and full conversation history in SQLite,
  shared live between Telegram and the dashboard.
- **Multi-provider LLM failover** — Gemini → Groq → OpenRouter (and local Ollama),
  with auto-retry, cooldowns, and shared provider observability.
- **Always-online cloud relay** — an optional free Cloudflare Worker + Durable
  Object long-poll relay so the bot answers general questions while the Mac sleeps.

### Security
- Every dashboard data endpoint requires authentication (Argon2id password hash +
  JWT access/refresh, login rate-limiting, `sub`/type validation).
- Backend binds to `127.0.0.1` by default; only the configured Telegram ID is
  accepted, and rejected access is logged.
- No arbitrary shell execution (list-arg `subprocess` + strict allowlist);
  parameterized SQL; file downloads are `$HOME`-jailed and must be indexed.
- Added a security disclosure policy (`docs/SECURITY.md`) and regression tests
  asserting `401` for unauthenticated access across all sensitive endpoints.

### Branding
- Complete product identity: the "presence-dot" logo, iris/apricot colour system,
  typography, and a full brand guide (`docs/brand/BRAND_GUIDE.md`).
- Wired favicon (SVG + PNG fallback), Apple touch icon, and a PWA web manifest
  with maskable icons into the dashboard.

### Documentation
- Premium README plus a complete engineering docs set under `docs/`
  (architecture, workflow, install, features, API reference, troubleshooting,
  recovery, FAQ, security), `LICENSE` (MIT), and `CONTRIBUTING.md`.

### Breaking changes
- **None** — this is the first public release, so there is no prior public API to
  break. For anyone who tracked pre-release builds: the legacy unauthenticated
  static dashboard and its open `/api/*` read endpoints were **removed**; the
  Next.js dashboard and its authenticated routers are now the only interface.

### Known limitations
- **macOS-first.** Local commands and indexing are tuned for macOS; the backend
  and dashboard are portable and Docker is supported, but non-mac local actions
  are limited.
- **Settings are read-only in the UI** — configuration changes go through `.env`
  + restart.
- **Chat is text + voice-in / voice-out**; image (vision) input is not yet wired.
- **No `⌘K` command palette** and **no installable PWA service worker** yet
  (manifest/icons are in place).
- Test coverage is strong on core paths; the indexer, vector store, voice, and
  bot handlers do not yet have dedicated unit tests.

### Future plans
See the [roadmap](docs/ROADMAP.md). Next up (1.1): ⌘K command palette, image
vision in chat, installable PWA, settings write-through, and Calendar/Gmail
modules.

[1.0.0]: https://github.com/manishsinghks/Kukku/releases/tag/v1.0.0
