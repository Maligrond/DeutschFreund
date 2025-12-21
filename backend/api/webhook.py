import os
import logging
from fastapi import APIRouter, Request, BackgroundTasks
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from bot.handlers import router as bot_router
from bot.placement_test import router as placement_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telegram Webhook"])

# Инициализация бота для Webhook
# Важно: создаём объекты тут, но лучше вынести в зависимость
bot = Bot(token=settings.telegram_token)
dp = Dispatcher(storage=MemoryStorage()) # В serverless лучше использовать RedisStorage, но пока Memory
dp.include_router(bot_router)
dp.include_router(placement_router)

# Секрет для защиты вебхука
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "germanbuddy-secret")

@router.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint для получения обновлений от Telegram (Webhook).
    """
    # Проверка секрета (опционально, но рекомендуется)
    secret = request.query_params.get("secret")
    if secret != WEBHOOK_SECRET:
        return {"status": "error", "message": "Invalid secret"}
        
    try:
        data = await request.json()
        update = types.Update(**data)
        
        # Обработка обновления
        # В Vercel важно быстро ответить OK, поэтому обработку запускаем в фоне
        # Но Vercel может убить процесс сразу после ответа.
        # Для простых ботов await dp.feed_update работает быстро.
        
        await dp.feed_update(bot, update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.get("/webhook/set")
async def set_webhook(url: str):
    """
    Установить Webhook URL.
    Вызывать один раз после деплоя.
    Пример: /api/webhook/set?url=https://your-app.vercel.app/api/webhook/telegram
    """
    webhook_url = f"{url}?secret={WEBHOOK_SECRET}"
    await bot.set_webhook(webhook_url)
    return {"status": "ok", "url": webhook_url}
