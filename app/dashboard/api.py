"""Admin dashboard: FastAPI JSON API + static single-page UI.

Binds to 127.0.0.1 by default — it exposes file paths and logs, so it is
deliberately local-only unless the user changes DASHBOARD_HOST.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.auth.router import build_auth
from app.config import Settings
from app.db.database import Database
from app.search.indexer import Indexer
from app.search.vector_store import VectorStore
from app.tools.system_status import system_status

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    settings: Settings, db: Database, store: VectorStore, indexer: Indexer,
    provider_name: str = "?", provider: Any = None,
    agent: Any = None, search: Any = None,
) -> FastAPI:
    app = FastAPI(title="Kukku Dashboard", version=__version__, docs_url="/api/docs")

    # Allow the Next.js dev/prod app (localhost) to call this API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:3001", "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Authentication (login / refresh / logout) + the require_user dependency.
    auth_router, _require_user, _auth_service = build_auth(settings)
    app.include_router(auth_router)
    app.state.require_user = _require_user

    # Authenticated chat + realtime + memory + search (shared agent) for the web app.
    if agent is not None and search is not None:
        from app.dashboard.chat_api import build_chat_router
        from app.dashboard.modules_api import build_modules_router

        app.include_router(
            build_chat_router(settings, db, agent, search, _require_user, _auth_service)
        )
        app.include_router(build_modules_router(settings, db, search, _require_user))

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        from app.core.llm import METRICS

        providers = provider.status() if hasattr(provider, "status") else None
        return {
            "version": __version__,
            "llm": provider_name,
            "providers": providers,
            "provider_metrics": METRICS.snapshot(),
            "system": system_status(),
            "db": db.stats_summary(),
            "vector": store.stats(),
            "indexer": {
                "scanning": indexer.scanning,
                "pending": indexer.pending,
                "last_scan": indexer.last_scan,
                "watched_dirs": [str(p) for p in settings.index_paths],
            },
        }

    @app.get("/api/files")
    def files(limit: int = Query(200, le=5000), q: str = "") -> list[dict[str, Any]]:
        if q:
            return db.search_files_by_name(q, limit)
        return db.all_files(limit)

    @app.get("/api/files/stats")
    def files_stats() -> dict[str, Any]:
        return db.file_stats()

    @app.get("/api/searches")
    def searches(limit: int = Query(100, le=1000)) -> list[dict[str, Any]]:
        return db.recent_searches(limit)

    @app.get("/api/logs")
    def logs(limit: int = Query(100, le=1000)) -> list[dict[str, Any]]:
        return db.recent_requests(limit)

    @app.get("/api/memory")
    def memory() -> dict[str, Any]:
        return {"memories": db.list_memories(), "aliases": db.list_aliases()}

    @app.post("/api/reindex")
    def reindex() -> dict[str, Any]:
        import threading

        threading.Thread(target=indexer.full_scan, daemon=True).start()
        return {"ok": True}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
