"""Cloud-bridge (long-poll mode): receive Telegram updates via the Cloudflare relay.

The Mac makes only OUTBOUND requests — it long-polls the Worker's /pull endpoint.
There is no tunnel, no inbound exposure, and nothing that can silently die: if a
poll fails it simply reconnects. When the Mac isn't polling (off/asleep) the
Worker answers general questions itself.

Replaces the old cloudflared-tunnel bridge, which depended on account-less quick
tunnels that Cloudflare throttles and gives "no uptime guarantee".
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import httpx
from telegram import Update

from app.config import Settings
from app.utils.logging import get_logger

log = get_logger(__name__)

POLL_TIMEOUT = 30.0  # > the Worker's 20s long-poll hold


class CloudBridge:
    def __init__(
        self, settings: Settings, ptb_app: Any,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.ptb_app = ptb_app
        self._transport = transport  # injectable for tests
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self.connected = False

    @property
    def _pull_url(self) -> str:
        return f"{self.settings.worker_url.rstrip('/')}/pull"

    async def _handle_updates(self, updates: list[dict[str, Any]]) -> None:
        for data in updates:
            update = Update.de_json(data, self.ptb_app.bot)
            if update:
                await self.ptb_app.update_queue.put(update)

    async def _poll_once(self, client: httpx.AsyncClient) -> None:
        r = await client.post(
            self._pull_url, headers={"x-bridge-secret": self.settings.bridge_secret}
        )
        r.raise_for_status()
        updates = r.json().get("updates", [])
        if not self.connected:
            self.connected = True
            log.info("Cloud relay connected (long-poll, no tunnel)")
        if updates:
            await self._handle_updates(updates)

    async def _poll_loop(self) -> None:
        backoff = 1.0
        async with httpx.AsyncClient(timeout=POLL_TIMEOUT, transport=self._transport) as client:
            while not self._stop.is_set():
                try:
                    await self._poll_once(client)
                    backoff = 1.0
                except Exception as e:  # noqa: BLE001 — reconnect on any failure
                    self.connected = False
                    log.warning("relay poll failed (%s); reconnecting in %.0fs",
                                type(e).__name__, backoff)
                    with contextlib.suppress(asyncio.TimeoutError):
                        await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                    backoff = min(backoff * 2, 30.0)

    # -- lifecycle ------------------------------------------------------------
    async def start(self) -> None:
        self._task = asyncio.create_task(self._poll_loop())
        log.info("Cloud bridge active: long-polling %s", self._pull_url)

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
