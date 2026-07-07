"""Tests for the proactive scheduler: reminders, alerts, backup, time math."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from unittest.mock import MagicMock

from app.config import Settings
from app.core.scheduler import Scheduler, next_daily_ts


def test_next_daily_ts_future_today():
    now = datetime(2026, 7, 5, 8, 0, 0).timestamp()
    ts = next_daily_ts("09:30", now)
    assert datetime.fromtimestamp(ts).hour == 9
    assert ts > now and ts - now < 2 * 3600


def test_next_daily_ts_rolls_to_tomorrow():
    now = datetime(2026, 7, 5, 10, 0, 0).timestamp()
    ts = next_daily_ts("09:30", now)  # already past today
    assert datetime.fromtimestamp(ts).day == 6


def _scheduler(db, sent, **overrides):
    settings = Settings(allowed_user_ids="42", **overrides)
    return Scheduler(settings, db, sent), settings


def test_reminder_fires_and_deactivates(db):
    sent = []

    async def send(chat_id, text):
        sent.append((chat_id, text))

    sched, _ = _scheduler(db, send)
    db.add_reminder(42, "call mom", time.time() - 5, "once")

    async def run():
        # run one pass of the loop body manually
        for r in db.due_reminders(time.time()):
            await sched.send(r["chat_id"], f"⏰ Reminder: {r['text']}")
            db.deactivate_reminder(r["id"])

    asyncio.run(run())
    assert sent == [(42, "⏰ Reminder: call mom")]
    assert db.list_reminders(42) == []


def test_daily_reminder_reschedules(db):
    rid = db.add_reminder(42, "standup", time.time() - 5, "daily", "09:00")
    # simulate the loop's reschedule branch
    db.reschedule_reminder(rid, next_daily_ts("09:00"))
    r = db.list_reminders(42)[0]
    assert r["recurrence"] == "daily"
    assert r["due_ts"] > time.time()


def test_battery_alert_hysteresis(db):
    sent = []

    async def send(chat_id, text):
        sent.append(text)

    sched, _ = _scheduler(db, send, alert_battery_pct=20)

    def batt(pct, plugged):
        m = MagicMock()
        m.percent = pct
        m.power_plugged = plugged
        return m

    import app.core.scheduler as sc

    async def run():
        sc.psutil.sensors_battery = lambda: batt(15, False)
        await sched._check_battery(42)  # fires
        await sched._check_battery(42)  # already active -> no re-fire
        sc.psutil.sensors_battery = lambda: batt(80, True)
        await sched._check_battery(42)  # recovered
        sc.psutil.sensors_battery = lambda: batt(15, False)
        await sched._check_battery(42)  # fires again

    asyncio.run(run())
    assert len(sent) == 2  # one per low-battery episode, not per check


def test_backup_writes_and_rotates(db, tmp_path):
    sched, settings = _scheduler(db, MagicMock())
    settings.data_dir = tmp_path
    # seed 9 old backups; keep should trim to backup_keep (7) + today
    bdir = tmp_path / "backups"
    bdir.mkdir()
    for i in range(9):
        (bdir / f"jarvis-2026010{i}.db").write_bytes(b"x")
    sched._maybe_backup()
    remaining = sorted(bdir.glob("jarvis-*.db"))
    assert len(remaining) <= settings.backup_keep
    # today's real backup exists and is a valid sqlite file (non-empty)
    today = datetime.now().strftime("%Y%m%d")
    assert (bdir / f"jarvis-{today}.db").stat().st_size > 0
