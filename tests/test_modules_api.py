"""Tests for the dashboard modules API (reminders, files, ocr, activity, settings)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.dashboard.modules_api import build_modules_router
from app.search.file_search import SearchResult


class FakeSearch:
    def search(self, q, limit=20, file_type=None):
        r = SearchResult(path="/x/shot.png", name="shot.png", file_type="image", score=0.9)
        return [r] if file_type == "image" else []


@pytest.fixture()
def client(db):
    settings = Settings(allowed_user_ids="42", data_dir="/tmp/jarvis-test-mods")

    def require_user():
        return "manish"

    app = FastAPI()
    app.include_router(build_modules_router(settings, db, FakeSearch(), require_user))
    return TestClient(app), db


def test_reminders_add_list_cancel(client):
    c, db = client
    when = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    assert c.post("/api/reminders", json={"text": "call mom", "when": when}).json()["ok"]
    lst = c.get("/api/reminders").json()["reminders"]
    assert any(r["text"] == "call mom" for r in lst)
    rid = lst[0]["id"]
    assert c.request("DELETE", f"/api/reminders/{rid}").json()["ok"] is True


def test_reminders_daily(client):
    c, _ = client
    r = c.post("/api/reminders", json={"text": "standup", "daily_time": "09:30"}).json()
    assert r["recurrence"] == "daily" and r["daily_time"] == "09:30"


def test_reminders_past_time_rejected(client):
    c, _ = client
    past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    assert c.post("/api/reminders", json={"text": "x", "when": past}).status_code == 400


def test_files_list_and_filter(client):
    c, db = client
    for name, ft in [("a.pdf", "document"), ("b.png", "image")]:
        db.upsert_file({"path": f"/d/{name}", "name": name, "ext": "." + name.split(".")[1],
                        "size": 10, "mtime": time.time(), "file_type": ft, "status": "indexed",
                        "chunks": 1, "error": None, "indexed_at": time.time()})
    assert len(c.get("/api/files/list").json()["files"]) == 2
    imgs = c.get("/api/files/list", params={"type": "image"}).json()["files"]
    assert len(imgs) == 1 and imgs[0]["name"] == "b.png"


def test_files_download_rejects_unindexed(client):
    c, _ = client
    r = c.get("/api/files/download", params={"path": "/etc/hosts"})
    assert r.status_code in (403, 404)


def test_ocr_search(client):
    c, _ = client
    res = c.get("/api/ocr/search", params={"q": "docker"}).json()
    assert res["results"] and res["results"][0]["file_type"] == "image"


def test_activity_and_settings(client):
    c, db = client
    db.log_request(42, "text", "hi", "hello", 100)
    assert c.get("/api/activity").json()["requests"][0]["request"] == "hi"
    s = c.get("/api/settings").json()
    assert "llm_priority" in s and "whisper_model" in s


def test_notifications_surfaces_denied(client):
    c, db = client
    db.log_request(999, "denied", "sneaky")
    n = c.get("/api/notifications").json()
    assert any(d["kind"] == "denied" for d in n["denied_access"])
