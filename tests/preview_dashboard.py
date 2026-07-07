"""Dashboard preview harness: real API + UI with seeded demo data, no bot/LLM needed.

    uvicorn tests.preview_dashboard:app --port 8788
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from app.config import Settings
from app.dashboard.api import create_app
from app.db.database import Database
from tests.conftest import FakeVectorStore


class StubIndexer:
    scanning = False
    pending = 3
    last_scan = time.time()

    def full_scan(self):
        return 0


_tmp = tempfile.mkdtemp(prefix="kukku-preview-")
settings = Settings(data_dir=Path(_tmp), index_dirs=str(Path.home() / "Desktop"))
db = Database(Path(_tmp) / "preview.db")

# Demo file paths are derived from $HOME so the harness stays portable and
# carries no personal information.
_docs = Path.home() / "Documents"

now = time.time()
for i, (name, ftype, chunks) in enumerate([
    ("resume_2026.pdf", "document", 4), ("expense_tracker.py", "code", 2),
    ("Screenshot docker error.png", "image", 1), ("budget.xlsx", "data", 6),
    ("notes.md", "document", 3),
]):
    db.upsert_file({
        "path": str(_docs / name), "name": name,
        "ext": "." + name.rsplit(".", 1)[-1], "size": 12345 * (i + 1),
        "mtime": now - i * 86400, "file_type": ftype, "status": "indexed",
        "chunks": chunks, "error": None, "indexed_at": now - i * 3600,
    })
db.add_memory("Prefers dark mode everywhere")
db.add_memory("Working on the bookmark dashboard project")
db.set_alias("my resume", str(_docs / "resume_2026.pdf"))
db.log_request(12345, "text", "find my resume", "Found resume_2026.pdf", 2100)
db.log_request(12345, "voice", "what's my cpu usage", "CPU is at 14%", 3400)
db.log_request(99999, "denied", "hello")
db.log_search("resume", "all", [str(_docs / "resume_2026.pdf")])
db.log_search("docker failed screenshot", "semantic", [str(_docs / "Screenshot docker error.png")])

store = FakeVectorStore()
store.index_file(str(_docs / "resume_2026.pdf"), "resume_2026.pdf", "document", ["a", "b", "c", "d"])


class FakeProvider:
    """Mimics FailoverProvider.status() for the dashboard preview."""

    def status(self):
        return {
            "Gemini (gemini-2.5-flash)": {"in_cooldown": False, "cooldown_left_s": 0},
            "Groq (llama-3.3-70b-versatile)": {"in_cooldown": False, "cooldown_left_s": 0},
        }


app = create_app(
    settings, db, store, StubIndexer(),
    "Gemini (gemini-2.5-flash) → Groq (llama-3.3-70b-versatile)", FakeProvider(),
)
