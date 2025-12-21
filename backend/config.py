"""
Конфигурация приложения.
Загрузка переменных окружения.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram
    telegram_bot_token: str = Field(..., description="Telegram Bot Token", validation_alias="TELEGRAM_TOKEN")
    
    # Google AI
    google_api_key: str = Field(..., description="Google AI API Key")
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/germanbuddy",
        description="PostgreSQL connection URL"
    )
    
    # Redis (для кеширования, опционально)
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # API / Mini App URL
    api_base_url: str = Field(
        default="",
        description="Base URL for Mini App (must be HTTPS for Telegram)"
    )
    
    # App settings
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()
