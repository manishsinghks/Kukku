# Recovery Guide

## Restart / stop / start
```bash
launchctl kickstart -k gui/$(id -u)/com.manish.jarvis     # restart
launchctl unload ~/Library/LaunchAgents/com.manish.jarvis.plist  # stop
launchctl load   ~/Library/LaunchAgents/com.manish.jarvis.plist  # start
./scripts/start.sh                                        # foreground (debugging)
```

## Logs
- App: `data/logs/jarvis.log` (rotating, 5×5 MB)
- Supervisor: `data/logs/launchd.{out,err}.log`
- Request/audit trail: dashboard → Logs tab (SQLite `request_log`)

## Rebuild the search index from scratch
```bash
launchctl unload ~/Library/LaunchAgents/com.manish.jarvis.plist
rm -rf data/chroma && sqlite3 data/jarvis.db "DELETE FROM indexed_files;"
launchctl load ~/Library/LaunchAgents/com.manish.jarvis.plist   # full rescan starts
```
Conversation history, memories, and logs are untouched.

## Reset everything (nuclear)
```bash
launchctl unload ~/Library/LaunchAgents/com.manish.jarvis.plist
rm -rf data/            # index + DB + logs + inbox — memories included!
launchctl load ~/Library/LaunchAgents/com.manish.jarvis.plist
```

## Cloud relay (long-poll, no tunnel)
```bash
./scripts/disable_cloud.sh    # back to plain polling (Mac-only mode)
./scripts/setup_cloud.sh      # re-enable / redeploy / rotate webhook secret
cd cloud && npx -y wrangler@3 deploy   # redeploy worker + Durable Object
cd cloud && npx -y wrangler@3 tail     # live worker logs
```
The Mac connects outbound (long-poll) — no tunnel to fix. If the bot goes quiet
while the Mac is on, a `launchctl kickstart -k gui/$(id -u)/com.manish.jarvis`
reconnects it.

## Rotate credentials
| Credential | Where to rotate | Then |
|---|---|---|
| Telegram bot token | @BotFather → /revoke | update `.env`, rerun `setup_cloud.sh` |
| Gemini key | aistudio.google.com/apikey | update `.env`, `cd cloud && printf '%s' NEWKEY \| npx -y wrangler@3 secret put GEMINI_API_KEY`, restart |
| Groq key | console.groq.com | same as Gemini with `GROQ_API_KEY` |

## Backups worth taking
`data/jarvis.db` (memories, aliases, history, audit log) and `.env`.
Everything else is rebuildable (index, models re-download).

## Move to a new Mac
1. Copy the repo + `.env` + optionally `data/jarvis.db`.
2. `./scripts/start.sh` (rebuilds venv), install `tesseract`/`ffmpeg` via brew.
3. `cp scripts/com.manish.jarvis.plist ~/Library/LaunchAgents/ && launchctl load …`
4. If using the relay: `./scripts/setup_cloud.sh` re-registers everything.
