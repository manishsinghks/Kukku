"""Proactive background jobs — all zero LLM cost:

  • reminders  — fire due one-time / daily reminders over Telegram
  • monitor    — battery / disk alerts with hysteresis (no spam)
  • backup     — daily consistent copy of the SQLite DB

Runs as asyncio tasks in the bot's event loop. Delivery is a `send(chat_id, text)`
coroutine supplied by the caller (the Telegram bot).
"""
from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import psutil

from app.config import Settings
from app.db.database import Database
from app.utils.logging import get_logger

log = get_logger(__name__)

Send = Callable[[int, str], Awaitable[None]]


def next_daily_ts(daily_time: str, now: float | None = None) -> float:
    """Epoch of the next HH:MM in local time (today if still ahead, else tomorrow)."""
    now = now or time.time()
    hh, mm = (int(x) for x in daily_time.split(":"))
    base = datetime.fromtimestamp(now)
    target = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target.timestamp() <= now:
        target += timedelta(days=1)
    return target.timestamp()


class Scheduler:
    def __init__(self, settings: Settings, db: Database, send: Send):
        self.settings = settings
        self.db = db
        self.send = send
        self._stop = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._alert_active: dict[str, bool] = {}  # hysteresis state per alert
        self._last_backup_day: str | None = None

    # -- reminders -----------------------------------------------------------
    async def _reminder_loop(self) -> None:
        while not self._stop.is_set():
            try:
                for r in self.db.due_reminders(time.time()):
                    await self.send(r["chat_id"], f"⏰ Reminder: {r['text']}")
                    if r["recurrence"] == "daily" and r["daily_time"]:
                        self.db.reschedule_reminder(r["id"], next_daily_ts(r["daily_time"]))
                    else:
                        self.db.deactivate_reminder(r["id"])
            except Exception:  # noqa: BLE001
                log.exception("reminder loop error")
            await self._sleep(30)

    # -- system monitor ------------------------------------------------------
    async def _monitor_loop(self) -> None:
        chat_id = self.settings.owner_chat_id
        if chat_id is None:
            return
        while not self._stop.is_set():
            try:
                await self._check_battery(chat_id)
                await self._check_disk(chat_id)
            except Exception:  # noqa: BLE001
                log.exception("monitor loop error")
            await self._sleep(self.settings.monitor_interval_min * 60)

    async def _check_battery(self, chat_id: int) -> None:
        batt = psutil.sensors_battery()
        if batt is None:  # desktop / no battery
            return
        low = batt.percent <= self.settings.alert_battery_pct and not batt.power_plugged
        if low and not self._alert_active.get("battery"):
            self._alert_active["battery"] = True
            await self.send(chat_id, f"🔋 Battery low: {int(batt.percent)}% and not charging — plug in soon.")
        elif self._alert_active.get("battery") and (batt.power_plugged or batt.percent > self.settings.alert_battery_pct + 10):
            self._alert_active["battery"] = False  # recovered (hysteresis)

    async def _check_disk(self, chat_id: int) -> None:
        pct = psutil.disk_usage("/").percent
        high = pct >= self.settings.alert_disk_pct
        if high and not self._alert_active.get("disk"):
            self._alert_active["disk"] = True
            free_gb = round(psutil.disk_usage("/").free / 1e9, 1)
            await self.send(chat_id, f"💽 Disk almost full: {pct:.0f}% used ({free_gb} GB free).")
        elif self._alert_active.get("disk") and pct < self.settings.alert_disk_pct - 5:
            self._alert_active["disk"] = False

    # -- backup --------------------------------------------------------------
    async def _backup_loop(self) -> None:
        if not self.settings.backup_enabled:
            return
        while not self._stop.is_set():
            try:
                self._maybe_backup()
            except Exception:  # noqa: BLE001
                log.exception("backup error")
            await self._sleep(3600)  # check hourly, acts once/day

    def _maybe_backup(self) -> None:
        today = datetime.now().strftime("%Y%m%d")
        if today == self._last_backup_day:
            return
        self.settings.backup_dir.mkdir(parents=True, exist_ok=True)
        dest = self.settings.backup_dir / f"jarvis-{today}.db"
        self.db.backup(dest)
        self._last_backup_day = today
        log.info("DB backup written: %s", dest)
        # rotate: keep the newest N
        backups = sorted(self.settings.backup_dir.glob("jarvis-*.db"))
        for old in backups[: -self.settings.backup_keep]:
            with contextlib.suppress(OSError):
                old.unlink()

    # -- lifecycle -----------------------------------------------------------
    async def _sleep(self, seconds: float) -> None:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._reminder_loop()),
            asyncio.create_task(self._monitor_loop()),
            asyncio.create_task(self._backup_loop()),
        ]
        log.info("Scheduler started (reminders, monitor, backup)")

    async def stop(self) -> None:
        self._stop.set()
        for t in self._tasks:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await t
