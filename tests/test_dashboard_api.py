"""Integration tests for the dashboard API using FastAPI's TestClient."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dashboard.api import create_app


class StubIndexer:
    scanning = False
    pending = 0
    last_scan = None

    def full_scan(self):
        return 0


@pytest.fixture()
def client(db, fake_store, tmp_path):
    settings = Settings(data_dir=tmp_path / "data", index_dirs=str(tmp_path))
    app = create_app(settings, db, fake_store, StubIndexer(), "test-llm")
    return TestClient(app)


def test_status_endpoint(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["llm"] == "test-llm"
    assert "cpu_percent" in body["system"]
    assert body["vector"]["available"] is True


def test_files_endpoint_with_query(client, db):
    db.upsert_file({
        "path": "/x/a.pdf", "name": "a.pdf", "ext": ".pdf", "size": 1, "mtime": time.time(),
        "file_type": "document", "status": "indexed", "chunks": 1, "error": None,
        "indexed_at": time.time(),
    })
    assert len(client.get("/api/files").json()) == 1
    assert len(client.get("/api/files", params={"q": "a.pdf"}).json()) == 1
    assert client.get("/api/files", params={"q": "zzz"}).json() == []


def test_memory_logs_searches_endpoints(client, db):
    db.add_memory("note")
    db.set_alias("x", "y")
    db.log_request(1, "text", "req")
    db.log_search("q", "all", [])
    assert client.get("/api/memory").json()["memories"][0]["content"] == "note"
    assert client.get("/api/logs").json()[0]["request"] == "req"
    assert client.get("/api/searches").json()[0]["query"] == "q"


def test_reindex_endpoint(client):
    assert client.post("/api/reindex").json() == {"ok": True}


def test_dashboard_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Kukku" in r.text
