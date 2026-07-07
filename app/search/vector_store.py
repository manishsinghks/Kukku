"""ChromaDB-backed vector store with a lazily loaded sentence-transformers model.

If chromadb / sentence-transformers are not installed the store reports itself
unavailable and semantic search degrades to filename+keyword search.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.utils.logging import get_logger

log = get_logger(__name__)


class VectorStore:
    def __init__(self, persist_dir: Path, model_name: str):
        self._persist_dir = persist_dir
        self._model_name = model_name
        self._lock = threading.Lock()
        self._collection = None
        self._model = None
        self._unavailable_reason: str | None = None

    # -- lazy init -----------------------------------------------------------
    def _ensure(self) -> bool:
        if self._collection is not None and self._model is not None:
            return True
        if self._unavailable_reason:
            return False
        with self._lock:
            if self._collection is not None:
                return True
            try:
                import chromadb
                from sentence_transformers import SentenceTransformer

                client = chromadb.PersistentClient(
                    path=str(self._persist_dir),
                    settings=chromadb.Settings(anonymized_telemetry=False),
                )
                self._collection = client.get_or_create_collection(
                    "files", metadata={"hnsw:space": "cosine"}
                )
                log.info("Loading embedding model %s ...", self._model_name)
                self._model = SentenceTransformer(self._model_name)
                log.info("Vector store ready (%d chunks)", self._collection.count())
                return True
            except Exception as e:  # noqa: BLE001
                self._unavailable_reason = f"{type(e).__name__}: {e}"
                log.warning("Vector store unavailable: %s", self._unavailable_reason)
                return False

    @property
    def available(self) -> bool:
        return self._ensure()

    @property
    def unavailable_reason(self) -> str | None:
        return self._unavailable_reason

    def _embed(self, texts: list[str]) -> list[list[float]]:
        assert self._model is not None
        return self._model.encode(texts, show_progress_bar=False, batch_size=32).tolist()

    # -- write ---------------------------------------------------------------
    def index_file(self, path: str, name: str, file_type: str, chunks: list[str]) -> int:
        """Replace all chunks for a file. Returns number of chunks stored."""
        if not chunks or not self._ensure():
            return 0
        with self._lock:
            self._collection.delete(where={"path": path})
            ids = [f"{path}::{i}" for i in range(len(chunks))]
            metadatas: list[dict[str, Any]] = [
                {"path": path, "name": name, "file_type": file_type, "chunk": i}
                for i in range(len(chunks))
            ]
            self._collection.add(
                ids=ids, documents=chunks, metadatas=metadatas,
                embeddings=self._embed(chunks),
            )
        return len(chunks)

    def remove_file(self, path: str) -> None:
        if self._collection is None:
            return
        with self._lock:
            self._collection.delete(where={"path": path})

    # -- read ----------------------------------------------------------------
    def query(self, text: str, n_results: int = 10) -> list[dict[str, Any]]:
        """Return [{path, name, file_type, snippet, score}] sorted by score desc."""
        if not self._ensure():
            return []
        with self._lock:
            if self._collection.count() == 0:
                return []
            res = self._collection.query(
                query_embeddings=self._embed([text]),
                n_results=min(n_results * 3, 60),
                include=["documents", "metadatas", "distances"],
            )
        # keep the best chunk per file
        best: dict[str, dict[str, Any]] = {}
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0], strict=False
        ):
            score = 1.0 - float(dist)  # cosine distance -> similarity
            path = meta["path"]
            if path not in best or score > best[path]["score"]:
                best[path] = {
                    "path": path,
                    "name": meta.get("name", ""),
                    "file_type": meta.get("file_type", ""),
                    "snippet": doc[:400],
                    "score": round(score, 4),
                }
        out = sorted(best.values(), key=lambda x: x["score"], reverse=True)
        return out[:n_results]

    def stats(self) -> dict[str, Any]:
        if self._collection is None:
            ok = self._ensure()
            if not ok:
                return {"available": False, "reason": self._unavailable_reason, "chunks": 0}
        return {
            "available": True,
            "chunks": self._collection.count(),
            "model": self._model_name,
        }
