from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


load_dotenv(dotenv_path=_ENV_FILE, override=True)


class Settings(BaseSettings):
    

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

   
    APP_ENV: str = "development"
    APP_TITLE: str = "GRAVITY Backend for EklavyaX"
    APP_VERSION: str = "1.0.0"

  
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eklavyax"

  
    SECRET_KEY: str = "CHANGE_ME_use_a_long_random_string_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    
    AI_PROVIDER: str = "groq"           
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-oss-120b"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "openai/gpt-oss-120b"

   
    AI_EXPLAIN_COST: int = 10            # EduCoins charged per AI explain call
    AI_REFUND_COINS: int = 5             # Coins refunded on correct answer
    STREAK_BONUS_COINS: int = 5          # Daily streak reward
    STREAK_BONUS_XP: int = 10            # Daily streak XP
    BOUNTY_COMPLETION_XP: int = 50       # XP for completing a bounty
    NEW_USER_COINS: int = 100            # Starting wallet balance

   
    QUESTION_MIN_COOLDOWN_SECONDS: float = 2.0    # Min seconds before answer accepted
    DAILY_MAX_COINS: int = 500                     # Max coins earnable per day via quizzes
    DAILY_MAX_XP: int = 1000                       # Max XP earnable per day via quizzes
    CAP_EXCEEDED_POLICY: str = "reduced"            # "reject" | "zero" | "reduced"
    CAP_REDUCTION_FACTOR: float = 0.25              # Multiplier when policy is "reduced"
    ROLLING_WINDOW_SIZE: int = 20                   # Questions in rolling pattern window
    Z_SCORE_FLAG_THRESHOLD: float = 2.5             # Z-score above which user is flagged

  
    QUIZ_CORRECT_COINS: int = 10         # Coins per correct quiz answer
    QUIZ_CORRECT_XP: int = 20            # XP per correct quiz answer
    QUIZ_DEFAULT_SIZE: int = 10           # Default questions per quiz

  
    FACTION_WAR_POLL_INTERVAL_SECONDS: int = 5
    FACTION_WAR_LOSER_PARTICIPATION_COINS: int = 15
    FACTION_WAR_LOSER_PARTICIPATION_XP: int = 25
    FACTION_WAR_WINNER_BONUS_COINS: int = 50
    FACTION_WAR_WINNER_BONUS_XP: int = 100

    REFERRAL_BONUS_COINS: int = 50
    REFERRAL_BONUS_XP: int = 100

   
    CORS_ORIGINS: str = (
        "*,http://localhost:3000,http://localhost:5173,http://localhost:5500,"
        "http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:8080"
    )

   
    REDIS_URL: Optional[str] = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        """Accept comma-separated string."""
        return v

    def get_cors_origins(self) -> List[str]:
        """Return CORS origins as a list."""
        if "*" in self.CORS_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
