# Installation Guide

## Prerequisites

- macOS (tested on Apple Silicon), Python 3.12+
- A Telegram bot token — talk to [@BotFather](https://t.me/BotFather) → `/newbot`
- **One** LLM key — a **free** Gemini key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey), no card) or Groq is recommended; Anthropic (paid) and local Ollama also work
- Optional: `brew install tesseract` (OCR), `brew install ffmpeg` (voice notes)

## 1. Install

```bash
cd ~/Kukku
./scripts/start.sh
```

The first run creates `.venv`, installs dependencies (a few minutes — it pulls
PyTorch for the embedding model), copies `.env.example` → `.env`, and exits so
you can configure it.

## 2. Configure `.env`

| Variable | What it is |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `ALLOWED_USER_IDS` | Your numeric Telegram ID(s), comma-separated. **Leave empty on first run** — message the bot and it will tell you your ID. |
| `GEMINI_API_KEY` | **Free** — https://aistudio.google.com/apikey, no credit card. Recommended free option. |
| `GROQ_API_KEY` | **Free** — https://console.groq.com. Fast Llama 3.3 70B. |
| `OLLAMA_MODEL` | **Free + offline** — `brew install ollama && ollama pull llama3.1`, then set `llama3.1`. Needs ~5 GB RAM. |
| `ANTHROPIC_API_KEY` | Claude (paid, best quality) |
| `OPENROUTER_API_KEY` | OpenRouter (has `:free` models) |

Only **one** LLM variable is needed. Priority order if several are set: Claude → Gemini → Groq → OpenRouter → Ollama. All providers get **full tool use** (file search, file delivery, local commands).
| `INDEX_DIRS` | Folders to index, relative to `$HOME` or absolute |
| `ENABLE_OCR` / `ENABLE_VOICE` | Feature toggles |
| `WHISPER_MODEL` | `tiny`/`base`/`small` — bigger = better transcription, slower |
| `DASHBOARD_PORT` | Default `8788` |

## 3. First run

```bash
./scripts/start.sh
```

- Message your bot on Telegram → it replies with your user ID → paste it into
  `ALLOWED_USER_IDS` → restart.
- The first full index runs in the background; semantic search gets better as
  it fills. Watch progress in the dashboard (`./scripts/web.sh` → http://localhost:3000).
- The first embedding model + whisper model downloads happen on first use.

## 4. Run 24/7 with launchd

```bash
cp scripts/com.manish.jarvis.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.manish.jarvis.plist
# stop with: launchctl unload ~/Library/LaunchAgents/com.manish.jarvis.plist
```

Logs: `data/logs/jarvis.log` (app) and `data/logs/launchd.*.log` (supervisor).

> **macOS permissions:** the first time Kukku scans Desktop/Documents/Downloads,
> macOS will ask to grant file access to your terminal (or to `python`). For
> `lock_screen`/`sleep`/`shutdown` you may need to allow Accessibility /
> Automation access in System Settings → Privacy & Security.

## 5. Always-online cloud relay (optional, free)

Answers general questions even when the Mac is off/asleep.

1. Create a free Cloudflare account (email only): https://dash.cloudflare.com/sign-up
2. `./scripts/setup_cloud.sh` — logs into Cloudflare (browser opens), deploys
   the Worker, sets secrets, points the Telegram webhook at it, restarts Kukku.
3. Done. Disable anytime: `./scripts/disable_cloud.sh`.

## 6. Docker (optional)

```bash
docker compose up -d --build
```

Caveats on macOS: the container cannot open apps, lock the screen, or shut the
Mac down, and it only indexes the folders mounted in `docker-compose.yml`.
Use launchd for the full experience.

## Troubleshooting

- **"Not configured yet" reply** → put your ID in `ALLOWED_USER_IDS` and restart.
- **Semantic search says unavailable** → check `data/logs/jarvis.log` for the
  chromadb/sentence-transformers import error; `pip install -r requirements.txt`.
- **OCR errors** → `brew install tesseract`.
- **Voice notes fail** → `brew install ffmpeg`; first transcription downloads the model.
- **Bot doesn't answer** → only one process may poll a bot token; make sure a
  second instance isn't running (`ps aux | grep app.main`).
