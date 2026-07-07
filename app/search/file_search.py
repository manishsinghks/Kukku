"""Hybrid file search: filename fuzzy match + semantic vector search, merged and ranked."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz

from app.db.database import Database
from app.search.vector_store import VectorStore


@dataclass
class SearchResult:
    path: str
    name: str
    file_type: str
    score: float
    mtime: float = 0.0
    size: int = 0
    snippet: str = ""
    matched_by: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path, "name": self.name, "file_type": self.file_type,
            "score": round(self.score, 4), "mtime": self.mtime, "size": self.size,
            "snippet": self.snippet, "matched_by": self.matched_by,
        }


def _recency_boost(mtime: float, now: float | None = None) -> float:
    """0..0.15 boost for recently modified files (30-day half-life-ish)."""
    now = now or time.time()
    age_days = max(0.0, (now - mtime) / 86400)
    return 0.15 / (1.0 + age_days / 30.0)


CACHE_TTL = 60.0  # seconds — repeated identical queries skip re-embedding


class FileSearch:
    def __init__(self, db: Database, store: VectorStore):
        self.db = db
        self.store = store
        self._cache: dict[tuple, tuple[float, list[SearchResult]]] = {}

    def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 8,
        file_type: str | None = None,
    ) -> list[SearchResult]:
        """search_type: filename | semantic | all"""
        query = query.strip()
        key = (query.lower(), search_type, limit, file_type)
        cached = self._cache.get(key)
        if cached and time.time() - cached[0] < CACHE_TTL:
            return cached[1]
        merged: dict[str, SearchResult] = {}

        if search_type in ("filename", "all"):
            for r in self._filename_search(query, limit * 3):
                merged[r.path] = r

        if search_type in ("semantic", "all"):
            for hit in self.store.query(query, n_results=limit * 2):
                existing = merged.get(hit["path"])
                if existing:
                    existing.score += hit["score"] * 0.8
                    existing.snippet = existing.snippet or hit["snippet"]
                    existing.matched_by.append("semantic")
                else:
                    rec = self.db.get_file(hit["path"]) or {}
                    merged[hit["path"]] = SearchResult(
                        path=hit["path"], name=hit["name"],
                        file_type=hit.get("file_type") or rec.get("file_type", ""),
                        score=hit["score"], snippet=hit["snippet"],
                        mtime=rec.get("mtime") or 0.0, size=rec.get("size") or 0,
                        matched_by=["semantic"],
                    )

        results = list(merged.values())
        if file_type:
            results = [r for r in results if r.file_type == file_type]
        for r in results:
            r.score += _recency_boost(r.mtime)
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:limit]

        self.db.log_search(query, search_type, [r.path for r in results])
        if len(self._cache) > 128:  # bounded
            self._cache.clear()
        self._cache[key] = (time.time(), results)
        return results

    def _filename_search(self, query: str, limit: int) -> list[SearchResult]:
        out: list[SearchResult] = []
        seen: set[str] = set()

        # exact-ish LIKE hits first
        for token in [query] + query.split():
            for rec in self.db.search_files_by_name(token, limit):
                if rec["path"] in seen:
                    continue
                seen.add(rec["path"])
                ratio = fuzz.partial_ratio(query.lower(), rec["name"].lower()) / 100.0
                out.append(self._from_record(rec, score=0.5 + 0.5 * ratio, how="filename"))
            if len(out) >= limit:
                break

        # fuzzy pass over the corpus if LIKE found little
        if len(out) < 5:
            for rec in self.db.all_files(limit=4000):
                if rec["path"] in seen or rec["status"] != "indexed":
                    continue
                ratio = fuzz.partial_ratio(query.lower(), rec["name"].lower()) / 100.0
                if ratio >= 0.75:
                    seen.add(rec["path"])
                    out.append(self._from_record(rec, score=0.4 + 0.4 * ratio, how="filename-fuzzy"))
        return out[:limit]

    @staticmethod
    def _from_record(rec: dict[str, Any], score: float, how: str) -> SearchResult:
        return SearchResult(
            path=rec["path"], name=rec["name"], file_type=rec.get("file_type") or "",
            score=score, mtime=rec.get("mtime") or 0.0, size=rec.get("size") or 0,
            matched_by=[how],
        )
