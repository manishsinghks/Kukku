"""Authenticated API for the remaining dashboard modules: Automation (reminders),
Files, OCR, Developer (activity/logs), Settings, Notifications.

Everything reads/writes the SAME database and settings the Telegram bot uses.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import Settings
from app.core.llm import METRICS
from app.core.scheduler import next_daily_ts
from app.db.database import Database
from app.search.file_search import FileSearch
from app.tools import local_commands
from app.utils.logging import get_logger

log = get_logger(__name__)


class ReminderBody(BaseModel):
    text: str
    when: str | None = None        # one-time: local ISO 'YYYY-MM-DDTHH:MM'
    daily_time: str | None = None  # daily: 'HH:MM'


class RevealBody(BaseModel):
    path: str


def build_modules_router(
    settings: Settings, db: Database, search: FileSearch, require_user,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["modules"])
    OWNER = settings.owner_chat_id or 0

    # -- Automation: reminders ----------------------------------------------
    @router.get("/reminders")
    def reminders_list(_u: str = Depends(require_user)):
        rows = db.list_reminders(OWNER)
        return {"reminders": [
            {"id": r["id"], "text": r["text"], "recurrence": r["recurrence"],
             "daily_time": r["daily_time"],
             "when": datetime.fromtimestamp(r["due_ts"]).strftime("%Y-%m-%d %H:%M"),
             "due_ts": r["due_ts"]}
            for r in rows
        ]}

    @router.post("/reminders")
    def reminders_add(body: ReminderBody, _u: str = Depends(require_user)):
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "text required")
        if body.daily_time:
            db.add_reminder(OWNER, text, next_daily_ts(body.daily_time), "daily", body.daily_time)
            return {"ok": True, "recurrence": "daily", "daily_time": body.daily_time}
        if not body.when:
            raise HTTPException(400, "provide `when` (one-time) or `daily_time`")
        try:
            due = datetime.fromisoformat(body.when).timestamp()
        except ValueError as e:
            raise HTTPException(400, "bad time format (use YYYY-MM-DDTHH:MM)") from e
        if due <= time.time():
            raise HTTPException(400, "that time is in the past")
        db.add_reminder(OWNER, text, due, "once")
        return {"ok": True, "recurrence": "once"}

    @router.delete("/reminders/{reminder_id}")
    def reminders_cancel(reminder_id: int, _u: str = Depends(require_user)):
        ok = db.deactivate_reminder(reminder_id, OWNER)
        return {"ok": ok}

    # -- Files & OCR ---------------------------------------------------------
    @router.get("/files/list")
    def files_list(
        q: str = "", type: str = "", limit: int = Query(200, le=2000),
        _u: str = Depends(require_user),
    ):
        rows = db.search_files_by_name(q, limit) if q else db.all_files(limit)
        if type:
            rows = [r for r in rows if r.get("file_type") == type]
        return {"files": [
            {"name": r["name"], "path": r["path"], "ext": r["ext"], "size": r["size"],
             "file_type": r["file_type"], "status": r["status"], "chunks": r["chunks"],
             "mtime": r["mtime"]}
            for r in rows
        ]}

    @router.get("/files/stats")
    def files_stats(_u: str = Depends(require_user)):
        return db.file_stats()

    @router.get("/files/download")
    def files_download(path: str = Query(...), _u: str = Depends(require_user)):
        # only serve files Kukku has indexed and that live under the home dir
        p = Path(path).expanduser().resolve()
        home = Path.home().resolve()
        if not (p == home or home in p.parents) or not p.is_file():
            raise HTTPException(404, "not found")
        if db.get_file(str(p)) is None and db.get_file(path) is None:
            raise HTTPException(403, "file is not indexed")
        return FileResponse(str(p), filename=p.name)

    @router.post("/files/reveal")
    def files_reveal(body: RevealBody, _u: str = Depends(require_user)):
        folder = str(Path(body.path).expanduser().parent)
        res = local_commands.execute("open_folder", folder)
        return {"ok": res.ok, "message": res.message}

    @router.get("/ocr/search")
    def ocr_search(q: str = Query(..., min_length=1), _u: str = Depends(require_user)):
        results = search.search(q, limit=20, file_type="image")
        return {"query": q, "results": [r.to_dict() for r in results]}

    # -- Developer: activity / logs -----------------------------------------
    @router.get("/activity")
    def activity(limit: int = Query(100, le=1000), _u: str = Depends(require_user)):
        return {"requests": db.recent_requests(limit), "searches": db.recent_searches(50)}

    @router.get("/logs/tail")
    def logs_tail(lines: int = Query(120, le=1000), _u: str = Depends(require_user)):
        log_file = settings.log_dir / "jarvis.log"
        if not log_file.exists():
            return {"lines": []}
        try:
            content = log_file.read_text(errors="replace").splitlines()
        except OSError:
            return {"lines": []}
        return {"lines": content[-lines:]}

    # -- Settings (read-only view; edits still go through .env + restart) ----
    @router.get("/settings")
    def get_settings(_u: str = Depends(require_user)):
        return {
            "llm_priority": settings.llm_priority,
            "providers": METRICS.snapshot(),
            "index_dirs": [str(p) for p in settings.index_paths],
            "whisper_model": settings.whisper_model,
            "enable_ocr": settings.enable_ocr,
            "enable_voice": settings.enable_voice,
            "max_file_size_mb": settings.max_file_size_mb,
            "rescan_interval_min": settings.rescan_interval_min,
            "alert_battery_pct": settings.alert_battery_pct,
            "alert_disk_pct": settings.alert_disk_pct,
            "backup_enabled": settings.backup_enabled,
            "dashboard_port": settings.dashboard_port,
        }

    # -- Notifications (recent alerts + denied access) ----------------------
    @router.get("/notifications")
    def notifications(_u: str = Depends(require_user)):
        reqs = db.recent_requests(200)
        denied = [r for r in reqs if r["kind"] == "denied"][:20]
        return {
            "denied_access": denied,
            "recent": reqs[:30],
        }

    return router
