"""
Миграция для добавления колонок челленджей.
Запустить один раз: python -m database.migrate_challenges
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к БД
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "germanbuddy.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


async def migrate():
    """Добавляет новые колонки для системы челленджей."""
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Добавляем колонки в users (SQLite игнорирует NOT NULL без DEFAULT для ALTER)
        columns_to_add = [
            ("total_xp", "INTEGER DEFAULT 0"),
            ("challenge_streak", "INTEGER DEFAULT 0"),
            ("best_challenge_streak", "INTEGER DEFAULT 0"),
            ("last_challenge_date", "DATE"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                await conn.execute(text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                ))
                logger.info("✅ Added column: users.%s", col_name)
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.info("⏭️ Column users.%s already exists", col_name)
                else:
                    logger.warning("⚠️ %s: %s", col_name, e)
    
    await engine.dispose()
    logger.info("✅ Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
