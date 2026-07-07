# API Reference

Three interfaces: the **Dashboard HTTP API**, the **Agent tools** (what the AI can
call), and the **Cloud Worker endpoints**.

---

## 1. Dashboard HTTP API

Base URL: `http://127.0.0.1:8788` (local only). Interactive docs at `/api/docs`.
Defined in `app/dashboard/api.py`.

| Method | Path | Returns |
|---|---|---|
| GET | `/` | The dashboard HTML page |
| GET | `/api/status` | Full snapshot: version, LLM, provider status, system stats, DB counts, vector stats, indexer state |
| GET | `/api/files?limit=200&q=<text>` | Indexed files (optionally filtered by name) |
| GET | `/api/files/stats` | File counts by status and type |
| GET | `/api/searches?limit=100` | Recent search history |
| GET | `/api/logs?limit=100` | Recent request log (audit trail) |
| GET | `/api/memory` | `{memories: [...], aliases: [...]}` |
| POST | `/api/reindex` | Triggers a full background rescan → `{"ok": true}` |

### `GET /api/status` (the important one)
```json
{
  "version": "1.0.0",
  "llm": "Groq (llama-3.3-70b-versatile) → Gemini (gemini-2.5-flash)",
  "providers": {
    "Groq (llama-3.3-70b-versatile)": {"in_cooldown": false, "cooldown_left_s": 0},
    "Gemini (gemini-2.5-flash)": {"in_cooldown": false, "cooldown_left_s": 0}
  },
  "system": {"cpu_percent": 12, "ram_percent": 61, "ram_used_gb": 9.8,
             "ram_total_gb": 16, "disk_percent": 72, "uptime_s": 8123},
  "db": {"messages": 120, "memories": 4, "aliases": 2, "requests": 96,
         "searches": 33, "files_indexed": 3350, "chunks": 24152},
  "vector": {"available": true, "chunks": 24152, "model": "...all-MiniLM-L6-v2"},
  "indexer": {"scanning": false, "pending": 0, "last_scan": 1751612345.1,
              "watched_dirs": ["/Users/you/Desktop", "..."]}
}
```

Example:
```bash
curl -s http://127.0.0.1:8788/api/status | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8788/api/reindex
```

---

## 2. Agent tools (what the AI can call)

Defined in `app/core/agent.py` (`TOOLS`), executed in `_run_tool`. The AI picks
these; you don't call them directly, but knowing them explains what Kukku can do.

| Tool | Arguments | What it does |
|---|---|---|
| `search_files` | `query`, `search_type?`, `file_type?` | Hybrid ranked laptop search |
| `read_file` | `path`, `max_chars?` | Extract a file's text (for RAG) |
| `send_file` | `path` | Attach a file to the Telegram reply |
| `run_local_command` | `action`, `target?`, `confirmed?` | Allowlisted Mac action |
| `web_search` | `query` | Gemini-grounded web search (DDG fallback) |
| `save_memory` | `content` | Persist a fact |
| `set_alias` | `name`, `value` | Save a shortcut |
| `system_status` | — | CPU/RAM/disk snapshot |
| `get_weather` | `city` | Current weather (Open-Meteo) |
| `set_reminder` | `text`, `when?` (ISO) or `daily_time?` (HH:MM) | Schedule a reminder |
| `list_reminders` | — | List active reminders |
| `cancel_reminder` | `id` | Cancel a reminder |

### `run_local_command` actions
`open_vscode`, `open_chrome`, `open_folder`, `open_file`, `open_app`,
`read_clipboard`, `copy_to_clipboard`, `lock_screen`, `sleep`, `shutdown`⚠️,
`restart`⚠️ (⚠️ = requires `confirmed=true`).

---

## 3. Cloud Worker endpoints

Defined in `cloud/worker.js`. Public URL: `https://jarvis-relay.<subdomain>.workers.dev`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/webhook` | `x-telegram-bot-api-secret-token` | Telegram delivers updates here |
| POST | `/pull` | `x-bridge-secret` | The Mac long-polls for updates |
| POST | `/register` | `x-bridge-secret` | Legacy no-op (kept for old scripts) |
| GET | `/health` | none | `{"ok": true}` liveness check |

### RelayDO (Durable Object) internal routes
Not public — only the Worker calls these:
| Path | Purpose |
|---|---|
| `/deliver` | Worker hands a new update to the mailbox; returns `{online}` |
| `/pull` | Held open (long-poll) until an update arrives or 20s passes |

---

## 4. Telegram bot commands

Handled in `app/bot/telegram_bot.py`:
| Command | Effect |
|---|---|
| `/start`, `/help` | Capability overview |
| `/status` | CPU/RAM/disk + index + active LLM |
| `/memory` | List saved memories |
| `/clear` | Clear this chat's conversation history |
| `/reindex` | Trigger a full rescan |

Anything else (text, voice, files) goes to the agent.

---

## 5. Key internal classes (for developers)

| Class | File | Role |
|---|---|---|
| `Settings` | `config.py` | All configuration |
| `Database` | `db/database.py` | SQLite access |
| `VectorStore` | `search/vector_store.py` | ChromaDB access |
| `Indexer` | `search/indexer.py` | Background file indexing |
| `FileSearch` | `search/file_search.py` | Hybrid search |
| `Agent` | `core/agent.py` | Tool-use loop |
| `FailoverProvider` / `OpenAICompatProvider` | `core/llm.py` | AI providers |
| `Transcriber` | `core/voice.py` | Voice → text |
| `Scheduler` | `core/scheduler.py` | Reminders/alerts/backup |
| `JarvisBot` | `bot/telegram_bot.py` | Telegram interface |
| `CloudBridge` | `bot/bridge.py` | Long-poll transport |

Next: [DATABASE.md](DATABASE.md) or [EXTENDING.md](EXTENDING.md).
