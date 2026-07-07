"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Telegram
    telegram_bot_token: str = ""
    allowed_user_ids: str = ""

    # LLM — first configured wins: Claude > Gemini > Groq > OpenRouter > Ollama
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    ollama_model: str = ""
    ollama_url: str = "http://localhost:11434"
    # Provider try-order (comma-separated). Groq first keeps Gemini's smaller
    # free quota in reserve; Groq's free tier is far more generous.
    llm_priority: str = "groq,gemini,claude,openrouter,ollama"

    # Cloud relay (optional): set both to receive updates via the Cloudflare
    # Worker instead of polling — enables offline general-question answering.
    worker_url: str = ""
    bridge_secret: str = ""

    # Indexing
    index_dirs: str = "Desktop,Documents,Downloads,Projects,Pictures"
    max_file_size_mb: int = 25
    rescan_interval_min: int = 60
    enable_ocr: bool = True
    enable_voice: bool = True
    whisper_model: str = "base"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Proactive monitoring (all zero LLM cost)
    monitor_interval_min: int = 10
    alert_battery_pct: int = 20
    alert_disk_pct: int = 90
    backup_enabled: bool = True
    backup_keep: int = 7

    # Dashboard
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8788

    # Storage
    data_dir: Path = PROJECT_ROOT / "data"

    @field_validator("data_dir", mode="before")
    @classmethod
    def _resolve_data_dir(cls, v: str | Path) -> Path:
        p = Path(v).expanduser()
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def allowed_ids(self) -> set[int]:
        return {int(x) for x in self.allowed_user_ids.split(",") if x.strip().isdigit()}

    @property
    def index_paths(self) -> list[Path]:
        home = Path.home()
        out: list[Path] = []
        for raw in self.index_dirs.split(","):
            raw = raw.strip()
            if not raw:
                continue
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = home / p
            if p.is_dir():
                out.append(p)
        return out

    @property
    def owner_chat_id(self) -> int | None:
        """In Telegram private chats chat_id == user_id, so the first allowed
        id is where proactive alerts/briefings are sent."""
        ids = sorted(self.allowed_ids)
        return ids[0] if ids else None

    @property
    def db_path(self) -> Path:
        return self.data_dir / "jarvis.db"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def auth_path(self) -> Path:
        return self.data_dir / "auth.json"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def inbox_dir(self) -> Path:
        """Where files uploaded via Telegram are saved."""
        return self.data_dir / "inbox"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.log_dir, self.inbox_dir, self.chroma_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
