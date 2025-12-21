"""
Сервис для управления streak системой.
Обрабатывает логику streak, награды, freeze и уведомления.
"""

import logging
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserBadge, StreakReward

logger = logging.getLogger(__name__)

# ============ КОНФИГУРАЦИЯ ============

MIN_MESSAGES_PER_DAY = 1  # минимум сообщений для засчитывания дня

# Milestone награды
STREAK_MILESTONES: Dict[int, Dict[str, Any]] = {
    3: {
        "badge_id": "streak_starter",
        "name": "🌱 Starter",
        "emoji": "🌱",
        "description": "3 дня подряд",
        "xp": 50,
        "premium_days": 0,
        "freeze": 0,
    },
    7: {
        "badge_id": "streak_week_warrior",
        "name": "⚔️ Week Warrior",
        "emoji": "⚔️",
        "description": "Неделя практики",
        "xp": 100,
        "premium_days": 0,
        "freeze": 1,
    },
    14: {
        "badge_id": "streak_two_weeks",
        "name": "🔥 Two Weeks",
        "emoji": "🔥",
        "description": "Две недели без пропусков",
        "xp": 200,
        "premium_days": 0,
        "freeze": 1,
    },
    30: {
        "badge_id": "streak_monthly",
        "name": "🏆 Monthly Master",
        "emoji": "🏆",
        "description": "Месяц ежедневной практики",
        "xp": 500,
        "premium_days": 3,
        "freeze": 0,
    },
    50: {
        "badge_id": "streak_dedicated",
        "name": "💎 Dedicated",
        "emoji": "💎",
        "description": "50 дней — настоящая преданность",
        "xp": 1000,
        "premium_days": 7,
        "freeze": 0,
    },
    100: {
        "badge_id": "streak_legend",
        "name": "👑 Legend",
        "emoji": "👑",
        "description": "100 дней — ты легенда!",
        "xp": 2000,
        "premium_days": 30,
        "freeze": 0,
    },
}


# ============ ОСНОВНЫЕ ФУНКЦИИ ============

async def increment_daily_messages(session: AsyncSession, user: User) -> int:
    """
    Увеличить счётчик сообщений за день.
    Возвращает новый счётчик.
    """
    today = date.today()
    
    # Если новый день — сбрасываем счётчик
    if user.last_daily_reset != today:
        user.daily_messages_count = 0
        user.last_daily_reset = today
    
    user.daily_messages_count += 1
    
    logger.debug(
        "User %d: daily messages = %d/%d",
        user.user_id, user.daily_messages_count, MIN_MESSAGES_PER_DAY
    )
    
    return user.daily_messages_count


async def check_and_update_streak(session: AsyncSession, user: User) -> Dict[str, Any]:
    """
    Проверить и обновить streak пользователя.
    Вызывается при каждом сообщении.
    
    Returns:
        Dict с информацией о streak: 
        - streak_updated: bool
        - new_streak: int
        - milestone_reached: Optional[int]
        - reward: Optional[dict]
    """
    result = {
        "streak_updated": False,
        "new_streak": user.streak_days,
        "milestone_reached": None,
        "reward": None,
        "daily_goal_reached": False,
    }
    
    today = date.today()
    
    # Проверяем достигнута ли цель дня
    if user.daily_messages_count >= MIN_MESSAGES_PER_DAY:
        result["daily_goal_reached"] = True
        
        # Проверяем нужно ли обновить streak
        if user.last_message_date is None:
            # Первый день
            user.streak_days = 1
            user.streak_start_date = today
            user.best_streak = max(user.best_streak, 1)
            result["streak_updated"] = True
            result["new_streak"] = 1
            
        elif user.last_message_date.date() == today:
            # Тот же день — streak не меняется, но проверяем milestone
            pass
            
        elif user.last_message_date.date() == today - timedelta(days=1):
            # Вчера — увеличиваем streak
            user.streak_days += 1
            user.best_streak = max(user.best_streak, user.streak_days)
            result["streak_updated"] = True
            result["new_streak"] = user.streak_days
            
        else:
            # Пропустили дни — проверяем freeze
            freeze_used = await _check_and_use_freeze(session, user, today)
            
            if freeze_used:
                # Streak сохранён благодаря freeze
                user.streak_days += 1
                user.best_streak = max(user.best_streak, user.streak_days)
                result["streak_updated"] = True
                result["new_streak"] = user.streak_days
                result["freeze_used"] = True
            else:
                # Streak сбрасывается
                user.streak_days = 1
                user.streak_start_date = today
                result["streak_updated"] = True
                result["new_streak"] = 1
                result["streak_reset"] = True
        
        # Проверяем milestone
        milestone = await check_streak_milestone(session, user)
        if milestone:
            result["milestone_reached"] = milestone["day"]
            result["reward"] = milestone
    
    return result


async def _check_and_use_freeze(session: AsyncSession, user: User, today: date) -> bool:
    """
    Проверить и использовать streak freeze если доступен.
    
    Returns:
        True если freeze был использован
    """
    if user.streak_freeze_available <= 0:
        return False
    
    # Проверяем не использовался ли freeze сегодня
    if user.streak_freeze_used_at and user.streak_freeze_used_at.date() == today:
        return False
    
    # Используем freeze
    user.streak_freeze_available -= 1
    user.streak_freeze_used_at = datetime.now(timezone.utc)
    
    logger.info(
        "User %d: streak freeze used. Remaining: %d",
        user.user_id, user.streak_freeze_available
    )
    
    return True


async def check_streak_milestone(session: AsyncSession, user: User) -> Optional[Dict[str, Any]]:
    """
    Проверить достиг ли пользователь нового milestone и выдать награду.
    
    Returns:
        Dict с информацией о награде или None
    """
    current_streak = user.streak_days
    
    # Находим milestone который нужно проверить
    milestone_day = None
    for day in sorted(STREAK_MILESTONES.keys()):
        if current_streak >= day and user.last_streak_reward_day < day:
            milestone_day = day
            break
    
    if milestone_day is None:
        return None
    
    milestone = STREAK_MILESTONES[milestone_day]
    
    # Проверяем не получен ли уже этот milestone
    existing = await session.execute(
        select(StreakReward).where(
            StreakReward.user_id == user.user_id,
            StreakReward.milestone_day == milestone_day
        )
    )
    if existing.scalar_one_or_none():
        # Уже получен
        user.last_streak_reward_day = milestone_day
        return None
    
    # Создаём награду
    reward = StreakReward(
        user_id=user.user_id,
        milestone_day=milestone_day,
        badge_id=milestone["badge_id"],
        xp_earned=milestone["xp"],
        premium_days=milestone["premium_days"],
        freeze_earned=milestone.get("freeze", 0),
    )
    session.add(reward)
    
    # Создаём бейдж
    badge = UserBadge(
        user_id=user.user_id,
        badge_id=milestone["badge_id"],
    )
    session.add(badge)
    
    # Обновляем пользователя
    user.total_xp += milestone["xp"]
    user.weekly_xp += milestone["xp"]
    user.monthly_xp += milestone["xp"]
    user.last_streak_reward_day = milestone_day
    
    # Добавляем freeze если есть
    if milestone.get("freeze", 0) > 0:
        user.streak_freeze_available += milestone["freeze"]
    
    logger.info(
        "User %d reached streak milestone %d: +%d XP, badge=%s, freeze=%d",
        user.user_id, milestone_day, milestone["xp"], 
        milestone["badge_id"], milestone.get("freeze", 0)
    )
    
    return {
        "day": milestone_day,
        "badge_id": milestone["badge_id"],
        "name": milestone["name"],
        "emoji": milestone["emoji"],
        "description": milestone["description"],
        "xp": milestone["xp"],
        "premium_days": milestone["premium_days"],
        "freeze": milestone.get("freeze", 0),
    }


async def use_streak_freeze(session: AsyncSession, user: User) -> Dict[str, Any]:
    """
    Использовать streak freeze вручную (для защиты на будущее).
    
    Returns:
        Dict с результатом
    """
    if user.streak_freeze_available <= 0:
        return {
            "success": False,
            "message": "У тебя нет доступных заморозок 😔",
            "remaining": 0,
        }
    
    today = date.today()
    
    # Проверяем не использовался ли freeze сегодня
    if user.streak_freeze_used_at and user.streak_freeze_used_at.date() == today:
        return {
            "success": False,
            "message": "Заморозка уже использована сегодня",
            "remaining": user.streak_freeze_available,
        }
    
    user.streak_freeze_available -= 1
    user.streak_freeze_used_at = datetime.now(timezone.utc)
    
    return {
        "success": True,
        "message": "❄️ Streak Freeze активирован! Твой streak сохранится даже если пропустишь сегодня.",
        "remaining": user.streak_freeze_available,
    }


async def reset_weekly_freeze(session: AsyncSession, user: User) -> None:
    """
    Сбросить и пополнить streak freeze раз в неделю.
    Вызывается планировщиком каждый понедельник.
    """
    today = date.today()
    
    # Проверяем прошла ли неделя
    if user.streak_freeze_week_start is None or (today - user.streak_freeze_week_start).days >= 7:
        # Пополняем freeze (максимум 1 для free, 4 для premium)
        max_freeze = 1  # TODO: увеличить для premium пользователей
        user.streak_freeze_available = max_freeze
        user.streak_freeze_week_start = today
        
        logger.info("User %d: weekly freeze reset to %d", user.user_id, max_freeze)


async def get_streak_info(session: AsyncSession, user: User) -> Dict[str, Any]:
    """
    Получить полную информацию о streak пользователя.
    
    Returns:
        Dict со всеми данными о streak
    """
    today = date.today()
    
    # Получаем активность за последние 7 дней
    weekly_activity = await _get_weekly_activity(session, user.user_id)
    
    # Получаем streak бейджи
    streak_badges = await _get_streak_badges(session, user.user_id)
    
    # Находим следующий milestone
    next_milestone = None
    next_milestone_reward = None
    for day in sorted(STREAK_MILESTONES.keys()):
        if user.streak_days < day:
            next_milestone = day
            next_milestone_reward = {
                "name": STREAK_MILESTONES[day]["name"],
                "emoji": STREAK_MILESTONES[day]["emoji"],
                "xp": STREAK_MILESTONES[day]["xp"],
                "premium_days": STREAK_MILESTONES[day]["premium_days"],
            }
            break
    
    # Проверяем использовался ли freeze сегодня
    freeze_used_today = (
        user.streak_freeze_used_at is not None and 
        user.streak_freeze_used_at.date() == today
    )
    
    return {
        "streak_days": user.streak_days,
        "best_streak": user.best_streak,
        "streak_start_date": user.streak_start_date.isoformat() if user.streak_start_date else None,
        "daily_progress": user.daily_messages_count,
        "daily_goal": MIN_MESSAGES_PER_DAY,
        "daily_goal_reached": user.daily_messages_count >= MIN_MESSAGES_PER_DAY,
        "next_milestone": next_milestone,
        "next_milestone_reward": next_milestone_reward,
        "xp_today": 0,  # TODO: подсчитать XP за сегодня
        "xp_week": user.weekly_xp,
        "xp_month": user.monthly_xp,
        "total_xp": user.total_xp,
        "freeze_available": user.streak_freeze_available,
        "freeze_used_today": freeze_used_today,
        "weekly_activity": weekly_activity,
        "streak_badges": streak_badges,
    }


async def _get_weekly_activity(session: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """
    Получить активность за последние 7 дней.
    """
    from database.models import Message
    
    today = date.today()
    week_ago = today - timedelta(days=6)
    
    # Получаем количество сообщений по дням
    result = await session.execute(
        select(
            func.date(Message.created_at).label("day"),
            func.count(Message.id).label("count")
        )
        .where(
            Message.user_id == user_id,
            Message.role == "user",
            func.date(Message.created_at) >= week_ago
        )
        .group_by(func.date(Message.created_at))
    )
    
    messages_by_day = {row.day: row.count for row in result}
    
    # Формируем список за 7 дней
    activity = []
    for i in range(7):
        day = week_ago + timedelta(days=i)
        count = messages_by_day.get(day, 0)
        activity.append({
            "date": day.isoformat(),
            "weekday": day.strftime("%a"),
            "messages": count,
            "completed": count >= MIN_MESSAGES_PER_DAY,
        })
    
    return activity


async def _get_streak_badges(session: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """
    Получить streak бейджи пользователя.
    """
    result = await session.execute(
        select(StreakReward)
        .where(StreakReward.user_id == user_id)
        .order_by(StreakReward.milestone_day)
    )
    
    rewards = result.scalars().all()
    
    badges = []
    for milestone_day, milestone in STREAK_MILESTONES.items():
        earned = any(r.milestone_day == milestone_day for r in rewards)
        badges.append({
            "id": milestone["badge_id"],
            "day": milestone_day,
            "name": milestone["name"],
            "emoji": milestone["emoji"],
            "description": milestone["description"],
            "earned": earned,
            "xp": milestone["xp"],
        })
    
    return badges


def format_milestone_message(milestone: Dict[str, Any]) -> str:
    """
    Форматировать сообщение о достижении milestone.
    """
    msg = (
        f"🎉🎉🎉 *ПОЗДРАВЛЯЮ!*\n\n"
        f"Ты достиг *{milestone['day']} дней* подряд! 🔥\n\n"
        f"*Награды:*\n"
        f"🏆 Бейдж _{milestone['name']}_\n"
        f"⭐ +{milestone['xp']} XP\n"
    )
    
    if milestone.get("premium_days", 0) > 0:
        msg += f"💎 {milestone['premium_days']} дней Premium бесплатно\n"
    
    if milestone.get("freeze", 0) > 0:
        msg += f"❄️ +{milestone['freeze']} Streak Freeze\n"
    
    msg += "\nПродолжай в том же духе! 💪"
    
    return msg


def format_streak_reminder_soft(user: User) -> str:
    """
    Формат мягкого напоминания о streak (18:00).
    """
    if user.daily_messages_count >= MIN_MESSAGES_PER_DAY:
        return ""  # Цель уже достигнута
    
    remaining = MIN_MESSAGES_PER_DAY - user.daily_messages_count
    
    return (
        f"🔥 Не забудь про свой *{user.streak_days}-дневный streak*!\n\n"
        f"Осталось написать: {remaining} сообщений 📝\n\n"
        f"Напиши что-нибудь на немецком, чтобы сохранить прогресс 😊"
    )


def format_streak_reminder_urgent(user: User) -> str:
    """
    Формат срочного напоминания о streak (22:00).
    """
    if user.daily_messages_count >= MIN_MESSAGES_PER_DAY:
        return ""  # Цель уже достигнута
    
    remaining = MIN_MESSAGES_PER_DAY - user.daily_messages_count
    
    return (
        f"⚠️ *Осталось 2 часа!*\n\n"
        f"Твой *{user.streak_days}-дневный streak* в опасности! 🔥\n\n"
        f"Напиши ещё {remaining} сообщений до полуночи!\n\n"
        f"❄️ Или используй Streak Freeze: /freeze"
    )
