# Project Structure (Part 2)

This explains **every folder and important file**: why it exists, what it does,
how it talks to others, how you should modify it, and what you must never touch.

Legend: 🟢 safe to edit · 🟡 edit carefully · 🔴 don't edit unless you deeply understand it

---

## Top-level layout

```
Kukku/
├── app/                  # All the Python application code
│   ├── main.py           # 🔴 Entry point — wires everything together
│   ├── config.py         # 🟢 All settings (reads .env)
│   ├── bot/              # Telegram + cloud bridge
│   ├── core/             # The brain: agent, LLM, scheduler, voice
│   ├── search/           # File indexing + semantic search
│   ├── tools/            # Things the agent can "do"
│   ├── db/               # SQLite database layer
│   ├── dashboard/        # Local web dashboard (FastAPI)
│   └── utils/            # Logging
├── cloud/                # Cloudflare Worker (the always-on relay)
│   ├── worker.js         # 🟡 The relay + Durable Object
│   └── wrangler.toml     # 🟡 Worker config
├── scripts/              # Startup + deployment scripts
├── tests/                # 161 automated tests
├── docs/                 # ← you are here
├── data/                 # 🔴 Runtime data (DB, embeddings, logs) — never commit
├── .env                  # 🔴 Your secrets (git-ignored)
├── .env.example          # 🟢 Template for .env
├── requirements.txt      # 🟢 Python dependencies
└── Dockerfile            # 🟡 Container build
```

---

## `app/` — the application

### `app/main.py` 🔴
**The wiring hub.** This is the one file that knows about *everything*. On startup
it, in order: loads config, sets up logging, opens the database, creates the
vector store, starts the indexer, builds the AI provider chain, creates the agent,
starts the dashboard web server, starts the Telegram bot, starts the cloud bridge,
and starts the scheduler. On shutdown it stops them all cleanly.

- **How it communicates:** it *constructs* every other object and passes
  dependencies in (this is called "dependency injection" — objects don't create
  their own dependencies, they receive them).
- **How to modify:** only when you add a whole new subsystem (like a new
  background service). To add a *feature*, you almost never touch `main.py`.
- **Why 🔴:** the startup/shutdown order matters. Get it wrong and things
  initialize before their dependencies exist.

### `app/config.py` 🟢
**Every setting in one place.** It's a `pydantic-settings` class that reads from
`.env` and environment variables, with sensible defaults. It also has computed
properties like `allowed_ids` (parses the comma list into a set), `index_paths`
(turns folder names into real paths), `owner_chat_id`, and path helpers
(`db_path`, `chroma_dir`, `backup_dir`).

- **How to modify:** add a new setting here as a typed field with a default. It's
  automatically available everywhere via `settings.your_field`.
- **Why 🟢:** adding fields is safe. Just don't rename existing ones without
  updating `.env`.

---

### `app/bot/` — Telegram + cloud transport

| File | Emoji | Role |
|---|---|---|
| `telegram_bot.py` | 🟡 | The waiter: auth, commands, streaming replies, voice, file uploads |
| `bridge.py` | 🟡 | The long-poll client that pulls messages from the cloud Worker |

**`telegram_bot.py`** — Contains the `JarvisBot` class. It registers handlers for
commands (`/start`, `/status`, `/memory`, `/clear`, `/reindex`), text, voice, and
files. Its most important method is `_handle_query`, which shows the "typing"
indicator, posts a placeholder message, streams the agent's answer into it, and
sends any files. Also does the security check (`_authorized`).

- **Modify when:** adding a new `/command`, or changing how replies look/stream.
- **Careful because:** the streaming logic (editing a message repeatedly) has to
  respect Telegram's rate limits — don't remove the throttle in `_handle_query`.

**`bridge.py`** — Contains `CloudBridge`. It runs one async loop that does
`POST /pull` to the Worker, receives any queued Telegram updates, and feeds them
into the bot. Reconnects with backoff on any error. **No tunnel, no local server**
— just outbound HTTPS.

- **Modify when:** changing the transport (rare).
- **Careful because:** this is the reliability-critical path. It was rewritten
  once already to remove the fragile tunnel (see git history).

---

### `app/core/` — the brain

| File | Emoji | Role |
|---|---|---|
| `agent.py` | 🟡 | The head chef: the tool-use loop + all tool definitions |
| `llm.py` | 🟡 | AI providers, failover, retries, tool-call parsing |
| `scheduler.py` | 🟢 | Reminders, system alerts, DB backup |
| `voice.py` | 🟢 | Whisper voice-note transcription |

**`agent.py`** — The most important file to understand. Defines:
- `TOOLS` — the list of tools (as JSON schemas) the AI is allowed to call.
- `Agent.run()` — the loop: send message + tools to the LLM, if it asks to call a
  tool, run it, feed the result back, repeat (up to 8 rounds), then reply.
- `Agent._run_tool()` — the big dispatcher that actually executes each tool.
- `Agent._system_prompt()` — builds the instructions sent to the AI every turn
  (includes your memories, aliases, current time, language rules).

- **Modify when:** adding a new capability the AI can use → add a tool (see
  [EXTENDING.md](EXTENDING.md)).

**`llm.py`** — Defines `ClaudeProvider`, `OpenAICompatProvider` (covers Gemini,
Groq, OpenRouter, Ollama), and `FailoverProvider` (the chain that tries one, falls
to the next). Also the retry logic and the parser that recovers tool calls Groq
emits as text. `build_provider()` assembles the chain from your config.

- **Modify when:** adding a new AI provider, or tuning retry/failover behavior.

**`scheduler.py`** — `Scheduler` runs three async loops: reminders (fire due ones),
monitor (battery/disk alerts), backup (daily DB copy). `next_daily_ts()` computes
the next occurrence of a daily time. Zero AI cost.

**`voice.py`** — `Transcriber` lazy-loads `faster-whisper` and transcribes an
audio file to text. Auto-detects language (English/Hindi/Hinglish).

---

### `app/search/` — indexing + search

| File | Emoji | Role |
|---|---|---|
| `indexer.py` | 🟡 | Background scanning + live file watching |
| `extractors.py` | 🟢 | Turn any file (PDF, DOCX, image…) into plain text |
| `vector_store.py` | 🟡 | ChromaDB wrapper — stores/queries embeddings |
| `file_search.py` | 🟢 | Combines filename + semantic search, ranks results |

**`indexer.py`** — `Indexer` runs a scanner thread (walks your folders), a worker
thread (processes the queue), and a watchdog observer (reacts to file changes
live). Decides which files to (re)index. `_needs_retry` re-processes files that
failed only because a dependency (like Tesseract) was missing.

**`extractors.py`** — Pure functions: `extract_text(path)` dispatches by file type
to PyMuPDF (PDF), python-docx (Word), openpyxl (Excel), python-pptx (PowerPoint),
or Tesseract (images/OCR). `chunk_text()` splits long text into overlapping pieces
for embedding. `classify()` labels a file (document/code/image/data).

**`vector_store.py`** — `VectorStore` lazy-loads ChromaDB + the sentence-transformer
model. `index_file()` stores a file's chunks as embeddings; `query()` finds the
most similar chunks to a search phrase.

**`file_search.py`** — `FileSearch.search()` runs both a fuzzy filename match
(rapidfuzz) and a semantic query (vector store), merges them, boosts recent files,
ranks, and caches for 60s.

---

### `app/tools/` — things the agent can do

| File | Emoji | Role |
|---|---|---|
| `local_commands.py` | 🟡 | Allowlisted Mac commands (open apps, lock, clipboard…) |
| `web_search.py` | 🟢 | Web search (Gemini grounding → DuckDuckGo fallback) |
| `weather.py` | 🟢 | Weather via Open-Meteo (free, no key) |
| `system_status.py` | 🟢 | CPU/RAM/disk via psutil |

**`local_commands.py`** — The security-critical `execute(action, target, confirmed)`
function. Only actions in the `ACTIONS` allowlist run. Destructive ones
(`shutdown`, `restart`) require `confirmed=True`. Paths must resolve under your home
folder. **This is the file that keeps the AI from doing damage** — edit with care.

---

### `app/db/database.py` 🟡
The `Database` class — a thread-safe wrapper around one SQLite connection (WAL
mode). Every table has clear methods: `add_message`, `add_memory`, `set_alias`,
`log_request`, `upsert_file`, `add_reminder`, `backup`, etc. This is the shared
foundation almost every module uses.

- **Modify when:** adding a new table or query. Add the `CREATE TABLE` to the
  `_SCHEMA` string and add methods. Schema uses `CREATE TABLE IF NOT EXISTS`, so
  new tables appear automatically on next start.

---

### `app/dashboard/` — the web dashboard

| File | Emoji | Role |
|---|---|---|
| `api.py` | 🟢 | FastAPI app factory: auth wiring, `/api/status`, `/api/reindex` |
| `chat_api.py` | 🟢 | Authenticated chat / realtime (SSE) / memory / search router |
| `modules_api.py` | 🟢 | Authenticated reminders / files / OCR / activity / settings router |

Binds to `127.0.0.1:8788` (local only — on purpose, it exposes file paths). Serves
JSON only; every data endpoint requires a JWT. The dashboard **UI** is the Next.js
app in `web/` (port 3000). The old vanilla-JS `static/` dashboard was retired.

---

### `app/utils/logging.py` 🟢
Sets up rotating log files (`data/logs/jarvis.log`, 5×5MB) plus console output,
and quiets noisy third-party loggers. `get_logger(__name__)` is used everywhere.

---

## `cloud/` — the Cloudflare relay

| File | Emoji | Role |
|---|---|---|
| `worker.js` | 🟡 | The Worker (webhook handler) + `RelayDO` Durable Object |
| `wrangler.toml` | 🟡 | Worker name, bindings, migrations |
| `package.json` | 🟢 | Marks the folder as an ES module |

`worker.js` runs *on Cloudflare's servers*, not your Mac. It receives Telegram
webhooks, hands them to the Durable Object (which the Mac long-polls), and answers
directly when the Mac is offline. Deploy changes with
`cd cloud && npx wrangler@3 deploy`.

---

## `scripts/`

| File | Role |
|---|---|
| `start.sh` | 🟢 First-run setup (venv + deps) then launches Kukku |
| `setup_cloud.sh` | 🟡 Deploys the Worker, sets secrets, points the webhook |
| `disable_cloud.sh` | 🟢 Reverts to plain polling (no cloud relay) |
| `com.manish.jarvis.plist` | 🟡 launchd config that keeps Kukku running 24/7 |

---

## `data/` 🔴 (never commit, never hand-edit)

Created at runtime. Git-ignored. Contains:

```
data/
├── jarvis.db          # SQLite: history, memories, reminders, file index
├── jarvis.db-wal      # SQLite write-ahead log (don't touch)
├── chroma/            # ChromaDB embeddings
├── logs/              # Rotating app logs
├── backups/           # Daily DB backups (last 7)
├── inbox/             # Files you upload to the bot
└── voice/             # Temp voice notes (auto-deleted)
```

To reset the index safely, see [RECOVERY.md](RECOVERY.md). Don't edit `jarvis.db`
by hand while Kukku is running — use the app or stop it first.

---

## Files you should **never edit** (🔴 summary)

| File/Folder | Why |
|---|---|
| `data/` contents | Runtime state; edit via the app or you'll corrupt it |
| `.env` structure | You *fill in* values, but keep the keys' names |
| `app/main.py` startup order | Fragile; only touch when adding a subsystem |
| `*.pyc` / `__pycache__/` | Auto-generated Python bytecode |
| `.venv/` | The virtual environment; rebuilt by `start.sh` |

---

## The "where do I add X?" cheat sheet

| I want to add… | Put it in… |
|---|---|
| A new thing the AI can *do* | A tool in `app/core/agent.py` (+ maybe a new file in `app/tools/`) |
| A new `/command` | `app/bot/telegram_bot.py` |
| A new setting | `app/config.py` |
| A new database table | `app/db/database.py` |
| A new file type to index | `app/search/extractors.py` |
| A new AI provider | `app/core/llm.py` |
| A new dashboard panel | authenticated router in `app/dashboard/` + a page in `web/app/(app)/` |
| A new background job | `app/core/scheduler.py` |

Full walkthroughs in [EXTENDING.md](EXTENDING.md).
