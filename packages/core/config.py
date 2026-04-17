"""
Centralized configuration management.
Reads from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # ─── App ──────────────────────────
    ENV: str = "development"
    APP_NAME: str = "Grant Path AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── API ──────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    APP_DOMAIN: str = "localhost"

    # ─── Database ─────────────────────
    DATABASE_URL: str = "postgresql://postgres:devpassword@localhost:5432/grantpath"

    # ─── Redis ────────────────────────
    REDIS_URL: Optional[str] = None

    # ─── Auth ─────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # ─── AI: Gemini (Required) ────────
    GEMINI_API_KEY: str = ""

    # ─── AI: Groq (Recommended) ───────
    GROQ_API_KEY: Optional[str] = None

    # ─── AI: OpenAI (Optional) ────────
    OPENAI_API_KEY: Optional[str] = None

    # ─── AI: Local Models ─────────────
    MODEL_SERVICE_URL: str = "http://localhost:8001"
    MODEL_DEVICE: str = "cpu"

    # ─── Token Budgets ────────────────
    DAILY_PREMIUM_TOKEN_BUDGET: int = 50000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.ENV == "development"

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_redis(self) -> bool:
        return bool(self.REDIS_URL)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
