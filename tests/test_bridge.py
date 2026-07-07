"""Tests for the long-poll cloud bridge (Mac pulls updates from the relay)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.bot.bridge import CloudBridge
from app.config import Settings

UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 5, "date": 1,
        "chat": {"id": 681392979, "type": "private"},
        "from": {"id": 681392979, "is_bot": False, "first_name": "M"},
        "text": "hello",
    },
}


@pytest.fixture()
def ptb():
    app = MagicMock()
    app.update_queue.put = AsyncMock()
    app.bot = None  # Update.de_json tolerates None; a MagicMock breaks tz handling
    return app


def _bridge(ptb, handler) -> CloudBridge:
    settings = Settings(worker_url="https://relay.example.workers.dev", bridge_secret="s3cret")
    return CloudBridge(settings, ptb, transport=httpx.MockTransport(handler))


def test_poll_delivers_updates_to_ptb(ptb):
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        seen["secret"] = req.headers.get("x-bridge-secret")
        return httpx.Response(200, json={"updates": [UPDATE]})

    bridge = _bridge(ptb, handler)

    async def run():
        async with httpx.AsyncClient(transport=bridge._transport) as c:
            await bridge._poll_once(c)

    asyncio.run(run())
    assert seen["path"] == "/pull"
    assert seen["secret"] == "s3cret"
    assert bridge.connected is True
    ptb.update_queue.put.assert_awaited_once()
    assert ptb.update_queue.put.await_args.args[0].message.text == "hello"


def test_poll_empty_updates_marks_connected_no_dispatch(ptb):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"updates": []})

    bridge = _bridge(ptb, handler)

    async def run():
        async with httpx.AsyncClient(transport=bridge._transport) as c:
            await bridge._poll_once(c)

    asyncio.run(run())
    assert bridge.connected is True
    ptb.update_queue.put.assert_not_awaited()


def test_poll_error_propagates_for_reconnect(ptb):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    bridge = _bridge(ptb, handler)

    async def run():
        async with httpx.AsyncClient(transport=bridge._transport) as c:
            await bridge._poll_once(c)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(run())
    assert bridge.connected is False


def test_poll_loop_reconnects_after_error(ptb, monkeypatch):
    """First poll raises (triggering backoff), second succeeds; loop then stops."""
    bridge = _bridge(ptb, lambda req: httpx.Response(200, json={"updates": []}))
    calls = {"n": 0}

    async def fake_poll_once(_client):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom")
        bridge._stop.set()  # clean exit after a successful reconnect

    monkeypatch.setattr(bridge, "_poll_once", fake_poll_once)
    # loop self-terminates once stop is set (after the ~1s backoff wait)
    asyncio.run(asyncio.wait_for(bridge._poll_loop(), timeout=5))
    assert calls["n"] == 2  # errored once, retried, succeeded
