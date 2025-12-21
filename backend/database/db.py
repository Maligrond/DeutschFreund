"""
Подключение к базе данных.
Использует SQLite для простоты (легко переключить на PostgreSQL).
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

import os
import urllib.parse

# База данных
# Если задана переменная DATABASE_URL (например, на Vercel/Render), используем её.
# Иначе fallback на локальный SQLite.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # SQLite для локальной разработки (или fallback)
    try:
        DB_PATH = Path(__file__).parent.parent / "data" / "germanbuddy.db"
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback для Read-Only файловых систем (например, Vercel без DATABASE_URL)
        DB_PATH = Path("/tmp/germanbuddy.db")
    
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Fix for Vercel/Neon which provides postgres:// but SQLAlchemy needs postgresql+asyncpg://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Fix for "TypeError: connect() got an unexpected keyword argument 'sslmode'"
# asyncpg doesn't support 'sslmode' in URL query params, must be passed in connect_args or as 'ssl' context
CONNECT_ARGS = {}
if DATABASE_URL and "sslmode" in DATABASE_URL:
    try:
        url_parts = urllib.parse.urlparse(DATABASE_URL)
        qs = urllib.parse.parse_qs(url_parts.query)
        # If sslmode is present, remove it from URL and enable SSL in connect_args
        if 'sslmode' in qs:
            sslmode_val = qs.pop('sslmode')[0]
            if sslmode_val == 'require':
                CONNECT_ARGS['ssl'] = 'require'
            
            # Rebuild URL without sslmode
            new_query = urllib.parse.urlencode(qs, doseq=True)
            DATABASE_URL = urllib.parse.urlunparse(url_parts._replace(query=new_query))
    except Exception as e:
        logger.error(f"Failed to parse or fix DATABASE_URL: {e}")


# Engine и Session
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Базовый класс для моделей."""
    pass


async def init_db() -> None:
    """Инициализация базы данных."""
    global engine, async_session_factory
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args=CONNECT_ARGS,
    )
    
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Создаём таблицы
    async with engine.begin() as conn:
        from .models import (
            User, Message, UserContext, Vocabulary, VoicePractice,
            ChallengeSettings, UserChallenge, UserBadge
        )
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized.")


async def close_db() -> None:
    """Закрытие соединения с базой данных."""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI - получение сессии."""
    if not async_session_factory:
        raise RuntimeError("Database not initialized")
    
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Контекстный менеджер для получения сессии (для бота/scheduler)."""
    if not async_session_factory:
        raise RuntimeError("Database not initialized")
    
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
