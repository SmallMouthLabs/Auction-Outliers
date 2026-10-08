"""Application configuration.

Secrets (API keys, IMAP passwords) are read from environment variables / .env only.
They are never stored in the database and never returned by the API.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_prefix="OUTLIER_",
        extra="ignore",
    )

    # --- storage ---
    data_dir: Path = Field(default=BACKEND_DIR / "data")
    database_url: str | None = None  # defaults to sqlite in data_dir

    # --- server ---
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    run_worker: bool = True
    worker_poll_seconds: float = 2.0
    log_level: str = "INFO"

    # --- AI providers (secrets come from un-prefixed env vars, see below) ---
    triage_provider: str = "auto"  # auto | anthropic | gemini | demo
    triage_model: str | None = None
    deep_provider: str = "auto"
    deep_model: str | None = None
    daily_budget_usd: float = 5.0
    per_listing_budget_usd: float = 0.50
    max_zoom_calls: int = 6
    max_images_per_call: int = 8
    triage_image_max_px: int = 768
    deep_image_max_px: int = 1568

    # --- ingestion ---
    enable_unofficial_sgw_api: bool = False  # see docs/research.md before enabling
    sgw_user_agent: str = "OUTLIER-sourcing-tool/0.1 (personal, read-only, rate-limited)"
    sgw_min_request_interval_seconds: float = 5.0
    webhook_token: str | None = None

    # --- email (Personal Shopper notifications) ---
    imap_host: str | None = None
    imap_port: int = 993
    imap_user: str | None = None
    imap_folder: str = "INBOX"
    imap_subject_filter: str = "Personal Shopper"

    # --- user context ---
    buyer_zip: str | None = None
    buyer_state_sales_tax_rate: float = 0.0

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "outlier.sqlite3"

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.sqlite_path}"

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


class Secrets(BaseSettings):
    """API credentials. Read from env only. Never persisted, never serialized to clients."""

    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    ebay_client_id: str | None = Field(default=None, alias="EBAY_CLIENT_ID")
    ebay_client_secret: str | None = Field(default=None, alias="EBAY_CLIENT_SECRET")
    imap_password: str | None = Field(default=None, alias="OUTLIER_IMAP_PASSWORD")

    def configured(self) -> dict[str, bool]:
        return {
            "anthropic": bool(self.anthropic_api_key),
            "gemini": bool(self.gemini_api_key),
            "ebay": bool(self.ebay_client_id and self.ebay_client_secret),
            "imap": bool(self.imap_password),
        }


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.images_dir.mkdir(parents=True, exist_ok=True)
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    return s


@lru_cache
def get_secrets() -> Secrets:
    return Secrets()


def reset_caches() -> None:
    get_settings.cache_clear()
    get_secrets.cache_clear()
