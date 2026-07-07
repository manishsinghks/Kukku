"""Tests for the auth service, store, and router."""
from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.router import build_auth
from app.auth.service import AuthError, AuthService, AuthStore
from app.config import Settings


@pytest.fixture()
def store(tmp_path):
    return AuthStore(tmp_path / "auth.json")


# -- store ------------------------------------------------------------------
def test_store_set_and_verify_password(store):
    assert store.is_configured() is False
    store.set_credentials("manish", "s3cret-pass")
    assert store.is_configured() is True
    assert store.username == "manish"
    assert store.verify_password("manish", "s3cret-pass") is True
    assert store.verify_password("manish", "wrong") is False
    assert store.verify_password("someone", "s3cret-pass") is False


def test_store_hash_is_not_plaintext(store, tmp_path):
    store.set_credentials("manish", "s3cret-pass")
    raw = (tmp_path / "auth.json").read_text()
    assert "s3cret-pass" not in raw       # never stored in plaintext
    assert "argon2" in raw                 # it's an Argon2 hash


def test_store_file_is_owner_only(store, tmp_path):
    store.set_credentials("manish", "s3cret-pass")
    mode = (tmp_path / "auth.json").stat().st_mode & 0o777
    assert mode == 0o600


def test_secret_is_stable(store):
    s1 = store.secret
    s2 = store.secret
    assert s1 == s2 and len(s1) >= 32


# -- service ----------------------------------------------------------------
@pytest.fixture()
def service(store):
    store.set_credentials("manish", "s3cret-pass")
    return AuthService(store)


def test_login_success_returns_tokens(service):
    t = service.login("manish", "s3cret-pass")
    assert t["access_token"] and t["refresh_token"]
    assert t["user"] == "manish" and t["token_type"] == "bearer"


def test_login_wrong_password_raises(service):
    with pytest.raises(AuthError):
        service.login("manish", "nope")


def test_lockout_after_repeated_failures(service):
    for _ in range(5):
        with pytest.raises(AuthError):
            service.login("manish", "nope", client_key="1.2.3.4")
    # even the correct password is now locked out
    with pytest.raises(AuthError, match="locked out"):
        service.login("manish", "s3cret-pass", client_key="1.2.3.4")


def test_access_token_roundtrip(service):
    t = service.login("manish", "s3cret-pass")
    assert service.verify_access(t["access_token"]) == "manish"


def test_refresh_mints_new_access(service):
    t = service.login("manish", "s3cret-pass")
    t2 = service.refresh(t["refresh_token"])
    assert service.verify_access(t2["access_token"]) == "manish"


def test_refresh_token_cannot_be_used_as_access(service):
    t = service.login("manish", "s3cret-pass")
    with pytest.raises(AuthError, match="wrong token type"):
        service.verify_access(t["refresh_token"])


def test_tampered_token_rejected(service):
    t = service.login("manish", "s3cret-pass")
    with pytest.raises(AuthError):
        service.verify_access(t["access_token"] + "x")


# -- router -----------------------------------------------------------------
@pytest.fixture()
def client(tmp_path):
    settings = Settings(data_dir=tmp_path)
    AuthStore(settings.auth_path).set_credentials("manish", "s3cret-pass")
    router, require_user, _service = build_auth(settings)
    app = FastAPI()
    app.include_router(router)

    @app.get("/api/protected")
    def protected(user: str = Depends(require_user)):
        return {"hello": user}

    return TestClient(app)


def test_router_login_and_protected(client):
    r = client.post("/api/auth/login", json={"username": "manish", "password": "s3cret-pass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    # protected route requires the bearer token
    assert client.get("/api/protected").status_code == 401
    r2 = client.get("/api/protected", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200 and r2.json()["hello"] == "manish"


def test_router_login_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "manish", "password": "nope"})
    assert r.status_code == 401


def test_router_status_reports_configured(client):
    r = client.get("/api/auth/status")
    assert r.json() == {"configured": True, "user": "manish"}
