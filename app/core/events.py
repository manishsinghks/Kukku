"""In-process event bus for realtime sync between clients.

Every conversation message (from Telegram OR the web dashboard) is published
here. Web dashboard clients subscribe via an SSE stream (/api/events) and update
live — so a Telegram message appears on the dashboard instantly, and vice versa.

This is the "one source of truth" for realtime: the Agent publishes once, and
every connected client hears it, regardless of which client caused it.
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from app.utils.logging import get_logger

log = get_logger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, event: dict[str, Any]) -> None:
        """Fan out an event to every subscriber. Non-blocking; drops on a full
        (slow) consumer so one stuck client can't stall the others."""
        for q in list(self._subscribers):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(event)


# module-level singleton — the shared realtime bus
EVENTS = EventBus()
