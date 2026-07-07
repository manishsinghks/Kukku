# Troubleshooting (Part 10)

Every major problem in a fixed format: **symptoms → causes → fixes → logs to check →
commands → recovery.** Start with the "first response" below for anything.

---

## First response to any problem

```mermaid
flowchart TB
    P[Something's wrong] --> R{Is Kukku running?}
    R -->|launchctl list \| grep jarvis| Y[Yes: PID shown]
    R -->|No PID| RESTART[Restart it]
    Y --> L[Read the log:<br/>tail -50 data/logs/jarvis.log]
    L --> S[Check /status in Telegram<br/>or curl the dashboard]
    RESTART --> CMD["launchctl kickstart -k gui/$(id -u)/com.manish.jarvis"]
```

The two commands you'll use most:
```bash
tail -f ~/jarvis/data/logs/jarvis.log                       # watch the log live
launchctl kickstart -k gui/$(id -u)/com.manish.jarvis       # restart Kukku
```

---

## Problem 1 — Bot doesn't reply at all

**Symptoms:** You message the bot, nothing comes back (not even "typing").
**Causes:** Kukku isn't running · relay/webhook broken · two instances conflict.
**Fixes:**
1. Confirm it's running: `launchctl list | grep jarvis` (should show a PID).
2. Check the log for a crash: `tail -50 ~/jarvis/data/logs/jarvis.log`.
3. Check the relay is alive: `curl https://jarvis-relay.<subdomain>.workers.dev/health`
   → `{"ok":true}`.
4. Check the webhook: `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"` —
   `url` should point at the Worker.
5. Ensure only one instance: `pgrep -fl app.main` (two = they conflict).
**Recovery:** `launchctl kickstart -k gui/$(id -u)/com.manish.jarvis`.

---

## Problem 2 — "💤 Mac is offline" while the Mac is on

**Symptoms:** The bot answers general questions but adds the offline note; file
search/commands don't work.
**Cause:** The Mac's long-poll to the relay dropped (WiFi blip, sleep/wake).
**Fixes:**
1. Look for `Cloud relay connected (long-poll, no tunnel)` in the log.
2. The bridge auto-reconnects with backoff; give it ~30s.
3. If stuck: `launchctl kickstart -k gui/$(id -u)/com.manish.jarvis`.
**Logs:** `grep -i "relay\|poll" data/logs/jarvis.log | tail`.
**Live worker logs:** `cd cloud && npx -y wrangler@3 tail`.

---

## Problem 3 — "⏳ free AI quota" / rate-limit replies

**Symptoms:** "The free AI quota is catching its breath."
**Cause:** Both Groq and Gemini hit their free rate limits at once (heavy bursts).
**Fixes:**
1. Wait a minute — per-minute limits reset quickly.
2. Normal use rarely triggers this; it's usually rapid-fire bursts.
3. Long-term: keep Groq primary (generous) via `LLM_PRIORITY`.
**Logs:** `grep -i "rate limited\|failing over" data/logs/jarvis.log | tail`.

---

## Problem 4 — Raw tool call appears as text (`<function/...>`)

**Symptoms:** The bot replies with `<function/run_local_command {...}</function>`
instead of doing the thing.
**Cause:** A provider (usually Groq/Llama) emitted a tool call as text. This is
*handled* now — if you see it, the parser may have missed a new format.
**Fixes:** Restart to ensure latest code is loaded; report the exact text so the
parser (`_extract_text_tool_calls` in `llm.py`) can be extended.
**Logs:** `grep "tool call\|empty response" data/logs/jarvis.log | tail`.

---

## Problem 5 — Screenshot/OCR search finds nothing

**Symptoms:** "find the screenshot where X" returns nothing.
**Causes:** Tesseract not installed · image not indexed yet · image has no readable
text.
**Fixes:**
1. Install Tesseract: `brew install tesseract` (+ Hindi: it auto-uses `eng+hin` if
   `hin.traineddata` is present).
2. Re-index: send `/reindex` to the bot.
3. Check the dashboard → Files: OCR'd images show `chunks ≥ 1`.
**Logs:** `grep -i "ocr\|tesseract" data/logs/jarvis.log`.
**Command to verify Tesseract:** `/opt/homebrew/bin/tesseract --list-langs`.

---

## Problem 6 — Voice notes don't work

**Symptoms:** Voice note gets no reply or an error.
**Causes:** First-time model download in progress · `ffmpeg` missing · `ENABLE_VOICE`
off.
**Fixes:**
1. First voice note downloads the Whisper model (~1 min) — wait.
2. Install ffmpeg: `brew install ffmpeg`.
3. Check `ENABLE_VOICE=true` in `.env`.
**Logs:** `grep -i "whisper\|transcri\|voice" data/logs/jarvis.log`.

---

## Problem 7 — Local commands don't run

**Symptoms:** "open chrome" / "lock screen" does nothing.
**Causes:** macOS permission not granted · path outside home · destructive command
awaiting confirmation.
**Fixes:**
1. Grant permission: System Settings → Privacy & Security → Automation/Accessibility.
2. Files/folders must be under your home dir (safety rule).
3. Shutdown/restart ask you to confirm first — reply "yes".
**Logs:** `grep -i "local command" data/logs/jarvis.log`.

---

## Problem 8 — Semantic search "unavailable" (dashboard shows "off")

**Symptoms:** Dashboard Embeddings card says "off"; search only matches filenames.
**Cause:** ChromaDB / sentence-transformers failed to load.
**Fixes:** `cd ~/jarvis && ./.venv/bin/pip install -r requirements.txt`, then restart.
**Logs:** `tail -50 data/logs/jarvis.log | grep -i vector`.

---

## Problem 9 — Reminder didn't fire

**Symptoms:** A reminder never arrived.
**Causes:** Mac was off/asleep at fire time · Kukku wasn't running.
**Fixes:** Reminders only fire while Kukku runs. Keep the Mac awake for
time-critical ones. (Cloud-side reminders are on the roadmap.)
**Verify it's stored:** `sqlite3 data/jarvis.db "SELECT text,
datetime(due_ts,'unixepoch','localtime') FROM reminders WHERE active=1;"`

---

## Problem 10 — Dashboard unreachable

**Symptoms:** `http://127.0.0.1:8788` won't load.
**Causes:** Kukku not running · port taken.
**Fixes:** Confirm Kukku is up; change `DASHBOARD_PORT` in `.env` if 8788 is taken.
Note: it's **local-only by design** — not reachable from other devices.

---

## Problem 11 — Homebrew "Directory not empty @ dir_s_rmdir" on install

**Symptoms:** `brew install` fails to symlink a formula.
**Cause:** Another tool planted stub directories in `/opt/homebrew/opt/`.
**Fix:** `mv /opt/homebrew/opt/<formula> ~/stub-backup && brew link <formula>`, then
retry the install. (This is what happened installing Tesseract's dependencies.)

---

## Problem 12 — Kukku crashes on startup

**Symptoms:** No PID after a few seconds; `launchd.err.log` has a traceback.
**Causes:** Bad `.env` value · missing dependency · corrupt DB.
**Fixes:**
1. Read the crash: `tail -30 ~/jarvis/data/logs/launchd.err.log`.
2. Missing dep: `./.venv/bin/pip install -r requirements.txt`.
3. Bad config: check `.env` against `.env.example`.
4. Corrupt DB (rare): restore from `data/backups/` (see [RECOVERY.md](RECOVERY.md)).

---

## Log reference (what each log is for)

| Log | Shows | Read with |
|---|---|---|
| `data/logs/jarvis.log` | Everything the app does | `tail -f data/logs/jarvis.log` |
| `data/logs/launchd.err.log` | Startup crashes | `tail -30 …` |
| `data/logs/launchd.out.log` | launchd stdout | `tail -30 …` |
| SQLite `request_log` | User-facing audit trail | Dashboard → Logs |
| `wrangler tail` | Live cloud Worker logs | `cd cloud && npx wrangler@3 tail` |

---

## Full recovery procedures

See [RECOVERY.md](RECOVERY.md) for: restart/stop/start, rebuild the search index,
nuclear reset, rotate credentials, and migrate to a new Mac.

## Health-check one-liner

```bash
cd ~/jarvis && echo "PID:" && launchctl list | grep jarvis && \
curl -s http://127.0.0.1:8788/api/status | python3 -c "import json,sys;d=json.load(sys.stdin);print('LLM:',d['llm']);print('files:',d['db']['files_indexed'],'vectors:',d['vector'].get('chunks'))" && \
tail -3 data/logs/jarvis.log
```
