"""Central logging: rotating file + console, plus a SQLite event log."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:  # already configured
        return
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(console)

    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "jarvis.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "telegram", "apscheduler", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # chromadb 0.6 + new posthog raise a harmless capture() error on every event
    logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
