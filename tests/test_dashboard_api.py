"""Integration tests for the dashboard API using FastAPI's TestClient.

The dashboard API is authenticated: every data endpoint requires a valid JWT.
These tests exercise both the happy path (with a token) and, importantly, that
unauthenticated access is rejected with 401. The legacy unauthenticated static
dashboard and its open endpoints have been retired.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.service import AuthStore
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
    # configure a login so we can mint a real token
    AuthStore(settings.auth_path).set_credentials("manish", "s3cret-pass")
    app = create_app(settings, db, fake_store, StubIndexer(), "test-llm")
    return TestClient(app)


@pytest.fixture()
def auth(client):
    """Return an Authorization header dict for a freshly logged-in user."""
    r = client.post("/api/auth/login", json={"username": "manish", "password": "s3cret-pass"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# -- authentication enforcement ---------------------------------------------
def test_status_requires_auth(client):
    assert client.get("/api/status").status_code == 401


def test_reindex_requires_auth(client):
    assert client.post("/api/reindex").status_code == 401


def test_status_rejects_garbage_token(client):
    r = client.get("/api/status", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


# -- happy path (authenticated) ---------------------------------------------
def test_status_with_auth(client, auth):
    r = client.get("/api/status", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["llm"] == "test-llm"
    assert "cpu_percent" in body["system"]
    assert body["vector"]["available"] is True


def test_reindex_with_auth(client, auth):
    r = client.post("/api/reindex", headers=auth)
    assert r.status_code == 200 and r.json() == {"ok": True}


# -- retired legacy surface --------------------------------------------------
@pytest.mark.parametrize("path", ["/", "/api/files", "/api/logs", "/api/searches", "/api/files/stats"])
def test_retired_endpoints_are_gone(client, auth, path):
    # these belonged to the removed static dashboard; they should no longer exist
    # (checked WITH auth so a 404 means "removed", not "unauthorized")
    assert client.get(path, headers=auth).status_code == 404
