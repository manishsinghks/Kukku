# CONTINUE HERE — Resume & Backlog

This file lets **any new session (or you) pick up instantly** without losing
context. If a chat runs out, start a fresh one and paste the "How to resume"
message below.

---

## 🔄 How to resume in a NEW chat

Start a new Claude Code session in `~/Kukku` and send this:

> Continue the Kukku project. Read `docs/NEXT_STEPS.md`, `docs/WEB_DASHBOARD.md`,
> and `docs/ARCHITECTURE.md` to get up to speed, then let's work on: **<the item
> you want>**. Telegram bot + web dashboard are already built and working; don't
> rebuild — extend.

That's it. The codebase is documented, committed, and on GitHub, so nothing is
lost between sessions.

**Fast facts a new session needs:**
- Run backend: it's a launchd service (`launchctl list | grep jarvis`). Logs: `data/logs/jarvis.log`.
- Run web app: `~/Kukku/scripts/web.sh` → http://localhost:3000
- Tests: `./.venv/bin/pytest -q` (must stay green) · Lint: `./.venv/bin/ruff check app tests`
- Web build check: `cd web && npm run build`
- After a feature: commit + push to your own remote
- Set dashboard password: `./.venv/bin/python scripts/set_password.py`

---

## ✅ What's already built (don't rebuild)

- **Telegram bot**: streaming, voice (Whisper), OCR (eng+hin), file search, commands,
  reminders, alerts, weather, memory, Hinglish. Always-online cloud relay.
- **AI**: Gemini → Groq → OpenRouter failover, retries, cooldowns, provider metrics.
- **Web dashboard** (Next.js, `web/`): login (Argon2+JWT), 10 modules — AI Chat
  (streaming, markdown, provider badge, **voice input**, **text-to-speech**, live Telegram sync),
  Universal Search, Memory, File Explorer, OCR Search, Automation (reminders),
  Developer (activity/logs), System Monitor, Notifications, Settings.
- **One source of truth**: dashboard & Telegram share the same agent, DB, memory,
  realtime EventBus. 161 tests pass.

Architecture: [WEB_DASHBOARD.md](WEB_DASHBOARD.md) · [ARCHITECTURE.md](ARCHITECTURE.md)
Extend safely: [EXTENDING.md](EXTENDING.md)

---

## 📋 Backlog (prioritized — pick from the top)

### Quick wins (high value, low effort)
- [ ] **⌘K command palette** — jump modules / search / run commands (Raycast feel).
- [x] **Text-to-speech** — Kukku reads replies aloud (Web Speech `speechSynthesis`, free). ✅ Done — per-message speak button + header "Auto-speak" toggle; EN/हिं voice follows the language pill.
- [ ] **Image vision in chat** — drag a photo → Gemini (multimodal) describes/answers.
- [ ] **PWA** — make the dashboard installable on phone/desktop (manifest + service worker).
- [ ] **Multiple chat threads** — ChatGPT-style conversation list.

### Medium
- [ ] **Settings write-through** — edit provider order / folders / thresholds from the UI (needs a safe `.env` writer + reload).
- [ ] **File preview pane** — inline PDF/image/text preview in File Explorer.
- [ ] **Memory tags & categories** — group/filter memories (add a `tags` column).
- [ ] **Remote access** — same-WiFi (LAN bind + PWA) OR Cloudflare Tunnel (with hardening). See NEXT_STEPS notes.

### Bigger integrations
- [ ] **Calendar module** (Google Calendar, OAuth) + feed into a daily briefing.
- [ ] **Gmail module** (OAuth, read-only first).
- [ ] **GitHub module** (PAT — easiest of the integrations).
- [ ] **Automation triggers** — "when X happens, do Y" rules engine (extend scheduler.py).
- [ ] **Cloud-side reminders** — fire from the Cloudflare Worker so they work with the Mac asleep.
- [ ] **Multilingual embeddings** — better Hindi *content* search.
- [ ] **Encryption at rest** — encrypt the memory DB / use macOS Keychain for secrets.

### Your own ideas (add them here!)
- [ ] …
- [ ] …

---

## 🧭 Recommended order (if unsure)
1. ~~Text-to-speech~~ ✅ done
2. Image vision in chat
3. ⌘K command palette
4. PWA + same-WiFi remote access
5. Settings write-through

Each is free and fits the shared-backend pattern — no rebuilds.

---

## 🔐 Standing reminders
- Rotate the keys that passed through chat (OpenRouter, Gemini, Groq, bot token),
  update `.env`. Repo has no secrets, so no rush for GitHub's sake.
- Keep tests green and commit+push after each feature.
