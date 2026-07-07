"""Entrypoint: starts the indexer, the Telegram bot, and the dashboard together.

    python -m app.main
"""
from __future__ import annotations

import asyncio
import contextlib
import signal

import uvicorn

from app.config import get_settings
from app.core.agent import Agent
from app.core.llm import build_provider
from app.core.voice import Transcriber
from app.db.database import Database
from app.search.file_search import FileSearch
from app.search.indexer import Indexer
from app.search.vector_store import VectorStore
from app.utils.logging import get_logger, setup_logging

log = get_logger("jarvis")


async def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_dir)

    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set — copy .env.example to .env and fill it in.")

    log.info("Kukku starting …")
    db = Database(settings.db_path)
    store = VectorStore(settings.chroma_dir, settings.embedding_model)
    indexer = Indexer(settings, db, store)
    search = FileSearch(db, store)

    provider, provider_name = await build_provider(settings)
    agent = Agent(settings, db, search, provider)
    transcriber = Transcriber(settings.whisper_model) if settings.enable_voice else None

    # background indexing (threads)
    indexer.start()

    # dashboard (same event loop, non-blocking)
    from app.dashboard.api import create_app

    dash = create_app(
        settings, db, store, indexer, provider_name, provider,
        agent=agent, search=search,
    )
    uv_config = uvicorn.Config(
        dash, host=settings.dashboard_host, port=settings.dashboard_port, log_level="warning"
    )
    uv_server = uvicorn.Server(uv_config)
    dash_task = asyncio.create_task(uv_server.serve())
    log.info("Dashboard on http://%s:%s", settings.dashboard_host, settings.dashboard_port)

    # telegram bot — cloud-bridge mode if a relay is configured, else polling
    from app.bot.telegram_bot import JarvisBot

    use_bridge = bool(settings.worker_url and settings.bridge_secret)
    bot = JarvisBot(settings, db, agent, indexer, transcriber, provider_name)
    await bot.start(polling=not use_bridge)

    bridge = None
    if use_bridge:
        from app.bot.bridge import CloudBridge

        bridge = CloudBridge(settings, bot.app)
        try:
            await bridge.start()
        except Exception:  # noqa: BLE001 — relay down: fall back to polling
            log.exception("Cloud bridge failed to start — falling back to polling")
            with contextlib.suppress(Exception):
                await bridge.stop()
            bridge = None
            await bot.app.bot.delete_webhook(drop_pending_updates=False)
            await bot.app.updater.start_polling(drop_pending_updates=True)
            bot._polling = True

    # proactive scheduler: reminders, system alerts, daily backup (zero LLM cost)
    from telegram.constants import ParseMode

    from app.core.scheduler import Scheduler

    async def _send(chat_id: int, text: str) -> None:
        try:
            await bot.app.bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
        except Exception:  # noqa: BLE001 — never let a bad send kill the scheduler
            with contextlib.suppress(Exception):
                await bot.app.bot.send_message(chat_id, text)

    scheduler = Scheduler(settings, db, _send)
    await scheduler.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    log.info("Kukku is up. LLM: %s", provider_name)
    await stop_event.wait()

    log.info("Shutting down …")
    await scheduler.stop()
    if bridge:
        await bridge.stop()
    await bot.stop()
    indexer.stop()
    uv_server.should_exit = True
    with contextlib.suppress(asyncio.CancelledError):
        await dash_task
    db.close()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()
