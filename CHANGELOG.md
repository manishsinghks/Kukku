# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed the project from **Jarvis** to **Kukku** across all user-facing
  surfaces (bot replies, dashboard, docs). Internal identifiers tied to the
  running deployment (launchd label, Cloudflare Worker name, data paths) were
  intentionally left unchanged for compatibility.
- Open-source readiness: added `LICENSE` (MIT), `CONTRIBUTING.md`,
  `CHANGELOG.md`, a hardened `.gitignore`, and a security disclosure policy.
- Removed personal absolute paths from the launchd plist and the dashboard
  preview harness (now derived from `$HOME` / a `__KUKKU_DIR__` placeholder).

### Added
- **Text-to-speech** in the dashboard chat — Kukku reads replies aloud via the
  browser's Web Speech API, with a per-message speak button and an "Auto-speak"
  toggle (EN/हिं voice follows the language pill).

## [1.0.0]

Initial feature-complete release.

### Added
- **Telegram bot**: tool-use agent with streaming replies, typing indicator,
  and Markdown; allowlisted access by Telegram user ID.
- **Hybrid file search**: filename (fuzzy) + content + semantic similarity
  (ChromaDB + sentence-transformers), merged and ranked with a recency boost.
- **OCR**: screenshots/images text-indexed via Tesseract (English + Hindi).
- **Voice**: local transcription with faster-whisper (English + Hindi).
- **Hindi / Hinglish** understanding and replies that mirror the user's script.
- **Local commands**: allowlisted app/folder actions; destructive ones require
  confirmation.
- **Web search**: Gemini Google-Search grounding with a DuckDuckGo fallback.
- **Reminders, proactive alerts (battery/disk), weather, daily DB backup** —
  all at zero LLM cost.
- **Memory**: persistent notes, aliases, and full conversation history in SQLite.
- **Multi-provider LLM failover**: Gemini → Groq → OpenRouter (and local Ollama),
  with auto-retry, cooldowns, and shared provider observability.
- **Always-online cloud relay**: a free Cloudflare Worker + Durable Object
  long-poll relay so the bot answers general questions while the Mac is asleep.
- **Web dashboard** (Next.js): Argon2 + JWT login and 10 modules — AI Chat
  (streaming, live Telegram sync, voice input), Universal Search, Memory,
  File Explorer, OCR Search, Automation, Developer, System Monitor,
  Notifications, and Settings.
- **Engineering documentation set** under `docs/`.

[Unreleased]: https://example.com/compare
[1.0.0]: https://example.com/releases/1.0.0
