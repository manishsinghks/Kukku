"""Admin dashboard: authenticated FastAPI JSON API for the Next.js dashboard.

The official dashboard is the Next.js app in `web/`. This module exposes the
JSON API it consumes. Binds to 127.0.0.1 by default and every data endpoint
requires a valid JWT (see app.auth); public routes are limited to auth
(login/refresh/status).
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.auth.router import build_auth
from app.config import Settings
from app.db.database import Database
from app.search.indexer import Indexer
from app.search.vector_store import VectorStore
from app.tools.system_status import system_status


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
    require_user = _require_user

    # Authenticated chat + realtime + memory + search (shared agent) for the web app.
    if agent is not None and search is not None:
        from app.dashboard.chat_api import build_chat_router
        from app.dashboard.modules_api import build_modules_router

        app.include_router(
            build_chat_router(settings, db, agent, search, _require_user, _auth_service)
        )
        app.include_router(build_modules_router(settings, db, search, _require_user))

    @app.get("/api/status")
    def status(_u: str = Depends(require_user)) -> dict[str, Any]:
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

    @app.post("/api/reindex")
    def reindex(_u: str = Depends(require_user)) -> dict[str, Any]:
        import threading

        threading.Thread(target=indexer.full_scan, daemon=True).start()
        return {"ok": True}

    return app
