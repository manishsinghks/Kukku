"""Telegram bot: authentication, streaming replies, voice notes, file uploads."""
from __future__ import annotations

import asyncio
import contextlib
import time
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import Settings
from app.core.agent import Agent
from app.core.voice import Transcriber
from app.db.database import Database
from app.search.indexer import Indexer
from app.tools.system_status import system_status
from app.utils.logging import get_logger

log = get_logger(__name__)

EDIT_INTERVAL = 1.5  # seconds between streaming message edits (Telegram rate limits)


class JarvisBot:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        agent: Agent,
        indexer: Indexer,
        transcriber: Transcriber | None,
        provider_name: str,
    ):
        self.settings = settings
        self.db = db
        self.agent = agent
        self.indexer = indexer
        self.transcriber = transcriber
        self.provider_name = provider_name
        self.app: Application = (
            ApplicationBuilder().token(settings.telegram_bot_token).concurrent_updates(True).build()
        )
        self._register()

    # -- setup -----------------------------------------------------------
    def _register(self) -> None:
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("memory", self.cmd_memory))
        self.app.add_handler(CommandHandler("clear", self.cmd_clear))
        self.app.add_handler(CommandHandler("reindex", self.cmd_reindex))
        self.app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self.on_voice))
        self.app.add_handler(
            MessageHandler(filters.Document.ALL | filters.PHOTO, self.on_file)
        )
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))
        self.app.add_error_handler(self.on_error)

    # -- auth --------------------------------------------------------------
    def _authorized(self, update: Update) -> bool:
        user = update.effective_user
        if user is None:
            return False
        allowed = self.settings.allowed_ids
        if user.id in allowed:
            return True
        self.db.log_request(user.id, "denied", update.effective_message.text or "<non-text>")
        log.warning("Rejected user %s (%s)", user.id, user.username)
        return False

    async def _reject(self, update: Update) -> None:
        user = update.effective_user
        if not self.settings.allowed_ids:
            # bootstrap: no one is allowed yet — tell the owner their ID
            await update.effective_message.reply_text(
                f"🔒 Not configured yet. Your Telegram user ID is {user.id}.\n"
                f"Add it to ALLOWED_USER_IDS in the .env file and restart."
            )
        else:
            await update.effective_message.reply_text("⛔ You are not authorized to use this bot.")

    # -- commands ------------------------------------------------------------
    async def cmd_start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        await update.message.reply_text(
            "🤖 *Kukku online.*\n\n"
            "Just talk to me. I can:\n"
            "• answer questions (LLM: " + self.provider_name + ")\n"
            "• 🔍 find files on your Mac — _\"find my resume pdf\"_\n"
            "• 📎 send them here — _\"send me that file\"_\n"
            "• 🖼 search screenshots by their text (OCR)\n"
            "• 💻 open apps/folders, lock, sleep, shutdown\n"
            "• 🌐 search the web when needed\n"
            "• 🧠 remember things — _\"remember that ...\"_\n"
            "• 🎙 accept voice notes\n\n"
            "Commands: /status /memory /clear /reindex",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def cmd_status(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        s = await asyncio.get_running_loop().run_in_executor(None, system_status)
        stats = self.db.stats_summary()
        await update.message.reply_text(
            f"🖥 CPU {s['cpu_percent']}%  ·  RAM {s['ram_percent']}% "
            f"({s['ram_used_gb']}/{s['ram_total_gb']} GB)  ·  Disk {s['disk_percent']}%\n"
            f"📚 {stats['files_indexed']} files indexed · {stats['chunks']} chunks · "
            f"{self.indexer.pending} pending\n"
            f"🧠 {stats['memories']} memories · {stats['messages']} messages logged\n"
            f"🤖 LLM: {self.provider_name}"
        )

    async def cmd_memory(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        memories = self.db.list_memories(limit=20)
        if not memories:
            return await update.message.reply_text("🧠 No memories saved yet.")
        lines = "\n".join(f"{m['id']}. {m['content']}" for m in memories)
        await update.message.reply_text(f"🧠 Memories:\n{lines}")

    async def cmd_clear(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        self.db.clear_history(update.effective_chat.id)
        await update.message.reply_text("🧹 Conversation history cleared.")

    async def cmd_reindex(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        await update.message.reply_text("🔄 Rescan started in the background.")
        asyncio.get_running_loop().run_in_executor(None, self.indexer.full_scan)

    # -- messages ------------------------------------------------------------
    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        await self._handle_query(update, context, update.message.text)

    async def on_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        if not self.transcriber:
            return await update.message.reply_text("🎙 Voice support is disabled (ENABLE_VOICE=false).")
        msg = update.message
        await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
        tg_file = await (msg.voice or msg.audio).get_file()
        dest = self.settings.data_dir / "voice" / f"{tg_file.file_unique_id}.oga"
        dest.parent.mkdir(exist_ok=True)
        await tg_file.download_to_drive(str(dest))
        try:
            text = await asyncio.get_running_loop().run_in_executor(
                None, self._transcribe_sync, dest
            )
        except RuntimeError as e:
            return await msg.reply_text(f"🎙 {e}")
        finally:
            dest.unlink(missing_ok=True)
        if not text:
            return await msg.reply_text("🎙 I couldn't hear anything in that note.")
        await msg.reply_text(f"🎙 _{text}_", parse_mode=ParseMode.MARKDOWN)
        await self._handle_query(update, context, text, kind="voice")

    def _transcribe_sync(self, path: Path) -> str:
        assert self.transcriber is not None
        return self.transcriber.transcribe(path)

    async def on_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        msg = update.message
        if msg.document:
            tg_file = await msg.document.get_file()
            name = msg.document.file_name or tg_file.file_unique_id
        else:
            tg_file = await msg.photo[-1].get_file()
            name = f"photo_{tg_file.file_unique_id}.jpg"
        dest = self.settings.inbox_dir / name
        await tg_file.download_to_drive(str(dest))
        self.indexer.enqueue(dest)
        self.db.log_request(update.effective_user.id, "file", f"received {name}")
        await msg.reply_text(f"📥 Saved to {dest} and queued for indexing.")
        if msg.caption:
            await self._handle_query(update, context, msg.caption)

    # -- core query flow ---------------------------------------------------
    async def _handle_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, kind: str = "text"
    ) -> None:
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        placeholder = await update.effective_message.reply_text("💭 …")

        last_edit = 0.0
        last_len = 0

        async def on_stream(accumulated: str) -> None:
            nonlocal last_edit, last_len
            now = time.monotonic()
            if now - last_edit < EDIT_INTERVAL or len(accumulated) - last_len < 40:
                return
            last_edit, last_len = now, len(accumulated)
            # BadRequest = message unchanged or edit race — harmless
            with contextlib.suppress(BadRequest):
                await placeholder.edit_text(accumulated[:4000] + " ▌")

        try:
            reply = await self.agent.run(chat_id, text, on_text=on_stream)
        except Exception as e:  # noqa: BLE001
            log.exception("agent failed")
            msg = str(e)
            if "429" in msg or "rate limited" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
                await placeholder.edit_text(
                    "⏳ The free AI quota is catching its breath (rate limit). "
                    "Wait a minute and ask me again."
                )
            else:
                # never expose stack traces / long API bodies to the chat
                detail = str(e).split("\n")[0][:120]
                await placeholder.edit_text(f"⚠️ Something went wrong ({type(e).__name__}: {detail}). Try again in a moment.")
            return

        await self._finalize(placeholder, reply.text)
        for path in reply.files_to_send:
            try:
                with path.open("rb") as fh:
                    await context.bot.send_document(chat_id, fh, filename=path.name)
            except Exception as e:  # noqa: BLE001
                await context.bot.send_message(chat_id, f"⚠️ Could not send {path.name}: {e}")

    @staticmethod
    async def _finalize(placeholder, text: str) -> None:
        """Final edit with Markdown; fall back to plain text if parsing fails."""
        text = text[:4000] if text else "Done."
        try:
            await placeholder.edit_text(text, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            with contextlib.suppress(BadRequest):  # identical content
                await placeholder.edit_text(text)

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("Telegram error: %s", context.error)

    # -- lifecycle ------------------------------------------------------------
    async def start(self, polling: bool = True) -> None:
        """polling=False when updates arrive via the cloud bridge instead."""
        self._polling = polling
        await self.app.initialize()
        await self.app.start()
        me = await self.app.bot.get_me()
        if polling:
            await self.app.updater.start_polling(drop_pending_updates=True)
            log.info("Bot @%s is polling", me.username)
        else:
            log.info("Bot @%s ready (cloud-bridge mode, no polling)", me.username)

    async def stop(self) -> None:
        if getattr(self, "_polling", True):
            await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
