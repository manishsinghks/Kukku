# FAQ

Quick answers to common questions. For depth, follow the links.

---

### Is Kukku really free?
Yes. Groq + Gemini free tiers for AI, Cloudflare free tier for the relay, and local
free models for voice/OCR/search. No credit card, no paid services. See
[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md#8-cost-model-why-its-free).

### Does it work when my Mac is off?
Partially. **General questions** are answered by the always-on cloud relay
(Gemini→Groq) with a "💤 Mac offline" note. **File search, commands, and voice**
need the Mac on (they run there). See [ARCHITECTURE.md](ARCHITECTURE.md).

### Do my files leave my Mac?
Not for search/OCR/voice — those are local. Only your *message text* and any file
the AI *reads* go to the AI provider to compose an answer. Don't ask it to read
truly secret files. See [SECURITY.md](SECURITY.md#7-data-privacy).

### Can other people use my bot?
No. Only Telegram IDs in `ALLOWED_USER_IDS` are accepted (checked at the cloud *and*
the Mac). Everyone else is silently rejected and logged.

### How do I add a folder to search?
Edit `INDEX_DIRS` in `.env` (comma-separated), then restart. New folders are indexed
on the next scan.

### Why does the first voice note take so long?
It downloads the Whisper model once (~1 minute). After that, voice notes take a few
seconds. See [PERFORMANCE.md](PERFORMANCE.md).

### It said "Mac is offline" but my Mac is on. Why?
The Mac's long-poll to the relay dropped momentarily. It reconnects automatically;
if stuck, restart: `launchctl kickstart -k gui/$(id -u)/com.manish.jarvis`. See
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Which AI is it using right now?
`/status` in Telegram, or the dashboard, shows the active provider. Default order is
Groq (primary) → Gemini (fallback). Change with `LLM_PRIORITY` in `.env`.

### Why Groq first, not Gemini?
Groq's free tier is far more generous, so everyday use doesn't burn Gemini's small
quota. Both are free. See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md#1-providers).

### It replied in Devanagari but I wrote Hinglish. Can I fix that?
It's told to match your script. If it slips, just say "reply in Hinglish". See
[FEATURES.md](FEATURES.md).

### How do I make it forget the conversation?
`/clear` wipes the current chat's history. `/memory` shows long-term memories (say
"forget X" to remove one).

### How do I restart / stop / reindex it?
```bash
launchctl kickstart -k gui/$(id -u)/com.manish.jarvis   # restart
launchctl unload ~/Library/LaunchAgents/com.manish.jarvis.plist  # stop
# reindex: send /reindex to the bot, or POST /api/reindex
```
See [RECOVERY.md](RECOVERY.md).

### Where is everything stored?
In `data/`: `jarvis.db` (SQLite), `chroma/` (embeddings), `logs/`, `backups/`. See
[DATABASE.md](DATABASE.md).

### Can I run it on a different Mac?
Yes — copy the repo + `.env` + optionally `data/jarvis.db`, run `./scripts/start.sh`,
install `tesseract`/`ffmpeg`, load the launchd plist. See [RECOVERY.md](RECOVERY.md).

### Why isn't there a local LLM (Ollama)?
You chose not to — a local model uses several GB of RAM constantly and would slow
your 16GB Mac. Kukku uses cloud AI for thinking to stay light. See
[PERFORMANCE.md](PERFORMANCE.md#ram-budget-your-16gb-mac).

### Reminders didn't fire — why?
Reminders only fire while Kukku is running (Mac on). A reminder set for 3am with the
Mac asleep is missed. Cloud-side reminders are a planned fix — see
[ROADMAP.md](ROADMAP.md).

### How do I add a new capability?
Add a tool — 3 steps in `agent.py`. See [EXTENDING.md](EXTENDING.md#the-golden-pattern-adding-a-new-tool).

### Is my data backed up?
Yes — the DB is backed up daily to `data/backups/` (last 7 kept). `.env` is *not*
in those backups — back it up separately.

### How many tests are there / how do I run them?
161 tests. `cd ~/Kukku && ./.venv/bin/pytest -q`.

### Something's broken and I'm stuck.
Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md), check `data/logs/jarvis.log`, and if
still stuck, the logs + `/status` output are what a developer needs to diagnose it.
