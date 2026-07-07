"""SQLite persistence: conversations, memory, aliases, logs, search history, file index.

A single connection guarded by a lock is plenty at personal-assistant scale,
and WAL mode keeps the dashboard reads from blocking bot writes.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS aliases (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    kind TEXT NOT NULL,           -- text | voice | file | command | denied
    request TEXT,
    response_summary TEXT,
    duration_ms INTEGER,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_type TEXT NOT NULL,
    results_count INTEGER NOT NULL,
    top_result TEXT,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS indexed_files (
    path TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ext TEXT,
    size INTEGER,
    mtime REAL,
    file_type TEXT,               -- document | code | image | data | other
    status TEXT NOT NULL,         -- indexed | skipped | error
    chunks INTEGER DEFAULT 0,
    error TEXT,
    indexed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_files_name ON indexed_files(name);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    due_ts REAL NOT NULL,         -- epoch of the next (or only) fire
    recurrence TEXT NOT NULL DEFAULT 'once',  -- once | daily
    daily_time TEXT,              -- "HH:MM" for daily recurrence
    active INTEGER NOT NULL DEFAULT 1,
    created_ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(active, due_ts);
"""


class Database:
    def __init__(self, path: Path | str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    # -- low-level helpers ---------------------------------------------------
    def _write(self, sql: str, params: tuple = ()) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(sql, params)
            return cur.lastrowid or 0

    def _read(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def backup(self, dest: Path | str) -> None:
        """Consistent hot backup (safe under WAL) via SQLite's backup API."""
        with self._lock:
            target = sqlite3.connect(str(dest))
            try:
                self._conn.backup(target)
            finally:
                target.close()

    # -- conversation history ------------------------------------------------
    def add_message(self, chat_id: int, role: str, content: str) -> None:
        self._write(
            "INSERT INTO messages (chat_id, role, content, ts) VALUES (?,?,?,?)",
            (chat_id, role, content, time.time()),
        )

    def recent_messages(self, chat_id: int, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._read(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        )
        return list(reversed(rows))

    def clear_history(self, chat_id: int) -> None:
        self._write("DELETE FROM messages WHERE chat_id=?", (chat_id,))

    # -- memory / aliases ------------------------------------------------
    def add_memory(self, content: str) -> int:
        return self._write(
            "INSERT INTO memories (content, ts) VALUES (?,?)", (content, time.time())
        )

    def list_memories(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._read(
            "SELECT id, content, ts FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        )

    def delete_memory(self, memory_id: int) -> None:
        self._write("DELETE FROM memories WHERE id=?", (memory_id,))

    def set_alias(self, name: str, value: str) -> None:
        self._write(
            "INSERT INTO aliases (name, value, ts) VALUES (?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value, ts=excluded.ts",
            (name.lower(), value, time.time()),
        )

    def get_alias(self, name: str) -> str | None:
        rows = self._read("SELECT value FROM aliases WHERE name=?", (name.lower(),))
        return rows[0]["value"] if rows else None

    def list_aliases(self) -> list[dict[str, Any]]:
        return self._read("SELECT name, value, ts FROM aliases ORDER BY name")

    # -- request log ------------------------------------------------
    def log_request(
        self,
        user_id: int | None,
        kind: str,
        request: str,
        response_summary: str = "",
        duration_ms: int = 0,
    ) -> None:
        self._write(
            "INSERT INTO request_log (user_id, kind, request, response_summary, duration_ms, ts)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, kind, request[:2000], response_summary[:2000], duration_ms, time.time()),
        )

    def recent_requests(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._read(
            "SELECT * FROM request_log ORDER BY id DESC LIMIT ?", (limit,)
        )

    # -- search history ------------------------------------------------
    def log_search(self, query: str, search_type: str, results: list[str]) -> None:
        self._write(
            "INSERT INTO search_history (query, search_type, results_count, top_result, ts)"
            " VALUES (?,?,?,?,?)",
            (query, search_type, len(results), results[0] if results else None, time.time()),
        )

    def recent_searches(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._read(
            "SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (limit,)
        )

    # -- file index ------------------------------------------------
    def upsert_file(self, meta: dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO indexed_files (path, name, ext, size, mtime, file_type, status, chunks, error, indexed_at)"
                " VALUES (:path, :name, :ext, :size, :mtime, :file_type, :status, :chunks, :error, :indexed_at)"
                " ON CONFLICT(path) DO UPDATE SET name=excluded.name, ext=excluded.ext, size=excluded.size,"
                " mtime=excluded.mtime, file_type=excluded.file_type, status=excluded.status,"
                " chunks=excluded.chunks, error=excluded.error, indexed_at=excluded.indexed_at",
                meta,
            )

    def get_file(self, path: str) -> dict[str, Any] | None:
        rows = self._read("SELECT * FROM indexed_files WHERE path=?", (path,))
        return rows[0] if rows else None

    def remove_file(self, path: str) -> None:
        self._write("DELETE FROM indexed_files WHERE path=?", (path,))

    def search_files_by_name(self, pattern: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._read(
            "SELECT * FROM indexed_files WHERE name LIKE ? AND status='indexed'"
            " ORDER BY mtime DESC LIMIT ?",
            (f"%{pattern}%", limit),
        )

    def all_files(self, limit: int = 5000) -> list[dict[str, Any]]:
        return self._read(
            "SELECT * FROM indexed_files ORDER BY indexed_at DESC LIMIT ?", (limit,)
        )

    # -- reminders ------------------------------------------------------
    def add_reminder(
        self, chat_id: int, text: str, due_ts: float,
        recurrence: str = "once", daily_time: str | None = None,
    ) -> int:
        return self._write(
            "INSERT INTO reminders (chat_id, text, due_ts, recurrence, daily_time, active, created_ts)"
            " VALUES (?,?,?,?,?,1,?)",
            (chat_id, text, due_ts, recurrence, daily_time, time.time()),
        )

    def due_reminders(self, now: float) -> list[dict[str, Any]]:
        return self._read(
            "SELECT * FROM reminders WHERE active=1 AND due_ts<=? ORDER BY due_ts", (now,)
        )

    def list_reminders(self, chat_id: int | None = None) -> list[dict[str, Any]]:
        if chat_id is None:
            return self._read("SELECT * FROM reminders WHERE active=1 ORDER BY due_ts")
        return self._read(
            "SELECT * FROM reminders WHERE active=1 AND chat_id=? ORDER BY due_ts", (chat_id,)
        )

    def reschedule_reminder(self, reminder_id: int, next_ts: float) -> None:
        self._write("UPDATE reminders SET due_ts=? WHERE id=?", (next_ts, reminder_id))

    def deactivate_reminder(self, reminder_id: int, chat_id: int | None = None) -> bool:
        if chat_id is None:
            self._write("UPDATE reminders SET active=0 WHERE id=?", (reminder_id,))
            return True
        rows = self._read(
            "SELECT id FROM reminders WHERE id=? AND chat_id=? AND active=1",
            (reminder_id, chat_id),
        )
        if not rows:
            return False
        self._write("UPDATE reminders SET active=0 WHERE id=?", (reminder_id,))
        return True

    def file_stats(self) -> dict[str, Any]:
        counts = self._read(
            "SELECT status, COUNT(*) AS n, COALESCE(SUM(chunks),0) AS chunks FROM indexed_files GROUP BY status"
        )
        by_type = self._read(
            "SELECT file_type, COUNT(*) AS n FROM indexed_files WHERE status='indexed' GROUP BY file_type"
        )
        return {"by_status": counts, "by_type": by_type}

    def stats_summary(self) -> dict[str, Any]:
        def one(sql: str) -> int:
            r = self._read(sql)
            return int(list(r[0].values())[0]) if r else 0

        return {
            "messages": one("SELECT COUNT(*) FROM messages"),
            "memories": one("SELECT COUNT(*) FROM memories"),
            "aliases": one("SELECT COUNT(*) FROM aliases"),
            "requests": one("SELECT COUNT(*) FROM request_log"),
            "searches": one("SELECT COUNT(*) FROM search_history"),
            "files_indexed": one("SELECT COUNT(*) FROM indexed_files WHERE status='indexed'"),
            "chunks": one("SELECT COALESCE(SUM(chunks),0) FROM indexed_files"),
        }
