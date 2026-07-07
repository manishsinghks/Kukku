"""Tests for the dashboard chat/realtime/memory/search API + the event bus."""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.agent import AgentReply
from app.core.events import EVENTS, EventBus
from app.dashboard.chat_api import build_chat_router


# -- event bus --------------------------------------------------------------
def test_event_bus_fanout():
    async def run():
        bus = EventBus()
        q1, q2 = bus.subscribe(), bus.subscribe()
        assert bus.subscriber_count == 2
        bus.publish({"type": "message", "content": "hi"})
        assert (await q1.get())["content"] == "hi"
        assert (await q2.get())["content"] == "hi"
        bus.unsubscribe(q1)
        assert bus.subscriber_count == 1
    asyncio.run(run())


def test_event_bus_drops_on_full():
    bus = EventBus()
    q = bus.subscribe()
    for i in range(500):
        bus.publish({"n": i})  # queue maxsize=200 → excess dropped, no crash
    assert q.qsize() <= 200


# -- API --------------------------------------------------------------------
class FakeAgent:
    async def run(self, chat_id, text, on_text=None, source="telegram"):
        if on_text:
            await on_text("Hel")
            await on_text("Hello!")
        # mimic the real agent writing to the DB + broadcasting
        self.db.add_message(chat_id, "user", text)
        self.db.add_message(chat_id, "assistant", "Hello!")
        EVENTS.publish({"type": "message", "role": "assistant", "content": "Hello!",
                        "source": source})
        return AgentReply(text="Hello!")


class FakeSearch:
    def search(self, q, limit=12):
        return []


class FakeService:
    def verify_access(self, token):
        if token != "good":
            from app.auth.service import AuthError
            raise AuthError("bad")
        return "manish"


@pytest.fixture()
def client(db):
    settings = Settings(allowed_user_ids="42")
    agent = FakeAgent()
    agent.db = db

    def require_user():  # stub dependency: always authenticated
        return "manish"

    router = build_chat_router(settings, db, agent, FakeSearch(), require_user, FakeService())
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), db


def test_chat_streams_tokens_and_done(client):
    c, _ = client
    r = c.post("/api/chat", json={"message": "hi"})
    assert r.status_code == 200
    events = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]
    types = [e["type"] for e in events]
    assert "token" in types and types[-1] == "done"
    done = events[-1]
    assert done["text"] == "Hello!" and "latency_ms" in done


def test_chat_history_and_clear(client):
    c, db = client
    c.post("/api/chat", json={"message": "hi"})
    hist = c.get("/api/chat/history").json()
    assert hist["chat_id"] == 42
    assert any(m["content"] == "hi" for m in hist["messages"])
    c.post("/api/chat/clear")
    assert c.get("/api/chat/history").json()["messages"] == []


def test_chat_empty_message_rejected(client):
    c, _ = client
    assert c.post("/api/chat", json={"message": "  "}).status_code == 400


def test_memory_add_delete_export(client):
    c, _ = client
    mid = c.post("/api/memory", json={"content": "likes dark mode"}).json()["id"]
    exp = c.get("/api/memory/export").json()
    assert any(m["content"] == "likes dark mode" for m in exp["memories"])
    assert c.request("DELETE", f"/api/memory/{mid}").status_code == 200
    exp2 = c.get("/api/memory/export").json()
    assert not any(m["id"] == mid for m in exp2["memories"])


def test_search_endpoint(client):
    c, db = client
    db.add_memory("docker notes")
    res = c.get("/api/search", params={"q": "docker"}).json()
    assert res["query"] == "docker"
    assert any("docker" in m["content"] for m in res["memories"])


def test_events_requires_valid_token(client):
    c, _ = client
    # bad token → 401
    assert c.get("/api/events", params={"token": "bad"}).status_code == 401
