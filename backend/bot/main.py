"""
Точка входа Telegram бота для изучения немецкого языка.
"""

import asyncio
import logging
import sys
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from database.db import init_db, close_db
from .handlers import router
from .placement_test import router as placement_router
from .gemini_client import init_gemini_client
from .scheduler import setup_scheduler, shutdown_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

# Глобальные объекты
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None


async def on_startup() -> None:
    """Действия при запуске бота."""
    logger.info("Starting bot...")
    
    # Инициализация базы данных
    await init_db()
    logger.info("Database initialized")
    
    # Инициализация Gemini клиента
    init_gemini_client(settings.google_api_key)
    logger.info("Gemini client initialized")
    
    # Запуск планировщика
    setup_scheduler(bot)
    logger.info("Scheduler started")
    
    logger.info("Bot started successfully!")


async def on_shutdown() -> None:
    """Действия при остановке бота."""
    logger.info("Shutting down bot...")
    
    # Остановка планировщика
    shutdown_scheduler()
    
    # Закрытие соединения с БД
    await close_db()
    
    logger.info("Bot stopped")


async def main() -> None:
    """Основная функция запуска бота."""
    global bot, dp
    
    # Создание бота
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создание диспетчера
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(router)
    dp.include_router(placement_router)
    
    # Регистрация событий жизненного цикла
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        # Удаление вебхука (если был) и запуск polling
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def run_bot() -> None:
    """Запуск бота (entry point)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Bot crashed: %s", str(e))
        raise


if __name__ == "__main__":
    run_bot()
