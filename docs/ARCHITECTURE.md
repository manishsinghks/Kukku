# Architecture (Part 1 & Part 13)

This document explains **what the system is made of, why each piece exists, how a
request travels through it, and how the files depend on each other.**

---

## 1. The problem Kukku solves

You have a laptop full of files, projects, and screenshots. You want to ask
questions like *"find the screenshot where Docker failed"* or *"send me my
resume"* from your phone, in plain language, and get an answer — even when you're
not at your desk. Existing assistants (Siri, etc.) can't see your files or run
your commands. Kukku does, because it runs **on your machine** and is reachable
**through Telegram**, which you already have on your phone.

Concretely, Kukku solves four problems:

| Problem | Kukku's answer |
|---|---|
| "I can't find my own files" | Semantic search — search by *meaning*, not just filename |
| "I want to control my Mac remotely" | Allowlisted local commands over Telegram |
| "I want a private AI assistant" | Free LLMs + local data; nothing sold to third parties |
| "I want it available all the time" | Cloud relay answers even when the Mac sleeps |

---

## 2. High-level architecture

```mermaid
flowchart TB
    subgraph Phone["📱 Your Phone / Telegram"]
        U([You])
    end

    subgraph Cloud["☁️ Cloudflare (free, always-on)"]
        W[Worker<br/>worker.js]
        DO[(RelayDO<br/>Durable Object<br/>real-time mailbox)]
        W <--> DO
    end

    subgraph Mac["💻 Your Mac (Kukku process, 24/7 via launchd)"]
        BR[Bridge<br/>long-poll client]
        BOT[Telegram Bot Layer<br/>auth, streaming, voice]
        AG[Agent<br/>the tool-use brain]
        subgraph Tools["Tools the agent can call"]
            FS[File Search]
            LC[Local Commands]
            WS[Web Search]
            WX[Weather]
            MEM[Memory]
            RM[Reminders]
        end
        IDX[Indexer<br/>background]
        SCH[Scheduler<br/>reminders/alerts/backup]
        DASH[Dashboard<br/>FastAPI :8788]
    end

    subgraph Data["🗄️ Local storage"]
        SQL[(SQLite<br/>jarvis.db)]
        CHR[(ChromaDB<br/>embeddings)]
    end

    subgraph AI["🧠 AI providers (free tiers)"]
        GROQ[Groq / Llama 3.3]
        GEM[Gemini 2.5 Flash]
    end

    U -->|Telegram webhook| W
    W -->|Mac online| DO
    BR <-->|long-poll HTTPS| W
    BR --> BOT --> AG
    AG --> Tools
    AG <-->|understand + tool-call| GROQ
    GROQ -.failover.-> GEM
    FS --> CHR
    FS --> SQL
    MEM --> SQL
    RM --> SQL
    IDX --> CHR
    IDX --> SQL
    SCH --> SQL
    DASH --> SQL
    DASH --> CHR
    W -.Mac offline.-> GEM
    AG -->|reply| BOT --> BR --> W --> U
```

---

## 3. Why each component exists

Think of Kukku as a restaurant. Here's who does what:

| Component | Restaurant analogy | File(s) | Why it exists |
|---|---|---|---|
| **Telegram Bot layer** | The waiter | `app/bot/telegram_bot.py` | Takes your order (message), checks you're allowed in, shows "typing…", streams the reply back, handles voice notes and file uploads |
| **Cloud Relay (Worker + DO)** | The phone line to the kitchen | `cloud/worker.js` | Telegram can't reach your Mac directly (it's behind your router). The Worker is a public address that relays messages. The Durable Object is a real-time mailbox. |
| **Bridge** | The runner carrying orders from phone to kitchen | `app/bot/bridge.py` | The Mac *pulls* messages from the Worker (outbound only), so no fragile tunnel is needed |
| **Agent** | The head chef | `app/core/agent.py` | Decides what to do with your request and coordinates the tools. This is the brain. |
| **LLM providers** | The chef's trained instincts | `app/core/llm.py` | The actual AI models (Groq, Gemini) that understand language and decide which tool to use |
| **Tools** | Kitchen stations (grill, fryer) | `app/tools/`, `app/search/` | The things the chef can actually *do*: search files, run commands, get weather |
| **Indexer** | The prep cook stocking the pantry | `app/search/indexer.py` | Runs in the background reading your files so search is instant later |
| **Scheduler** | The kitchen timer | `app/core/scheduler.py` | Fires reminders, watches battery/disk, backs up the database |
| **Databases** | The pantry + recipe cards | `app/db/database.py` (SQLite), `app/search/vector_store.py` (ChromaDB) | Store your history, memories, reminders, and the searchable "fingerprints" of your files |
| **Dashboard** | The manager's office window | `app/dashboard/` | A local web page showing what's happening inside |

---

## 4. The three "planes" of the system

It helps to split Kukku into three planes that operate on different timescales:

```mermaid
flowchart LR
    subgraph RT["⚡ Real-time plane (per message)"]
        direction TB
        r1[Bridge receives] --> r2[Bot authenticates] --> r3[Agent runs tools] --> r4[Reply streams back]
    end
    subgraph BG["🔄 Background plane (continuous)"]
        direction TB
        b1[Indexer scans files] --> b2[Watchdog reacts to changes]
        b3[Scheduler checks reminders/battery/disk]
    end
    subgraph OD["📅 On-demand plane (occasional)"]
        direction TB
        o1[Dashboard HTTP requests]
        o2[Daily DB backup]
        o3[Full re-index]
    end
```

- **Real-time plane**: everything that happens when you send a message. Must be
  fast. Lives in `bot → agent → tools`.
- **Background plane**: always running, never blocks a message. Indexing and
  scheduling live here, in their own threads/tasks.
- **On-demand plane**: things triggered rarely — you opening the dashboard, the
  nightly backup, a manual `/reindex`.

---

## 5. How a request travels (summary)

The full trace is in [WORKFLOW.md](WORKFLOW.md). The short version:

```mermaid
sequenceDiagram
    participant You
    participant TG as Telegram
    participant W as Worker+DO
    participant BR as Bridge (Mac)
    participant BOT as Bot Layer
    participant AG as Agent
    participant AI as Groq/Gemini
    participant T as Tools

    You->>TG: "find my resume"
    TG->>W: webhook POST
    W->>BR: hands to waiting long-poll
    BR->>BOT: feed update
    BOT->>BOT: auth check ✓, show "typing…"
    BOT->>AG: run(chat_id, text)
    AG->>AI: here's the message + list of tools
    AI-->>AG: call search_files("resume")
    AG->>T: FileSearch.search("resume")
    T-->>AG: ranked results
    AG->>AI: here are the results
    AI-->>AG: call send_file(path) + text answer
    AG->>T: attach file
    AG-->>BOT: reply text + file
    BOT->>BR: send message + document
    BR->>W: (reply goes via Telegram API directly)
    BOT->>TG: sendDocument
    TG->>You: 📎 resume.pdf
```

---

## 6. Design decisions (and why)

These are the choices that shape the whole system. Understanding *why* helps you
avoid "fixing" things that are intentional.

| Decision | Why | Alternative rejected |
|---|---|---|
| **No LangChain** | The agent needs one thing — a tool loop — which is ~50 lines against the raw LLM API. Fewer dependencies, full control over streaming. | LangChain (heavy, leaky abstractions, breaks on version bumps) |
| **Mac long-polls the cloud** (no tunnel) | Outbound connections always work behind any router. Tunnels (`cloudflared` quick tunnels) die silently and are throttled. | cloudflared quick tunnel (unreliable — see git history) |
| **Groq primary, Gemini fallback** | Groq's free tier is far more generous; keeps Gemini's small quota in reserve. Both are free. | Gemini-only (hits daily cap fast) |
| **SQLite, not Postgres** | One user, one machine. SQLite is zero-setup, a single file, and plenty fast. | Postgres (needs a server, overkill) |
| **ChromaDB, not FAISS** | Chroma persists to disk automatically and handles metadata. FAISS is faster but you'd hand-roll persistence. | FAISS (more setup for no real gain here) |
| **Everything lazy-loaded** | The heavy libraries (embeddings, Whisper, Chroma) load only when first used, so the app boots instantly and runs even if one is missing. | Eager imports (slow boot, one missing dep kills everything) |
| **Allowlist for commands** | The AI can *never* run arbitrary shell — only a fixed menu of safe actions. | Letting the LLM run raw commands (dangerous) |

See [ROADMAP.md](ROADMAP.md) for an honest critique of these choices.

---

## 7. Project dependency map (Part 13)

This shows **which module imports/uses which**. Arrows mean "depends on / calls."

```mermaid
flowchart TD
    main[main.py<br/>🔴 wires everything] --> config[config.py]
    main --> db[db/database.py]
    main --> vs[search/vector_store.py]
    main --> idx[search/indexer.py]
    main --> fs[search/file_search.py]
    main --> llm[core/llm.py]
    main --> agent[core/agent.py]
    main --> voice[core/voice.py]
    main --> bot[bot/telegram_bot.py]
    main --> bridge[bot/bridge.py]
    main --> sched[core/scheduler.py]
    main --> dash[dashboard/api.py]

    agent --> llm
    agent --> fs
    agent --> tools_lc[tools/local_commands.py]
    agent --> tools_ws[tools/web_search.py]
    agent --> tools_wx[tools/weather.py]
    agent --> tools_ss[tools/system_status.py]
    agent --> db
    agent --> extract[search/extractors.py]

    fs --> db
    fs --> vs
    idx --> db
    idx --> vs
    idx --> extract
    bot --> agent
    bot --> voice
    bot --> idx
    bot --> db
    bot --> tools_ss
    bridge --> bot
    sched --> db
    dash --> db
    dash --> vs
    dash --> idx

    everything[every module] --> utils[utils/logging.py]

    style main fill:#8b0000,color:#fff
    style config fill:#1a5c1a,color:#fff
    style utils fill:#1a5c1a,color:#fff
```

**How to read it:** `main.py` is the wiring hub (red = touch carefully). Everything
depends on `config.py` and `utils/logging.py` (green = stable, safe). The `agent`
is the busiest node — it pulls in the LLM and all the tools. `db/database.py` is
the shared foundation used by almost everyone.

**The golden rule of the dependency graph:** dependencies flow *downward and
inward*. `bot` uses `agent`; `agent` uses `tools` and `llm`; `tools` use `db`.
Nothing lower-level ever imports something higher-level (e.g., `db` never imports
`agent`). This keeps the system layered and testable. If you ever find yourself
wanting `database.py` to import `agent.py`, stop — you're about to create a
circular dependency, and the design is telling you the logic belongs elsewhere.

---

## 8. What runs where (process/thread model)

```mermaid
flowchart TB
    subgraph proc["Single Python process (launchd keeps it alive)"]
        subgraph loop["One asyncio event loop"]
            e1[Telegram bot handlers]
            e2[Bridge long-poll task]
            e3[Scheduler tasks: reminders, monitor, backup]
            e4[Dashboard uvicorn server]
        end
        subgraph threads["Background threads"]
            t1[Indexer scanner thread]
            t2[Indexer worker thread]
            t3[Watchdog observer thread]
        end
    end
```

- **One event loop** runs the bot, the bridge, the scheduler, and the dashboard
  concurrently (async = they take turns without blocking each other).
- **Blocking work** (reading a PDF, computing an embedding, running `tesseract`)
  is pushed to **threads** via `run_in_executor`, so it never freezes the loop.
- The **indexer** and **watchdog** run in their own threads because file scanning
  is heavy and long-running.

This is why Kukku can answer your message *while* it's indexing 3,000 files in
the background — they're on different execution tracks.

---

Next: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) explains every file, or jump to
[WORKFLOW.md](WORKFLOW.md) to trace a real message.
