"""Background indexer: initial scan, periodic rescans, and live watchdog updates.

Runs in its own threads so it never blocks the bot's event loop.
"""
from __future__ import annotations

import fnmatch
import queue
import threading
import time
from pathlib import Path

from app.config import Settings
from app.db.database import Database
from app.search import extractors
from app.search.vector_store import VectorStore
from app.utils.logging import get_logger

log = get_logger(__name__)

SKIP_DIR_PATTERNS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", ".cache",
    "Library", ".Trash", "dist", "build", ".next", "target", ".idea",
    "*.photoslibrary", "*.app",
}


def _skip_dir(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in SKIP_DIR_PATTERNS) or name.startswith(".")


def _needs_retry(record: dict) -> bool:
    """A recorded failure caused by a missing dependency (e.g. tesseract was
    installed after the first scan) should be retried; content errors stay."""
    err = record.get("error") or ""
    return "not installed" in err or "deps missing" in err


class Indexer:
    def __init__(self, settings: Settings, db: Database, store: VectorStore):
        self.settings = settings
        self.db = db
        self.store = store
        self._queue: queue.Queue[Path] = queue.Queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._observer = None
        self.scanning = False
        self.last_scan: float | None = None

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        worker = threading.Thread(target=self._worker, name="indexer-worker", daemon=True)
        scanner = threading.Thread(target=self._scan_loop, name="indexer-scanner", daemon=True)
        worker.start()
        scanner.start()
        self._threads = [worker, scanner]
        self._start_watchdog()

    def stop(self) -> None:
        self._stop.set()
        if self._observer:
            self._observer.stop()

    def _start_watchdog(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            log.warning("watchdog not installed; live re-indexing disabled")
            return

        idx = self

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if not event.is_directory:
                    idx.enqueue(Path(event.src_path))

            def on_modified(self, event):
                if not event.is_directory:
                    idx.enqueue(Path(event.src_path))

            def on_deleted(self, event):
                if not event.is_directory:
                    idx.forget(Path(event.src_path))

            def on_moved(self, event):
                if not event.is_directory:
                    idx.forget(Path(event.src_path))
                    idx.enqueue(Path(event.dest_path))

        self._observer = Observer()
        handler = Handler()
        for root in self.settings.index_paths:
            try:
                self._observer.schedule(handler, str(root), recursive=True)
            except OSError as e:
                log.warning("Cannot watch %s: %s", root, e)
        self._observer.daemon = True
        self._observer.start()
        log.info("Watchdog observing %d directories", len(self.settings.index_paths))

    # -- queue API -------------------------------------------------------
    def enqueue(self, path: Path) -> None:
        if self._eligible(path):
            self._queue.put(path)

    def forget(self, path: Path) -> None:
        self.db.remove_file(str(path))
        self.store.remove_file(str(path))

    def _eligible(self, path: Path) -> bool:
        if path.name.startswith(".") or path.suffix.lower() not in extractors.SUPPORTED_EXTS:
            return False
        return all(not _skip_dir(part) for part in path.parts[:-1])

    # -- scanning ----------------------------------------------------------
    def _scan_loop(self) -> None:
        # initial scan immediately, then periodic rescans
        while not self._stop.is_set():
            try:
                self.full_scan()
            except Exception:  # noqa: BLE001
                log.exception("full scan failed")
            self._stop.wait(self.settings.rescan_interval_min * 60)

    def full_scan(self) -> int:
        self.scanning = True
        queued = 0
        try:
            for root in self.settings.index_paths:
                queued += self._scan_dir(root)
        finally:
            self.scanning = False
            self.last_scan = time.time()
        log.info("Scan complete: %d files queued for (re)indexing", queued)
        return queued

    def _scan_dir(self, root: Path) -> int:
        queued = 0
        stack = [root]
        while stack and not self._stop.is_set():
            current = stack.pop()
            try:
                entries = list(current.iterdir())
            except (PermissionError, OSError):
                continue
            for entry in entries:
                if entry.is_dir():
                    if not _skip_dir(entry.name):
                        stack.append(entry)
                    continue
                if not self._eligible(entry):
                    continue
                try:
                    st = entry.stat()
                except OSError:
                    continue
                existing = self.db.get_file(str(entry))
                if (
                    existing
                    and existing["mtime"] == st.st_mtime
                    and existing["status"] == "indexed"
                    and not _needs_retry(existing)
                ):
                    continue  # unchanged
                self._queue.put(entry)
                queued += 1
        return queued

    # -- indexing worker -----------------------------------------------------
    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                path = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                self.index_one(path)
            except Exception:  # noqa: BLE001
                log.exception("indexing %s failed", path)

    def index_one(self, path: Path) -> None:
        if not path.exists():
            self.forget(path)
            return
        st = path.stat()
        # duplicate watchdog events for one save all carry the same mtime — skip repeats
        existing = self.db.get_file(str(path))
        if (
            existing
            and existing["mtime"] == st.st_mtime
            and existing["status"] == "indexed"
            and not _needs_retry(existing)
        ):
            return
        meta = {
            "path": str(path),
            "name": path.name,
            "ext": path.suffix.lower(),
            "size": st.st_size,
            "mtime": st.st_mtime,
            "file_type": extractors.classify(path),
            "status": "indexed",
            "chunks": 0,
            "error": None,
            "indexed_at": time.time(),
        }
        if st.st_size > self.settings.max_file_size_mb * 1024 * 1024:
            meta.update(status="skipped", error="too large")
            self.db.upsert_file(meta)
            return
        try:
            text = extractors.extract_text(path, ocr_enabled=self.settings.enable_ocr)
        except extractors.ExtractionError as e:
            # still searchable by filename — record it with 0 chunks
            meta.update(status="indexed", error=str(e))
            self.db.upsert_file(meta)
            return
        chunks = extractors.chunk_text(text)
        stored = self.store.index_file(str(path), path.name, meta["file_type"], chunks)
        meta["chunks"] = stored
        self.db.upsert_file(meta)

    @property
    def pending(self) -> int:
        return self._queue.qsize()
