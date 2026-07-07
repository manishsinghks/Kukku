"""Authenticated chat + realtime + memory + search API for the web dashboard.

Crucially, chat here runs the SAME `Agent` the Telegram bot uses, against the
SAME database and the SAME owner chat_id — so history and memory are identical
across clients. The /events SSE stream carries every message (from either client)
for live sync.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.service import AuthError, AuthService
from app.config import Settings
from app.core.agent import Agent
from app.core.events import EVENTS
from app.core.llm import METRICS
from app.db.database import Database
from app.search.file_search import FileSearch
from app.utils.logging import get_logger

log = get_logger(__name__)


class ChatBody(BaseModel):
    message: str


class MemoryBody(BaseModel):
    content: str


def _sse(obj: dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def build_chat_router(
    settings: Settings, db: Database, agent: Agent, search: FileSearch,
    require_user, service: AuthService,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["dashboard"])
    OWNER = settings.owner_chat_id or 0  # unified conversation id (== Telegram chat)

    # -- chat ----------------------------------------------------------------
    @router.get("/chat/history")
    def chat_history(limit: int = Query(80, le=500), _u: str = Depends(require_user)):
        return {"chat_id": OWNER, "messages": db.recent_messages(OWNER, limit)}

    @router.post("/chat/clear")
    def chat_clear(_u: str = Depends(require_user)):
        db.clear_history(OWNER)
        return {"ok": True}

    @router.post("/chat")
    async def chat(body: ChatBody, _u: str = Depends(require_user)):
        """Stream the assistant reply as SSE, using the shared agent."""
        text = body.message.strip()
        if not text:
            raise HTTPException(400, "empty message")
        started = time.time()

        async def event_stream():
            q: asyncio.Queue = asyncio.Queue()

            async def on_text(accumulated: str) -> None:
                await q.put({"type": "token", "text": accumulated})

            async def run_agent() -> None:
                try:
                    reply = await agent.run(OWNER, text, on_text=on_text, source="dashboard")
                    await q.put({
                        "type": "done", "text": reply.text,
                        "provider": METRICS.active,
                        "latency_ms": int((time.time() - started) * 1000),
                        "files": [str(p) for p in reply.files_to_send],
                    })
                except Exception as e:  # noqa: BLE001 — never leak a stack trace
                    log.exception("dashboard chat failed")
                    msg = str(e)
                    friendly = ("The free AI quota is catching its breath — try again in a minute."
                                if ("429" in msg or "rate limited" in msg.lower()) else
                                "Something went wrong. Please try again.")
                    await q.put({"type": "error", "message": friendly})
                finally:
                    await q.put(None)

            task = asyncio.create_task(run_agent())
            try:
                while True:
                    item = await q.get()
                    if item is None:
                        break
                    yield _sse(item)
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # -- realtime sync (SSE) -------------------------------------------------
    @router.get("/events")
    async def events(token: str = Query(...)):
        # EventSource can't send headers, so the access token comes as a query param
        try:
            service.verify_access(token)
        except AuthError as e:
            raise HTTPException(401, str(e)) from e

        async def stream():
            q = EVENTS.subscribe()
            try:
                yield _sse({"type": "connected"})
                while True:
                    try:
                        ev = await asyncio.wait_for(q.get(), timeout=25)
                        yield _sse(ev)
                    except TimeoutError:
                        yield _sse({"type": "ping"})  # keep the connection alive
            finally:
                EVENTS.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream")

    # -- memory CRUD ---------------------------------------------------------
    @router.get("/memory")
    def memory_list(_u: str = Depends(require_user)):
        return {"memories": db.list_memories(), "aliases": db.list_aliases()}

    @router.post("/memory")
    def memory_add(body: MemoryBody, _u: str = Depends(require_user)):
        content = body.content.strip()
        if not content:
            raise HTTPException(400, "empty memory")
        mid = db.add_memory(content)
        return {"id": mid, "content": content}

    @router.delete("/memory/{memory_id}")
    def memory_delete(memory_id: int, _u: str = Depends(require_user)):
        db.delete_memory(memory_id)
        return {"ok": True}

    @router.get("/memory/export")
    def memory_export(_u: str = Depends(require_user)):
        return {"memories": db.list_memories(limit=10000), "aliases": db.list_aliases()}

    # -- universal search ----------------------------------------------------
    @router.get("/search")
    def universal_search(
        q: str = Query(..., min_length=1),
        _u: str = Depends(require_user),
    ):
        files = [r.to_dict() for r in search.search(q, limit=12)]
        ql = q.lower()
        memories = [m for m in db.list_memories(limit=500) if ql in m["content"].lower()]
        aliases = [a for a in db.list_aliases() if ql in a["name"].lower() or ql in a["value"].lower()]
        return {"query": q, "files": files, "memories": memories[:10], "aliases": aliases[:10]}

    return router
