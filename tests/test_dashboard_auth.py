"""Integration test: every sensitive dashboard endpoint requires authentication.

Builds the full app exactly as production does (create_app with agent + search,
so the chat and modules routers are mounted) and asserts that each data endpoint
returns 401 without a token — and works with one. This is the regression guard
for the "no unauthenticated access to files/logs/memory/etc." requirement.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.service import AuthStore
from app.config import Settings
from app.core.agent import AgentReply
from app.dashboard.api import create_app


class StubIndexer:
    scanning = False
    pending = 0
    last_scan = None

    def full_scan(self):
        return 0


class FakeAgent:
    db = None

    async def run(self, chat_id, text, on_text=None, source="telegram"):
        return AgentReply(text="ok")


class FakeSearch:
    def search(self, q, limit=12, file_type=None):
        return []


# every endpoint that exposes data or performs an action — none may be public
PROTECTED = [
    ("GET", "/api/status"),
    ("POST", "/api/reindex"),
    ("GET", "/api/memory"),
    ("GET", "/api/memory/export"),
    ("GET", "/api/search?q=x"),
    ("GET", "/api/chat/history"),
    ("GET", "/api/files/list"),
    ("GET", "/api/files/download?path=/etc/hosts"),
    ("GET", "/api/activity"),
    ("GET", "/api/logs/tail"),
    ("GET", "/api/settings"),
    ("GET", "/api/notifications"),
    ("GET", "/api/reminders"),
    ("GET", "/api/ocr/search?q=x"),
]


@pytest.fixture()
def client(db, fake_store, tmp_path):
    settings = Settings(data_dir=tmp_path / "data", index_dirs=str(tmp_path), allowed_user_ids="42")
    AuthStore(settings.auth_path).set_credentials("manish", "s3cret-pass")
    agent = FakeAgent()
    agent.db = db
    app = create_app(settings, db, fake_store, StubIndexer(), "test-llm",
                     agent=agent, search=FakeSearch())
    return TestClient(app)


@pytest.mark.parametrize("method,path", PROTECTED)
def test_endpoint_requires_auth(client, method, path):
    r = client.request(method, path)
    assert r.status_code == 401, f"{method} {path} was reachable without a token"


def test_public_auth_endpoints_stay_open(client):
    # the login-flow endpoints must remain reachable without a token
    assert client.get("/api/auth/status").status_code == 200


def test_valid_token_unlocks_endpoints(client):
    tok = client.post("/api/auth/login",
                      json={"username": "manish", "password": "s3cret-pass"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/status", headers=h).status_code == 200
    assert client.get("/api/memory", headers=h).status_code == 200
    assert client.get("/api/settings", headers=h).status_code == 200
