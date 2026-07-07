# Glossary

Every technical term in this project, defined in plain language. Alphabetical.

**Agent** — The "brain" loop (`app/core/agent.py`) that sends your message to the
AI, runs whatever tools the AI requests, and returns the final answer.

**Alias** — A saved shortcut, e.g. "my resume" → a file path. Stored in the
`aliases` table, injected into the AI's prompt.

**API (Application Programming Interface)** — A defined way for programs to talk to
each other over HTTP. Kukku calls the Telegram API, Gemini API, etc.

**AppleScript** — Apple's scripting language for automating macOS apps. Used for
lock/shutdown (`osascript`).

**Async / asyncio** — Python's way of doing many things "at once" on one thread by
letting tasks pause (`await`) while waiting. Keeps the bot responsive.

**Backoff** — Waiting longer and longer between retries after failures, so you
don't hammer a failing service.

**Bridge** — `app/bot/bridge.py`. The Mac-side long-poll client that pulls messages
from the cloud Worker (outbound only, no tunnel).

**Chunk** — A ~1200-character piece of a file's text. Files are split into chunks
before embedding, so search can point at the relevant part.

**ChromaDB** — The vector database that stores embeddings and finds the nearest
ones. Lives in `data/chroma/`.

**Cloudflare Worker** — A small program running on Cloudflare's always-on servers.
Kukku's public "front door" for Telegram webhooks. See `cloud/worker.js`.

**Cloudflared** — Cloudflare's tunnel tool. *Removed* from Kukku (was unreliable);
replaced by long-poll + Durable Object.

**Cooldown** — A period during which a failed AI provider is skipped, so the next
messages go straight to the working one.

**Cosine similarity** — A math measure of how similar two embeddings are (the angle
between them). 1 = identical meaning, 0 = unrelated.

**Durable Object (DO)** — A special Cloudflare Worker that has memory and single
ownership. Used as the real-time "mailbox" (`RelayDO`) between Telegram and the Mac.

**Embedding** — A list of numbers (384 here) that represents the *meaning* of a
piece of text. Similar meanings → similar numbers.

**Environment variable** — A configuration value passed to the program from outside
the code, kept in `.env`.

**Event loop** — The engine that runs all the async tasks, giving each a turn.

**Failover** — Automatically switching to a backup AI provider when the primary
fails.

**FastAPI** — The Python web framework serving the dashboard.

**Hysteresis** — In alerts: only alert when crossing a threshold, and don't
re-alert until it recovers past a margin. Prevents spam.

**Indexer** — `app/search/indexer.py`. The background service that reads your files
and stores their searchable form.

**Lazy loading** — Loading a heavy library/model only the first time it's actually
needed, so startup is fast.

**launchd** — macOS's service manager. Keeps Kukku running 24/7 and restarts it if
it crashes.

**LLM (Large Language Model)** — The AI text model (Groq's Llama, Google's Gemini)
that understands language and decides what to do.

**Long-poll** — An HTTP request that the server holds open until it has something to
return (or a timeout). Lets the Mac get messages in real time without a tunnel.

**Markdown** — Lightweight text formatting (`**bold**`, `` `code` ``). Used for docs
and Telegram replies.

**OCR (Optical Character Recognition)** — Reading text out of an image. Done by
Tesseract.

**OpenAI-compatible API** — A common HTTP shape for chat APIs that Gemini, Groq,
OpenRouter, and Ollama all support, so one code path handles them all.

**Polling** — Repeatedly asking "anything new?" (the opposite of a webhook). Kukku
uses this in pure-local mode.

**Prompt (system prompt)** — The instructions given to the AI each turn (identity,
rules, your memories, current time).

**RAG (Retrieval-Augmented Generation)** — First *retrieve* relevant text (from your
files), then give it to the AI to *generate* a grounded answer.

**Rate limit** — A cap on how many API requests you can make in a period. Exceeding
it returns HTTP 429.

**Recency boost** — Ranking recently-modified files slightly higher in search.

**Scheduler** — `app/core/scheduler.py`. Fires reminders, checks battery/disk, backs
up the DB. Zero AI cost.

**Semantic search** — Searching by *meaning* rather than exact words, powered by
embeddings.

**Sentence Transformers** — The library providing the local embedding model
(`all-MiniLM-L6-v2`).

**SQLite** — A full SQL database in a single file (`data/jarvis.db`). No server
needed.

**Streaming** — Sending the AI's answer piece by piece as it's generated, editing
the Telegram message live.

**Tesseract** — The open-source OCR engine (installed via Homebrew).

**Tool calling (function calling)** — The AI responding with a request to run a
named function with arguments, instead of plain text. How the AI gets "hands".

**Token** — A chunk of text (roughly a word-piece) that LLMs process. Rate/usage
limits are often measured in tokens.

**Vector / vector database** — A vector is a list of numbers (an embedding). A
vector database (ChromaDB) stores them and finds the nearest ones fast.

**Watchdog** — A library that watches folders and fires events on file changes, so
the index updates live.

**WAL (Write-Ahead Logging)** — A SQLite mode letting reads and writes happen
concurrently.

**Webhook** — A URL you register so a service (Telegram) *pushes* events to you,
instead of you polling.

**Whisper** — OpenAI's speech-to-text model, run locally via `faster-whisper` for
voice notes.

**Wrangler** — Cloudflare's CLI for deploying Workers.
