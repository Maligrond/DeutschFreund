"""
Планировщик проактивных сообщений.
Бот пишет пользователю первым для возврата к практике.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, time
from typing import Optional, List

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.db import get_session_context
from database.models import User, Message as DBMessage, UserContext

logger = logging.getLogger(__name__)

# Глобальные объекты
scheduler: Optional[AsyncIOScheduler] = None
_bot: Optional[Bot] = None

# Константы
BATCH_SIZE = 50  # Максимум сообщений за раз
MESSAGE_DELAY = 1.0  # Секунд между сообщениями
QUIET_HOURS_START = 21  # Не отправлять после 21:00
QUIET_HOURS_END = 9  # Не отправлять до 9:00


def setup_scheduler(bot: Bot) -> None:
    """
    Настройка и запуск планировщика.
    
    Args:
        bot: Экземпляр Telegram бота
    """
    global scheduler, _bot
    _bot = bot
    
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    
    # Проверка неактивных пользователей каждые 12 часов
    scheduler.add_job(
        check_inactive_users,
        trigger=IntervalTrigger(hours=12),
        id="check_inactive_users",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=5)  # Первый запуск через 5 мин
    )
    
    # Проверка streak alerts (мягкое напоминание в 18:00)
    scheduler.add_job(
        send_streak_reminder_soft,
        trigger=CronTrigger(hour=18, minute=0),
        id="streak_reminder_soft",
        replace_existing=True,
    )
    
    # Срочное напоминание в 22:00
    scheduler.add_job(
        send_streak_reminder_urgent,
        trigger=CronTrigger(hour=22, minute=0),
        id="streak_reminder_urgent",
        replace_existing=True,
    )
    
    # Еженедельный итог (понедельник 9:00)
    scheduler.add_job(
        send_weekly_summary,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_summary",
        replace_existing=True,
    )
    
    # Утренняя отправка челленджей (проверяем каждые 30 мин с 6 до 12)
    scheduler.add_job(
        send_daily_challenges,
        trigger=CronTrigger(minute="0,30", hour="6-12"),
        id="send_daily_challenges",
        replace_existing=True,
    )
    
    # Напоминание о дедлайне челленджа (каждый час с 17 до 21)
    scheduler.add_job(
        send_challenge_reminders,
        trigger=CronTrigger(minute=0, hour="17-21"),
        id="challenge_reminders",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    """Остановка планировщика."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


async def check_inactive_users() -> None:
    """
    Проверка неактивных пользователей и отправка proactive messages.
    
    Логика:
    1. Получить пользователей где reminder_enabled = True
    2. last_message_date старше reminder_frequency дней
    3. last_proactive_message_date != сегодня (не более 1 в день)
    4. Сгенерировать персональное сообщение
    5. Отправить с rate limiting
    """
    if not _bot:
        logger.warning("Bot not initialized, skipping inactive users check")
        return
    
    # Проверка времени (не отправляем в тихие часы)
    now = datetime.now(timezone.utc)
    local_hour = (now.hour + 1) % 24  # Приблизительно Europe/Berlin
    
    if local_hour < QUIET_HOURS_END or local_hour >= QUIET_HOURS_START:
        logger.debug("Quiet hours (%d:00), skipping proactive messages", local_hour)
        return
    
    logger.info("Checking inactive users for proactive messages")
    
    sent_count = 0
    error_count = 0
    
    async with get_session_context() as session:
        # Получаем неактивных пользователей
        users = await _get_inactive_users(session, limit=BATCH_SIZE)
        
        if not users:
            logger.info("No inactive users found")
            return
        
        logger.info("Found %d inactive users", len(users))
        
        for user in users:
            try:
                # Генерируем и отправляем сообщение
                success = await _send_proactive_message(session, user)
                
                if success:
                    sent_count += 1
                    # Rate limiting
                    await asyncio.sleep(MESSAGE_DELAY)
                    
            except Exception as e:
                error_count += 1
                logger.error("Error sending proactive to %d: %s", user.user_id, str(e))
    
    logger.info(
        "Proactive messages: sent=%d, errors=%d",
        sent_count, error_count
    )


async def _get_inactive_users(session: AsyncSession, limit: int = 50) -> List[User]:
    """
    Получить список неактивных пользователей.
    
    Критерии:
    - reminder_enabled = True
    - last_message_date старше reminder_frequency дней
    - last_proactive_message_date != сегодня
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    
    # Базовый запрос
    query = select(User).where(
        User.reminder_enabled == True,
        User.last_message_date.isnot(None)
    ).limit(limit)
    
    result = await session.execute(query)
    all_users = result.scalars().all()
    
    # Фильтруем в Python (для сложной логики с reminder_frequency)
    inactive_users = []
    
    for user in all_users:
        # Проверяем, прошло ли reminder_frequency дней
        last_msg = user.last_message_date
        # Если дата в БД без таймзоны (sqlite), считаем её UTC
        if last_msg.tzinfo is None:
            last_msg = last_msg.replace(tzinfo=timezone.utc)
            
        days_inactive = (now - last_msg).days
        if days_inactive < user.reminder_frequency:
            continue
        
        # Проверяем, не отправляли ли уже сегодня
        if user.last_proactive_message_date:
            if user.last_proactive_message_date.date() == today:
                continue
        
        inactive_users.append(user)
    
    return inactive_users


async def _send_proactive_message(session: AsyncSession, user: User) -> bool:
    """
    Сгенерировать и отправить proactive message.
    
    Args:
        session: Database session
        user: Объект пользователя
    
    Returns:
        True если отправлено успешно
    """
    if not _bot:
        return False
    
    now = datetime.now(timezone.utc)
    
    # Получаем контекст
    last_topic = await _get_last_topic(session, user.user_id)
    user_context = await _get_user_context(session, user.user_id)
    
    # Вычисляем дни неактивности
    days_inactive = (now - user.last_message_date).days if user.last_message_date else 0
    
    # Генерируем сообщение
    message = await _generate_proactive_message(
        user=user,
        days_inactive=days_inactive,
        last_topic=last_topic,
        context=user_context
    )
    
    try:
        # Отправляем сообщение
        await _bot.send_message(user.user_id, message)
        
        # Обновляем дату proactive message
        user.last_proactive_message_date = now
        await session.commit()
        
        logger.info(
            "Sent proactive message to user %d (inactive %d days)",
            user.user_id, days_inactive
        )
        return True
        
    except TelegramForbiddenError:
        # Пользователь заблокировал бота
        logger.warning("User %d blocked the bot, disabling reminders", user.user_id)
        user.reminder_enabled = False
        await session.commit()
        return False
        
    except TelegramBadRequest as e:
        logger.warning("Bad request for user %d: %s", user.user_id, str(e))
        return False


async def _get_last_topic(session: AsyncSession, user_id: int) -> Optional[str]:
    """Получить последнюю тему разговора."""
    result = await session.execute(
        select(DBMessage)
        .where(DBMessage.user_id == user_id)
        .order_by(DBMessage.created_at.desc())
        .limit(5)
    )
    messages = result.scalars().all()
    
    if not messages:
        return None
    
    # Возвращаем последние сообщения как контекст
    topics = [m.content[:100] for m in messages if m.role == "user"]
    return " | ".join(topics[:3]) if topics else None


async def _get_user_context(session: AsyncSession, user_id: int) -> Optional[dict]:
    """Получить контекст пользователя."""
    context = await session.get(UserContext, user_id)
    return context.context_data if context else None


async def _generate_proactive_message(
    user: User,
    days_inactive: int,
    last_topic: Optional[str],
    context: Optional[dict]
) -> str:
    """
    Генерация персонального proactive message через Gemini.
    
    Args:
        user: Объект пользователя
        days_inactive: Дней неактивности
        last_topic: Последняя тема разговора
        context: Контекст пользователя
    
    Returns:
        Текст сообщения
    """
    try:
        from .gemini_client import get_gemini_client
        import google.generativeai as genai
        
        # Формируем контекст для промпта
        context_str = ""
        if context:
            context_parts = []
            if context.get("name"):
                context_parts.append(f"Имя: {context['name']}")
            if context.get("city"):
                context_parts.append(f"Город: {context['city']}")
            if context.get("job"):
                context_parts.append(f"Работа: {context['job']}")
            if context.get("interests"):
                context_parts.append(f"Интересы: {', '.join(context['interests'])}")
            context_str = "; ".join(context_parts)
        
        prompt = f"""Пользователь не писал {days_inactive} дней.
Последние темы разговора: {last_topic or "неизвестно"}
Контекст пользователя: {context_str or "нет данных"}
Имя пользователя: {user.first_name}

Напиши короткое дружеское сообщение (2-3 предложения), 
чтобы мягко вернуть его к практике немецкого.

Можешь:
- Спросить как дела
- Напомнить о чем говорили
- Предложить новую тему
- Быть поддерживающим

НЕ пиши: "Давай учить немецкий!" (слишком навязчиво)
НЕ используй слова: "напоминаю", "ты забыл", "пора практиковаться"
Пиши как настоящий друг, которому интересно.

Ответ только текст сообщения, без кавычек и пояснений."""

        # Используем Gemini для генерации
        gemini = get_gemini_client()
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        
        message = response.text.strip()
        
        # Проверка длины
        if len(message) > 500:
            message = message[:500] + "..."
        
        return message
        
    except Exception as e:
        logger.warning("Failed to generate proactive message: %s", str(e))
        # Fallback на шаблонные сообщения
        return _get_fallback_message(user, days_inactive)


def _get_fallback_message(user: User, days_inactive: int) -> str:
    """
    Fallback сообщения если Gemini недоступен.
    
    Args:
        user: Объект пользователя
        days_inactive: Дней неактивности
    
    Returns:
        Текст сообщения
    """
    name = user.first_name or "друг"
    
    messages = [
        f"Привет, {name}! 👋 Давно не общались. Как дела?",
        
        f"Привет! 😊 Соскучился по нашим разговорам. Что нового?",
        
        f"Эй, {name}! Как поживаешь? Расскажи как прошла неделя!",
        
        f"Hallo! 🇩🇪 Как твои дела? Может поболтаем немного?",
        
        f"Привет, {name}! Надеюсь у тебя всё хорошо. Напиши когда будет время! 😊",
    ]
    
    # Выбираем сообщение на основе user_id
    index = user.user_id % len(messages)
    return messages[index]


async def send_streak_reminder_soft() -> None:
    """
    Мягкое напоминание о streak (18:00).
    Отправляется пользователям, которые ещё не достигли цели дня.
    """
    if not _bot:
        return
    
    from .streak_service import MIN_MESSAGES_PER_DAY, format_streak_reminder_soft
    
    logger.info("Sending soft streak reminders (18:00)")
    
    now = datetime.now(timezone.utc)
    today = now.date()
    sent_count = 0
    
    async with get_session_context() as session:
        # Пользователи с включенными напоминаниями и streak > 0
        result = await session.execute(
            select(User).where(
                User.streak_reminder_enabled == True,
                User.streak_days >= 1,
                User.daily_messages_count < MIN_MESSAGES_PER_DAY
            ).limit(100)
        )
        users = result.scalars().all()
        
        for user in users:
            try:
                message = format_streak_reminder_soft(user)
                if not message:
                    continue
                
                await _bot.send_message(
                    user.user_id,
                    message,
                    parse_mode="Markdown"
                )
                sent_count += 1
                await asyncio.sleep(0.5)
                
            except TelegramForbiddenError:
                user.streak_reminder_enabled = False
            except Exception as e:
                logger.warning("Failed to send soft reminder to %d: %s", user.user_id, str(e))
        
        await session.commit()
    
    if sent_count > 0:
        logger.info("Sent %d soft streak reminders", sent_count)


async def send_streak_reminder_urgent() -> None:
    """
    Срочное напоминание о streak (22:00).
    Осталось 2 часа до полуночи!
    """
    if not _bot:
        return
    
    from .streak_service import MIN_MESSAGES_PER_DAY, format_streak_reminder_urgent
    
    logger.info("Sending urgent streak reminders (22:00)")
    
    sent_count = 0
    
    async with get_session_context() as session:
        # Пользователи, которые ещё не достигли цели и имеют streak
        result = await session.execute(
            select(User).where(
                User.streak_reminder_enabled == True,
                User.streak_days >= 3,  # Только для streak >= 3 дней
                User.daily_messages_count < MIN_MESSAGES_PER_DAY
            ).limit(100)
        )
        users = result.scalars().all()
        
        for user in users:
            try:
                message = format_streak_reminder_urgent(user)
                if not message:
                    continue
                
                await _bot.send_message(
                    user.user_id,
                    message,
                    parse_mode="Markdown"
                )
                sent_count += 1
                await asyncio.sleep(0.5)
                
            except TelegramForbiddenError:
                user.streak_reminder_enabled = False
            except Exception as e:
                logger.warning("Failed to send urgent reminder to %d: %s", user.user_id, str(e))
        
        await session.commit()
    
    if sent_count > 0:
        logger.info("Sent %d urgent streak reminders", sent_count)


async def send_weekly_summary() -> None:
    """
    Еженедельный итог (понедельник 9:00).
    Позиция в leaderboard, XP за неделю, streak.
    """
    if not _bot:
        return
    
    logger.info("Sending weekly summaries")
    
    sent_count = 0
    
    async with get_session_context() as session:
        # Пользователи с активностью за неделю
        result = await session.execute(
            select(User).where(
                User.weekly_xp > 0,
                User.streak_reminder_enabled == True
            ).order_by(User.weekly_xp.desc()).limit(100)
        )
        users = result.scalars().all()
        
        # Получаем топ-3 для отображения
        top3_result = await session.execute(
            select(User).where(
                User.weekly_xp > 0,
                User.is_anonymous_leaderboard == False
            ).order_by(User.weekly_xp.desc()).limit(3)
        )
        top3 = top3_result.scalars().all()
        
        top3_text = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(top3):
            name = u.username or u.first_name or f"User{u.user_id}"
            top3_text += f"{medals[i]} {name} - {u.weekly_xp} XP\n"
        
        for i, user in enumerate(users):
            try:
                rank = i + 1
                
                # Проверяем, в топе ли пользователь
                is_in_top3 = rank <= 3
                
                message = (
                    f"📊 *Итоги недели!*\n\n"
                    f"🏆 Твоя позиция: *#{rank}*\n"
                    f"⭐ Заработано XP: {user.weekly_xp}\n"
                    f"🔥 Streak: {user.streak_days} дней\n\n"
                )
                
                if is_in_top3:
                    message += f"🎉 *Ты в топ-3!* Поздравляем!\n\n"
                elif top3:
                    message += f"*Топ-3:*\n{top3_text}\n"
                    gap = top3[0].weekly_xp - user.weekly_xp if top3 else 0
                    if gap > 0:
                        message += f"До 1 места: {gap} XP 💪\n"
                
                message += "\nУдачи на этой неделе! 🌟"
                
                await _bot.send_message(
                    user.user_id,
                    message,
                    parse_mode="Markdown"
                )
                
                # Сбрасываем weekly_xp
                user.weekly_xp = 0
                
                sent_count += 1
                await asyncio.sleep(0.5)
                
            except TelegramForbiddenError:
                user.streak_reminder_enabled = False
            except Exception as e:
                logger.warning("Failed to send weekly summary to %d: %s", user.user_id, str(e))
        
        await session.commit()
    
    if sent_count > 0:
        logger.info("Sent %d weekly summaries", sent_count)


async def check_streak_alerts() -> None:
    """
    Legacy: Проверка streak и отправка предупреждений.
    Предупреждает пользователей, которые могут потерять streak сегодня.
    """
    # Теперь заменено на send_streak_reminder_soft и send_streak_reminder_urgent
    pass


async def send_custom_message(user_id: int, message: str) -> bool:
    """
    Отправка кастомного сообщения пользователю.
    
    Args:
        user_id: ID пользователя Telegram
        message: Текст сообщения
    
    Returns:
        True если отправлено успешно
    """
    if not _bot:
        return False
    
    try:
        await _bot.send_message(user_id, message)
        return True
    except Exception as e:
        logger.warning("Failed to send message to %d: %s", user_id, str(e))
        return False


# ============ CHALLENGE SCHEDULER FUNCTIONS ============

async def send_daily_challenges() -> None:
    """
    Отправка утренних уведомлений о челленджах.
    Проверяет пользователей, у которых включены челленджи и наступило время уведомления.
    """
    if not _bot:
        logger.warning("Bot not initialized, skipping daily challenges")
        return
    
    from database.models import ChallengeSettings
    from .challenges import (
        get_or_create_todays_challenge, format_challenge_message, get_todays_challenge
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    from config import settings
    
    now = datetime.now(timezone.utc)
    # Europe/Berlin примерно UTC+1/+2
    local_hour = (now.hour + 1) % 24
    local_minute = now.minute
    current_time = f"{local_hour:02d}:{local_minute // 30 * 30:02d}"  # Округляем до 30 мин
    
    logger.info("Checking daily challenges for time ~%s", current_time)
    
    sent_count = 0
    error_count = 0
    
    async with get_session_context() as session:
        # Получаем пользователей с включёнными челленджами
        result = await session.execute(
            select(ChallengeSettings, User).join(
                User, ChallengeSettings.user_id == User.user_id
            ).where(ChallengeSettings.enabled == True)
        )
        rows = result.all()
        
        for settings_row, user in rows:
            try:
                # Проверяем время уведомления
                notif_hour, notif_minute = map(int, settings_row.notification_time.split(":"))
                
                # Проверяем, что текущее время примерно соответствует
                if abs(local_hour - notif_hour) > 0:
                    continue
                if abs(local_minute - notif_minute) > 30:
                    continue
                
                # Проверяем, нет ли уже сегодняшнего челленджа
                existing = await get_todays_challenge(session, user.user_id)
                if existing and existing.completed:
                    # Уже выполнен
                    continue
                
                if existing:
                    # Челлендж уже создан, не отправляем повторно
                    # (проверяем, что created_at сегодня и было недавно)
                    if existing.created_at.date() == now.date():
                        created_minutes_ago = (now - existing.created_at).total_seconds() / 60
                        if created_minutes_ago < 60:  # Создан менее часа назад
                            continue
                
                # Создаём или получаем челлендж
                challenge = await get_or_create_todays_challenge(session, user)
                if not challenge:
                    continue
                
                # Форматируем сообщение
                message = format_challenge_message(challenge, user)
                
                # Клавиатура
                MINI_APP_URL = settings.api_base_url.replace("/api", "")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🚀 Начать", callback_data="challenge_start"),
                        InlineKeyboardButton(text="⏰ Позже", callback_data="challenge_remind"),
                    ],
                    [
                        InlineKeyboardButton(
                            text="⚙️ Настройки",
                            web_app=WebAppInfo(url=f"{MINI_APP_URL}/challenges")
                        ),
                    ]
                ])
                
                await _bot.send_message(
                    user.user_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                sent_count += 1
                await asyncio.sleep(MESSAGE_DELAY)
                
            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                settings_row.enabled = False
                error_count += 1
            except Exception as e:
                error_count += 1
                logger.error("Error sending challenge to %d: %s", user.user_id, str(e))
        
        await session.commit()
    
    if sent_count > 0 or error_count > 0:
        logger.info("Daily challenges: sent=%d, errors=%d", sent_count, error_count)


async def send_challenge_reminders() -> None:
    """
    Отправка напоминаний о дедлайне челленджа.
    Вызывается каждый час с 17 до 21.
    """
    if not _bot:
        return
    
    from database.models import UserChallenge, ChallengeSettings
    from datetime import date
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    today = date.today()
    now = datetime.now(timezone.utc)
    local_hour = (now.hour + 1) % 24  # Europe/Berlin approx
    
    # Напоминаем только если осталось 2-4 часа до 21:00
    hours_left = 21 - local_hour
    if hours_left < 1 or hours_left > 4:
        return
    
    logger.info("Checking challenge reminders, ~%d hours until deadline", hours_left)
    
    sent_count = 0
    
    async with get_session_context() as session:
        # Пользователи с невыполненными челленджами сегодня
        result = await session.execute(
            select(UserChallenge, User).join(
                User, UserChallenge.user_id == User.user_id
            ).where(
                UserChallenge.challenge_date == today,
                UserChallenge.completed == False
            )
        )
        rows = result.all()
        
        for challenge, user in rows:
            try:
                # Проверяем, что у пользователя включены челленджи
                settings = await session.get(ChallengeSettings, user.user_id)
                if not settings or not settings.enabled:
                    continue
                
                message = (
                    f"⏰ *Напоминание!*\n\n"
                    f"Осталось ~{hours_left} часа до конца челленджа!\n"
                    f"Не прерывай свой streak 🔥\n\n"
                    f"Челлендж: _{challenge.title}_"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Выполнить сейчас", callback_data="challenge_start")]
                ])
                
                await _bot.send_message(
                    user.user_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                sent_count += 1
                await asyncio.sleep(0.5)
                
            except TelegramForbiddenError:
                pass
            except Exception as e:
                logger.error("Error sending reminder to %d: %s", user.user_id, str(e))
    
    if sent_count > 0:
        logger.info("Challenge reminders sent: %d", sent_count)

