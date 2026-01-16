"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    
    # LLM Providers
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./stock_bot.db",
        env="DATABASE_URL"
    )
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # News APIs
    NEWSAPI_KEY: Optional[str] = Field(default=None, env="NEWSAPI_KEY")
    GNEWS_API_KEY: Optional[str] = Field(default=None, env="GNEWS_API_KEY")
    
    # Optional data sources
    ALPHA_VANTAGE_KEY: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_KEY")
    
    # App Settings
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Cache TTLs (seconds)
    PRICE_CACHE_TTL: int = 300  # 5 minutes
    HISTORICAL_CACHE_TTL: int = 3600  # 1 hour
    FUNDAMENTAL_CACHE_TTL: int = 86400  # 24 hours
    NEWS_CACHE_TTL: int = 900  # 15 minutes
    
    # LLM Settings
    PRIMARY_LLM_MODEL: str = "gemini-2.5-flash"
    FALLBACK_LLM_MODEL: str = "arcee-ai/trinity-mini:free"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 8000
    
    # Rate Limits
    MAX_REQUESTS_PER_MINUTE: int = 30
    MAX_CONCURRENT_ANALYSES: int = 5
    
    # Timeouts (seconds)
    DATA_COLLECTION_TIMEOUT: int = 10
    SINGLE_AGENT_TIMEOUT: int = 15
    FULL_ANALYSIS_TIMEOUT: int = 45
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Check if .env exists, if not use environment variables
if not os.path.exists(".env"):
    # Try to load from environment
    pass

settings = get_settings()
