"""The agent: a tool-use loop that lets the LLM search files, read them (RAG),
send files, run allowlisted local commands, search the web, and use memory.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.core.events import EVENTS
from app.core.llm import METRICS, LLMTurn, OnText
from app.db.database import Database
from app.search.file_search import FileSearch
from app.tools import local_commands, system_status, web_search
from app.utils.logging import get_logger

log = get_logger(__name__)

MAX_TOOL_ROUNDS = 8
HISTORY_LIMIT = 24

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_files",
        "description": (
            "Search the user's laptop (Desktop, Documents, Downloads, Projects, Pictures...) "
            "by filename and semantic content similarity. Use for any question about the "
            "user's files, projects, notes, screenshots, or documents. Returns ranked matches "
            "with paths and content snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for (natural language is fine)"},
                "search_type": {"type": "string", "enum": ["filename", "semantic", "all"], "default": "all"},
                "file_type": {"type": "string", "enum": ["document", "code", "image", "data", "other"],
                              "description": "Optional filter, e.g. 'image' for screenshots"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the text content of a specific file on the laptop (for answering questions about it).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "default": 6000},
            },
            "required": ["path"],
        },
    },
    {
        "name": "send_file",
        "description": "Send a file from the laptop to the user on Telegram. Use after finding the right file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "run_local_command",
        "description": (
            "Run an allowlisted local command on the Mac. Actions: open_vscode, open_chrome, "
            "open_folder, open_file, open_app, read_clipboard, copy_to_clipboard, "
            "lock_screen, sleep, shutdown, restart. "
            "shutdown/restart require confirmed=true, which you may only set after the user "
            "explicitly confirms in a follow-up message."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "target": {"type": "string", "description": "Path, URL, or app name depending on action"},
                "confirmed": {"type": "boolean", "default": False},
            },
            "required": ["action"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the internet. Use when local knowledge and the user's files can't answer.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "save_memory",
        "description": "Persist an important note the user wants remembered (preferences, facts, reminders).",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
    {
        "name": "set_alias",
        "description": "Remember a shortcut name for a path/URL/thing, e.g. 'my resume' -> /Users/x/Documents/resume.pdf",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
            "required": ["name", "value"],
        },
    },
    {
        "name": "system_status",
        "description": "Get laptop CPU / RAM / disk usage.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_weather",
        "description": "Current weather + today's high/low for a city (free, no key).",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
    {
        "name": "set_reminder",
        "description": (
            "Schedule a reminder that the bot will push to the user at the right time. "
            "Compute the time from the CURRENT LOCAL TIME given in the system prompt. "
            "For a one-time reminder pass `when` as local ISO 'YYYY-MM-DDTHH:MM'. "
            "For a repeating daily reminder pass `daily_time` as 'HH:MM' (24h) instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "What to remind about"},
                "when": {"type": "string", "description": "One-time: local ISO 'YYYY-MM-DDTHH:MM'"},
                "daily_time": {"type": "string", "description": "Daily repeat: 'HH:MM' (24h)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "list_reminders",
        "description": "List the user's active reminders.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "cancel_reminder",
        "description": "Cancel a reminder by its id (from list_reminders).",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
]


@dataclass
class AgentReply:
    text: str
    files_to_send: list[Path] = field(default_factory=list)


class Agent:
    def __init__(self, settings: Settings, db: Database, search: FileSearch, provider: Any):
        self.settings = settings
        self.db = db
        self.search = search
        self.provider = provider

    # -- prompt ---------------------------------------------------------------
    def _system_prompt(self) -> str:
        memories = self.db.list_memories(limit=30)
        aliases = self.db.list_aliases()
        mem_block = "\n".join(f"- {m['content']}" for m in memories) or "(none yet)"
        alias_block = "\n".join(f"- {a['name']} -> {a['value']}" for a in aliases) or "(none yet)"
        dirs = ", ".join(str(p) for p in self.settings.index_paths)
        return f"""You are Kukku, {Path.home().name}'s personal assistant running on their Mac, chatting over Telegram.

Capabilities via tools: search the laptop's files (filename + semantic), read files, send files to Telegram, run allowlisted local commands, web search, memory.

Guidelines:
- Be concise — this is a chat app. Prefer short answers; use Telegram-friendly Markdown (bold, italic, `code`). No headers or tables.
- If a question might relate to the user's local files, notes, or projects, use search_files BEFORE answering from general knowledge.
- When the user asks for a file, search, pick the best match, and use send_file. If several plausible matches exist, list the top candidates briefly and ask which one.
- Use web_search only when local files and your knowledge can't answer (news, live data, niche facts).
- For shutdown/restart: first ask the user to confirm, and only call the tool with confirmed=true after they explicitly say yes.
- Use save_memory when the user tells you to remember something; use set_alias for shortcuts like "my resume".
- Language: always reply in the SAME language and script the user used.
  • Hindi in Devanagari (e.g. "मेरा resume भेजो") → reply in Hindi (Devanagari).
  • Hinglish / Romanized Hindi (e.g. "mera resume bhejo", "aaj ka weather batao") → reply in the same Hinglish/Roman style, not Devanagari.
  • English → English. Mixed → mirror the user's mix. Keep technical terms/filenames as-is.

Additional tools: get_weather, set_reminder / list_reminders / cancel_reminder (the bot pushes reminders to the user at the scheduled time — compute times from the current local time below).

Indexed directories: {dirs}
Current local time: {time.strftime('%Y-%m-%d %H:%M %A')}

Saved memories:
{mem_block}

Aliases:
{alias_block}"""

    def _set_reminder(self, args: dict[str, Any], chat_id: int) -> str:
        from app.core.scheduler import next_daily_ts

        text = (args.get("text") or "").strip()
        if not text:
            return "Reminder text is required."
        if not chat_id:
            return "Cannot set a reminder without a chat context."
        if args.get("daily_time"):
            dt = args["daily_time"]
            due = next_daily_ts(dt)
            self.db.add_reminder(chat_id, text, due, "daily", dt)
            return f"OK — I'll remind you daily at {dt}: {text}"
        when = args.get("when")
        if not when:
            return "Provide either `when` (one-time) or `daily_time` (daily)."
        try:
            target = datetime.fromisoformat(when)
            due = target.timestamp()
        except ValueError:
            return f"Couldn't parse time {when!r}; use 'YYYY-MM-DDTHH:MM'."
        if due <= time.time():
            return "That time is in the past — pick a future time."
        self.db.add_reminder(chat_id, text, due, "once")
        return f"OK — reminder set for {target.strftime('%a %d %b, %H:%M')}: {text}"

    # -- tool dispatch ---------------------------------------------------------
    async def _run_tool(
        self, name: str, args: dict[str, Any], reply: AgentReply, chat_id: int = 0
    ) -> str:
        loop = asyncio.get_running_loop()
        try:
            if name == "search_files":
                results = await loop.run_in_executor(
                    None,
                    lambda: self.search.search(
                        args["query"],
                        args.get("search_type", "all"),
                        limit=8,
                        file_type=args.get("file_type"),
                    ),
                )
                if not results:
                    return "No matching files found."
                return json.dumps([r.to_dict() for r in results], ensure_ascii=False)

            if name == "read_file":
                p = Path(args["path"]).expanduser()
                if not p.exists() or not p.is_file():
                    return f"File not found: {p}"
                from app.search.extractors import ExtractionError, extract_text
                try:
                    text = await loop.run_in_executor(
                        None, lambda: extract_text(p, ocr_enabled=self.settings.enable_ocr)
                    )
                except ExtractionError as e:
                    return f"Could not extract text: {e}"
                return text[: int(args.get("max_chars", 6000))] or "(file is empty)"

            if name == "send_file":
                p = Path(args["path"]).expanduser()
                if not p.exists() or not p.is_file():
                    return f"File not found: {p}"
                if p.stat().st_size > 49 * 1024 * 1024:
                    return "File is larger than Telegram's 50 MB bot limit."
                reply.files_to_send.append(p)
                return f"OK — {p.name} will be attached to your reply."

            if name == "run_local_command":
                res = await loop.run_in_executor(
                    None,
                    lambda: local_commands.execute(
                        args["action"], args.get("target", ""), bool(args.get("confirmed"))
                    ),
                )
                if res.needs_confirmation:
                    return "BLOCKED: ask the user to explicitly confirm this destructive action first."
                return ("OK: " if res.ok else "FAILED: ") + res.message

            if name == "web_search":
                hits = await loop.run_in_executor(
                    None,
                    lambda: web_search.web_search(
                        args["query"],
                        gemini_api_key=self.settings.gemini_api_key,
                        gemini_model=self.settings.gemini_model,
                    ),
                )
                return json.dumps(hits, ensure_ascii=False) if hits else "Web search returned nothing."

            if name == "save_memory":
                self.db.add_memory(args["content"])
                return "Saved."

            if name == "set_alias":
                self.db.set_alias(args["name"], args["value"])
                return "Alias saved."

            if name == "system_status":
                status = await loop.run_in_executor(None, system_status.system_status)
                return json.dumps(status)

            if name == "get_weather":
                from app.tools.weather import get_weather
                data = await loop.run_in_executor(None, lambda: get_weather(args["city"]))
                return json.dumps(data, ensure_ascii=False)

            if name == "set_reminder":
                return self._set_reminder(args, chat_id)

            if name == "list_reminders":
                rows = self.db.list_reminders(chat_id)
                if not rows:
                    return "No active reminders."
                return json.dumps([
                    {"id": r["id"], "text": r["text"],
                     "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(r["due_ts"])),
                     "repeat": r["recurrence"]}
                    for r in rows
                ], ensure_ascii=False)

            if name == "cancel_reminder":
                ok = self.db.deactivate_reminder(int(args["id"]), chat_id)
                return "Reminder cancelled." if ok else "No such active reminder."

            return f"Unknown tool {name}"
        except Exception as e:  # noqa: BLE001 — report tool failure to the model
            log.exception("tool %s failed", name)
            return f"Tool error: {type(e).__name__}: {e}"

    # -- main entry -------------------------------------------------------------
    async def run(
        self, chat_id: int, user_text: str, on_text: OnText | None = None,
        source: str = "telegram",
    ) -> AgentReply:
        started = time.time()
        history = self.db.recent_messages(chat_id, limit=HISTORY_LIMIT)
        messages: list[dict[str, Any]] = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]
        messages.append({"role": "user", "content": user_text})

        reply = AgentReply(text="")
        turn: LLMTurn | None = None
        for _round in range(MAX_TOOL_ROUNDS):
            turn = await self.provider.turn(
                system=self._system_prompt(),
                messages=messages,
                tools=TOOLS,
                on_text=on_text,
            )
            if turn.stop_reason != "tool_use" or not turn.tool_calls:
                break
            messages.append({"role": "assistant", "content": turn.raw_content})
            results = []
            for call in turn.tool_calls:
                log.info("tool call: %s(%s)", call["name"], json.dumps(call["input"])[:300])
                output = await self._run_tool(call["name"], call["input"], reply, chat_id)
                results.append(
                    {"type": "tool_result", "tool_use_id": call["id"], "content": output[:20000]}
                )
            messages.append({"role": "user", "content": results})
        else:
            log.warning("hit MAX_TOOL_ROUNDS for chat %s", chat_id)

        reply.text = (turn.text if turn else "").strip() or "Done."
        self.db.add_message(chat_id, "user", user_text)
        self.db.add_message(chat_id, "assistant", reply.text)
        self.db.log_request(
            chat_id, "text", user_text, reply.text[:300],
            duration_ms=int((time.time() - started) * 1000),
        )
        # broadcast to any live clients (dashboard) so Telegram ↔ web stay synced
        now = time.time()
        EVENTS.publish({"type": "message", "chat_id": chat_id, "role": "user",
                        "content": user_text, "ts": now, "source": source})
        EVENTS.publish({"type": "message", "chat_id": chat_id, "role": "assistant",
                        "content": reply.text, "ts": now, "source": source,
                        "provider": METRICS.active,
                        "latency_ms": int((now - started) * 1000)})
        return reply
