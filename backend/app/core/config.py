"""
app/core/config.py
──────────────────
Central configuration using pydantic-settings.
All settings are read from environment variables (or .env file).
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file relative to this file's location so it always loads
# correctly regardless of where uvicorn/the process is launched from.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Force-load the .env into os.environ BEFORE pydantic-settings instantiates
# Settings(). This guarantees the key is available even if pydantic-settings
# has trouble resolving the env_file path.
load_dotenv(dotenv_path=_ENV_FILE, override=True)


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_TITLE: str = "Synapse Backend for EklavyaX"
    APP_VERSION: str = "1.0.0"

    # ── Database ─────────────────────────────────────────────────────────────
    # Configured for PostgreSQL by default. Can be customized via .env.
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eklavyax"

    # ── JWT / Security ───────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_use_a_long_random_string_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── AI Provider ──────────────────────────────────────────────────────────
    AI_PROVIDER: str = "openrouter"      # "openrouter" | "gemini" | "openai"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemma-4-26b-a4b-it:free"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Economy Tuning ───────────────────────────────────────────────────────
    AI_EXPLAIN_COST: int = 10            # EduCoins charged per AI explain call
    AI_REFUND_COINS: int = 5             # Coins refunded on correct answer
    STREAK_BONUS_COINS: int = 5          # Daily streak reward
    STREAK_BONUS_XP: int = 10            # Daily streak XP
    BOUNTY_COMPLETION_XP: int = 50       # XP for completing a bounty
    NEW_USER_COINS: int = 100            # Starting wallet balance

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Not needed when the backend serves the frontend itself (same origin),
    # but kept permissive for local dev servers / Live Server setups.
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:5500,"
        "http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:8080"
    )

    # ── Redis (optional) ─────────────────────────────────────────────────────
    REDIS_URL: Optional[str] = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        """Accept comma-separated string."""
        return v

    def get_cors_origins(self) -> List[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Singleton – import this everywhere instead of instantiating Settings again.
settings = Settings()
