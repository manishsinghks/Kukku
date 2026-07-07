"""Authentication: single-user login with Argon2 password hashing + JWT.

Design (single owner, no signup):
  • Credentials live in data/auth.json (chmod 600): {username, password_hash}.
    Set via scripts/set_password.py — the password is NEVER stored in code, .env,
    or chat, only its Argon2 hash.
  • Access token: short-lived JWT (default 30 min) sent as Bearer on each request.
  • Refresh token: long-lived JWT (default 7 days) to mint new access tokens.
  • The signing secret is generated once and persisted in data/auth.json.
  • Login is rate-limited (lockout after repeated failures) to resist brute force.
"""
from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.utils.logging import get_logger

log = get_logger(__name__)

_ph = PasswordHasher()  # sensible Argon2id defaults

ACCESS_TTL_S = 30 * 60           # 30 minutes
REFRESH_TTL_S = 7 * 24 * 3600    # 7 days
ALGO = "HS256"

# login rate limiting
_MAX_FAILURES = 5
_LOCKOUT_S = 300  # 5 minutes


class AuthError(Exception):
    """Any authentication failure (bad credentials, expired/invalid token, lockout)."""


@dataclass
class AuthStore:
    """Reads/writes credentials + signing secret from data/auth.json."""

    path: Path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))
        self.path.chmod(0o600)  # owner-only

    @property
    def secret(self) -> str:
        data = self._load()
        if not data.get("jwt_secret"):
            data["jwt_secret"] = secrets.token_hex(32)
            self._save(data)
        return data["jwt_secret"]

    @property
    def username(self) -> str | None:
        return self._load().get("username")

    def is_configured(self) -> bool:
        d = self._load()
        return bool(d.get("username") and d.get("password_hash"))

    def set_credentials(self, username: str, password: str) -> None:
        data = self._load()
        data["username"] = username.strip()
        data["password_hash"] = _ph.hash(password)
        data.setdefault("jwt_secret", secrets.token_hex(32))
        self._save(data)

    def verify_password(self, username: str, password: str) -> bool:
        data = self._load()
        if not data.get("password_hash") or username.strip() != data.get("username"):
            return False
        try:
            _ph.verify(data["password_hash"], password)
            return True
        except VerifyMismatchError:
            return False


class AuthService:
    def __init__(self, store: AuthStore):
        self.store = store
        self._failures: dict[str, list[float]] = {}  # key -> failure timestamps

    # -- rate limiting -------------------------------------------------------
    def _locked(self, key: str) -> bool:
        now = time.time()
        recent = [t for t in self._failures.get(key, []) if now - t < _LOCKOUT_S]
        self._failures[key] = recent
        return len(recent) >= _MAX_FAILURES

    def _record_failure(self, key: str) -> None:
        self._failures.setdefault(key, []).append(time.time())

    # -- tokens --------------------------------------------------------------
    def _make_token(self, kind: str, ttl_s: int) -> str:
        now = int(time.time())
        payload = {
            "sub": self.store.username,
            "type": kind,
            "iat": now,
            "exp": now + ttl_s,
            "jti": secrets.token_hex(8),
        }
        return jwt.encode(payload, self.store.secret, algorithm=ALGO)

    def _decode(self, token: str, expected_type: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.store.secret, algorithms=[ALGO])
        except jwt.ExpiredSignatureError as e:
            raise AuthError("token expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthError("invalid token") from e
        if payload.get("type") != expected_type:
            raise AuthError("wrong token type")
        if payload.get("sub") != self.store.username:
            raise AuthError("unknown user")
        return payload

    # -- public API ----------------------------------------------------------
    def login(self, username: str, password: str, client_key: str = "default") -> dict[str, Any]:
        if self._locked(client_key):
            raise AuthError("too many attempts — locked out, try again in a few minutes")
        if not self.store.is_configured():
            raise AuthError("no account configured — run scripts/set_password.py first")
        if not self.store.verify_password(username, password):
            self._record_failure(client_key)
            raise AuthError("invalid username or password")
        self._failures.pop(client_key, None)  # reset on success
        return self._tokens()

    def _tokens(self) -> dict[str, Any]:
        return {
            "access_token": self._make_token("access", ACCESS_TTL_S),
            "refresh_token": self._make_token("refresh", REFRESH_TTL_S),
            "token_type": "bearer",
            "expires_in": ACCESS_TTL_S,
            "user": self.store.username,
        }

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        self._decode(refresh_token, "refresh")  # raises AuthError if bad
        return self._tokens()

    def verify_access(self, token: str) -> str:
        """Return the username for a valid access token, or raise AuthError."""
        return self._decode(token, "access")["sub"]
