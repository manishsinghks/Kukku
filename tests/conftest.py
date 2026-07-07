from __future__ import annotations

from pathlib import Path

import pytest

from app.db.database import Database


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


class FakeVectorStore:
    """In-memory stand-in for the ChromaDB store (no heavy deps in tests)."""

    def __init__(self):
        self.docs: dict[str, dict] = {}

    @property
    def available(self) -> bool:
        return True

    def index_file(self, path, name, file_type, chunks):
        self.docs[path] = {"name": name, "file_type": file_type, "chunks": chunks}
        return len(chunks)

    def remove_file(self, path):
        self.docs.pop(path, None)

    def query(self, text, n_results=10):
        # naive keyword scoring: fraction of query words present in chunks
        words = set(text.lower().split())
        out = []
        for path, d in self.docs.items():
            joined = " ".join(d["chunks"]).lower()
            hits = sum(1 for w in words if w in joined)
            if hits:
                out.append({
                    "path": path, "name": d["name"], "file_type": d["file_type"],
                    "snippet": d["chunks"][0][:200], "score": hits / len(words),
                })
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:n_results]

    def stats(self):
        return {"available": True, "chunks": sum(len(d["chunks"]) for d in self.docs.values())}


@pytest.fixture()
def fake_store() -> FakeVectorStore:
    return FakeVectorStore()
