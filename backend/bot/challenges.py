"""
Модуль для работы с ежедневными челленджами.
Генерация, оценка, XP и бейджи.
"""

import logging
import json
import random
from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any

import google.generativeai as genai
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, ChallengeSettings, UserChallenge, UserBadge

logger = logging.getLogger(__name__)


# ============ КОНСТАНТЫ ============

TOPICS = {
    "daily_life": "Повседневная жизнь",
    "work": "Работа и карьера",
    "travel": "Путешествия",
    "food": "Еда и рестораны",
    "sports": "Спорт и хобби",
    "family": "Семья и друзья"
}

FORMATS = {
    "text": "Текстовые (написать)",
    "voice": "Голосовые (рассказать)",
    "grammar": "Грамматические",
    "vocabulary": "Словарные",
    "roleplay": "Ролевые игры",
    "creative": "Креативные"
}

BADGES = {
    "7_day_warrior": {
        "name": "7-Day Warrior",
        "emoji": "🔥",
        "description": "7 дней подряд",
        "condition_type": "streak",
        "condition_value": 7
    },
    "30_day_legend": {
        "name": "30-Day Legend",
        "emoji": "🏆",
        "description": "30 дней подряд",
        "condition_type": "streak",
        "condition_value": 30
    },
    "grammar_master": {
        "name": "Grammar Master",
        "emoji": "📚",
        "description": "10 грамматических челленджей",
        "condition_type": "format_count",
        "condition_format": "grammar",
        "condition_value": 10
    },
    "perfectionist": {
        "name": "Perfectionist",
        "emoji": "⭐",
        "description": "10 челленджей с оценкой 10/10",
        "condition_type": "perfect_count",
        "condition_value": 10
    },
    "early_bird": {
        "name": "Early Bird",
        "emoji": "🌅",
        "description": "Выполнил до 12:00",
        "condition_type": "time_before",
        "condition_value": 12
    },
    "night_owl": {
        "name": "Night Owl",
        "emoji": "🦉",
        "description": "Выполнил после 20:00",
        "condition_type": "time_after",
        "condition_value": 20
    }
}

XP_REWARDS = {
    "A1": 30,
    "A2": 50,
    "B1": 100
}

# Streak бонус за каждый день
STREAK_BONUS_XP = 10


# ============ ГЕНЕРАЦИЯ ЧЕЛЛЕНДЖЕЙ ============

GENERATE_CHALLENGE_PROMPT = """Сгенерируй ежедневный челлендж для изучения немецкого языка.

ПАРАМЕТРЫ:
- Уровень: {level}
- Тема: {topic} ({topic_name})
- Формат: {format} ({format_name})

ТРЕБОВАНИЯ:
1. Челлендж должен быть интересным и практичным
2. Четкие инструкции на русском (что делать)
3. Грамматический фокус (какую конструкцию использовать) — если формат грамматический
4. Примеры для старта на немецком
5. Минимальные требования (количество предложений, слов)

ПРИМЕРЫ ЧЕЛЛЕНДЖЕЙ ПО ФОРМАТАМ:

text (текстовые):
- Опиши свой день на немецком
- Напиши письмо другу
- Расскажи о своих планах на выходные

grammar (грамматические):
- Составь 5 предложений в Perfekt
- Используй все падежи в тексте
- Напиши диалог с модальными глаголами

vocabulary (словарные):
- Используй 10 новых слов из темы "еда"
- Опиши картинку используя минимум 8 прилагательных

creative (креативные):
- Придумай короткое стихотворение
- Напиши рецензию на фильм
- Создай рекламу продукта

Верни ТОЛЬКО валидный JSON (без markdown блоков):
{{
  "title": "короткое название челленджа (2-4 слова)",
  "description": "полное описание задания на русском (2-3 предложения)",
  "grammar_focus": "грамматическая тема или null если не применимо",
  "min_requirements": "минимальные требования (например: минимум 5 предложений)",
  "example_start": "пример начала ответа на немецком (1-2 предложения)"
}}"""


EVALUATE_CHALLENGE_PROMPT = """Оцени выполнение челленджа по изучению немецкого языка. Будь СТРОГИМ и честным.

ЗАДАНИЕ:
Тема: {topic}
Формат: {format}
Описание: {description}
Требования: {min_requirements}
Грамматический фокус: {grammar_focus}

ОТВЕТ ПОЛЬЗОВАТЕЛЯ:
{user_response}

СТРОГО ПРОВЕРЬ:
1. Выполнены ли РЕАЛЬНО минимальные требования? (не просто количество символов, а содержание)
2. Это РАЗНЫЕ предложения или копипаста одного и того же?
3. Есть ли реальный смысл и связь с темой?
4. Использована ли требуемая грамматика?
5. Это попытка выполнить задание или мусор/спам?

КРАСНЫЕ ФЛАГИ (ставь score 1-3 и completed: false):
- Одно предложение скопировано несколько раз
- Бессмысленный набор слов
- Полностью не по теме
- Текст не на немецком языке
- Очевидная попытка обмануть систему

ШКАЛА ОЦЕНОК:
- 1-3: Не выполнено (спам, копипаста, не по теме)
- 4-5: Минимально (есть попытка, много ошибок)
- 6-7: Средне (выполнено, есть ошибки)
- 8-9: Хорошо (качественно, мало ошибок)
- 10: Отлично (идеально)

Верни ТОЛЬКО валидный JSON:
{{
  "completed": true или false,
  "score": число от 1 до 10,
  "feedback": "честный фидбек на русском (2-3 предложения)",
  "corrections": ["исправление 1", "исправление 2"],
  "strong_points": ["что хорошо 1"]
}}"""


async def generate_daily_challenge(
    session: AsyncSession,
    user: User,
    settings: ChallengeSettings
) -> Optional[UserChallenge]:
    """
    Генерирует новый ежедневный челлендж для пользователя.
    
    Args:
        session: Database session
        user: Пользователь
        settings: Настройки челленджей
    
    Returns:
        UserChallenge или None при ошибке
    """
    today = date.today()
    
    # Проверяем, нет ли уже челленджа на сегодня
    existing = await session.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == user.user_id,
            UserChallenge.challenge_date == today
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Challenge already exists for user %d today", user.user_id)
        return None
    
    # Выбираем случайную тему и формат из настроек
    topic = random.choice(settings.topics) if settings.topics else "daily_life"
    format_type = random.choice(settings.formats) if settings.formats else "text"
    
    topic_name = TOPICS.get(topic, topic)
    format_name = FORMATS.get(format_type, format_type)
    
    # Генерируем через Gemini
    prompt = GENERATE_CHALLENGE_PROMPT.format(
        level=settings.difficulty,
        topic=topic,
        topic_name=topic_name,
        format=format_type,
        format_name=format_name
    )
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.8,
                max_output_tokens=1024,
            ),
        )
        
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
        # Убираем markdown если есть
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        challenge_data = json.loads(text)
        
        # Создаём челлендж
        challenge = UserChallenge(
            user_id=user.user_id,
            challenge_date=today,
            challenge_type=format_type,
            topic=topic,
            title=challenge_data.get("title", "Ежедневный челлендж"),
            description=challenge_data.get("description", ""),
            grammar_focus=challenge_data.get("grammar_focus"),
            min_requirements=challenge_data.get("min_requirements", "Напиши минимум 3 предложения"),
            example_start=challenge_data.get("example_start"),
            completed=False,
        )
        
        session.add(challenge)
        await session.flush()
        
        logger.info(
            "Generated challenge for user %d: %s (topic=%s, format=%s)",
            user.user_id, challenge.title, topic, format_type
        )
        
        return challenge
        
    except Exception as e:
        logger.error("Failed to generate challenge for user %d: %s", user.user_id, str(e))
        
        # Fallback челлендж
        challenge = UserChallenge(
            user_id=user.user_id,
            challenge_date=today,
            challenge_type=format_type,
            topic=topic,
            title="Расскажи о своём дне",
            description="Опиши на немецком, как прошёл твой день. Что ты делал? Что планируешь?",
            grammar_focus="Perfekt или Präsens",
            min_requirements="Минимум 5 предложений на немецком",
            example_start="Heute habe ich...",
            completed=False,
        )
        
        session.add(challenge)
        await session.flush()
        
        return challenge


async def evaluate_challenge_response(
    challenge: UserChallenge,
    user_response: str
) -> Dict[str, Any]:
    """
    Оценивает ответ пользователя на челлендж через Gemini.
    
    Args:
        challenge: Челлендж
        user_response: Ответ пользователя
    
    Returns:
        Словарь с оценкой и фидбеком
    """
    prompt = EVALUATE_CHALLENGE_PROMPT.format(
        topic=TOPICS.get(challenge.topic, challenge.topic),
        format=FORMATS.get(challenge.challenge_type, challenge.challenge_type),
        description=challenge.description,
        min_requirements=challenge.min_requirements,
        grammar_focus=challenge.grammar_focus or "не указан",
        user_response=user_response
    )
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.2,  # Lower for more consistent JSON
                max_output_tokens=512,  # Smaller to avoid truncation
            ),
        )
        
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
        logger.debug("Raw Gemini response: %s", text[:500])
        
        # Убираем markdown
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Попытка парсинга JSON
        try:
            result = json.loads(text)
        except json.JSONDecodeError as je:
            logger.warning("JSON parse failed, trying regex extraction: %s", str(je))
            
            # Regex fallback для извлечения ключевых полей
            import re
            
            completed_match = re.search(r'"completed"\s*:\s*(true|false)', text, re.IGNORECASE)
            score_match = re.search(r'"score"\s*:\s*(\d+)', text)
            feedback_match = re.search(r'"feedback"\s*:\s*"([^"]*)"', text)
            
            completed = completed_match.group(1).lower() == "true" if completed_match else False
            score = int(score_match.group(1)) if score_match else 5
            feedback = feedback_match.group(1) if feedback_match else "Попробуй написать полноценный ответ."
            
            result = {
                "completed": completed,
                "score": max(1, min(10, score)),
                "feedback": feedback,
                "corrections": [],
                "strong_points": []
            }
        
        # Валидация
        result["completed"] = bool(result.get("completed", False))
        result["score"] = max(1, min(10, int(result.get("score", 5))))
        result["feedback"] = str(result.get("feedback", "Хорошая работа!"))
        result["corrections"] = list(result.get("corrections", []))
        result["strong_points"] = list(result.get("strong_points", []))
        
        logger.info(
            "Evaluated challenge %d: completed=%s, score=%d",
            challenge.id, result["completed"], result["score"]
        )
        
        return result
        
    except Exception as e:
        logger.error("Failed to evaluate challenge %d: %s", challenge.id, str(e))
        import traceback
        logger.error(traceback.format_exc())
        
        # Fallback - intelligent based on response length
        words = len(user_response.split())
        unique_sentences = len(set(user_response.split('.')))
        
        if words < 10:
            return {
                "completed": False,
                "score": 2,
                "feedback": "Ответ слишком короткий. Напиши минимум 5 предложений.",
                "corrections": ["Добавь больше текста"],
                "strong_points": []
            }
        elif unique_sentences < 3:
            return {
                "completed": False,
                "score": 3,
                "feedback": "Похоже на повторение одного предложения. Напиши разные мысли.",
                "corrections": ["Используй разные предложения"],
                "strong_points": []
            }
        else:
            return {
                "completed": True,
                "score": 6,
                "feedback": "Задание засчитано! Продолжай практиковаться.",
                "corrections": [],
                "strong_points": ["Есть попытка выполнить задание"]
            }


async def complete_challenge(
    session: AsyncSession,
    challenge: UserChallenge,
    user_response: str,
    user: User
) -> Dict[str, Any]:
    """
    Завершает челлендж: оценивает, начисляет XP, проверяет бейджи.
    
    Args:
        session: Database session
        challenge: Челлендж
        user_response: Ответ пользователя
        user: Пользователь
    
    Returns:
        Результат с оценкой, XP и новыми бейджами
    """
    # Оцениваем ответ
    evaluation = await evaluate_challenge_response(challenge, user_response)
    
    if not evaluation["completed"]:
        return {
            "success": False,
            "message": "Ответ не соответствует минимальным требованиям. Попробуй написать больше или использовать нужную грамматику.",
            "evaluation": evaluation
        }
    
    now = datetime.now(timezone.utc)
    today = date.today()
    
    # Обновляем челлендж
    challenge.completed = True
    challenge.user_response = user_response
    challenge.score = evaluation["score"]
    challenge.feedback = evaluation
    challenge.completed_at = now
    
    # Вычисляем XP
    settings = await session.get(ChallengeSettings, user.user_id)
    difficulty = settings.difficulty if settings else "A2"
    base_xp = XP_REWARDS.get(difficulty, 50)
    
    # Обновляем streak
    yesterday = today - timedelta(days=1)
    
    if user.last_challenge_date == yesterday:
        # Продолжаем streak
        user.challenge_streak += 1
    elif user.last_challenge_date == today:
        # Уже выполнял сегодня (не должно случиться, но на всякий)
        pass
    else:
        # Streak сбрасывается
        user.challenge_streak = 1
    
    # Обновляем лучший streak
    if user.challenge_streak > user.best_challenge_streak:
        user.best_challenge_streak = user.challenge_streak
    
    user.last_challenge_date = today
    
    # Streak бонус
    streak_bonus = STREAK_BONUS_XP * min(user.challenge_streak, 10)  # Максимум 100 бонуса
    total_xp = base_xp + streak_bonus
    
    challenge.xp_earned = total_xp
    user.total_xp += total_xp
    
    # Проверяем бейджи
    new_badges = await check_and_award_badges(session, user, challenge, now)
    
    await session.flush()
    
    logger.info(
        "Challenge %d completed: score=%d, xp=%d, streak=%d, new_badges=%s",
        challenge.id, evaluation["score"], total_xp, user.challenge_streak, new_badges
    )
    
    return {
        "success": True,
        "completed": True,
        "score": evaluation["score"],
        "xp_earned": total_xp,
        "base_xp": base_xp,
        "streak_bonus": streak_bonus,
        "feedback": evaluation["feedback"],
        "corrections": evaluation["corrections"],
        "strong_points": evaluation["strong_points"],
        "new_streak": user.challenge_streak,
        "new_badges": new_badges,
        "total_xp": user.total_xp
    }


async def check_and_award_badges(
    session: AsyncSession,
    user: User,
    challenge: UserChallenge,
    completed_at: datetime
) -> List[str]:
    """
    Проверяет и выдаёт бейджи.
    
    Returns:
        Список ID новых бейджей
    """
    new_badges = []
    
    # Получаем существующие бейджи
    existing_result = await session.execute(
        select(UserBadge.badge_id).where(UserBadge.user_id == user.user_id)
    )
    existing_badges = set(existing_result.scalars().all())
    
    for badge_id, badge_info in BADGES.items():
        if badge_id in existing_badges:
            continue
        
        earned = False
        condition_type = badge_info["condition_type"]
        
        if condition_type == "streak":
            # Streak бейджи
            if user.challenge_streak >= badge_info["condition_value"]:
                earned = True
                
        elif condition_type == "format_count":
            # Бейджи за количество определённого формата
            count_result = await session.execute(
                select(func.count(UserChallenge.id)).where(
                    UserChallenge.user_id == user.user_id,
                    UserChallenge.completed == True,
                    UserChallenge.challenge_type == badge_info["condition_format"]
                )
            )
            count = count_result.scalar() or 0
            if count >= badge_info["condition_value"]:
                earned = True
                
        elif condition_type == "perfect_count":
            # Бейджи за идеальные оценки
            count_result = await session.execute(
                select(func.count(UserChallenge.id)).where(
                    UserChallenge.user_id == user.user_id,
                    UserChallenge.completed == True,
                    UserChallenge.score == 10
                )
            )
            count = count_result.scalar() or 0
            if count >= badge_info["condition_value"]:
                earned = True
                
        elif condition_type == "time_before":
            # Early Bird — выполнил до указанного часа
            if completed_at.hour < badge_info["condition_value"]:
                earned = True
                
        elif condition_type == "time_after":
            # Night Owl — выполнил после указанного часа
            if completed_at.hour >= badge_info["condition_value"]:
                earned = True
        
        if earned:
            badge = UserBadge(
                user_id=user.user_id,
                badge_id=badge_id,
                earned_at=completed_at
            )
            session.add(badge)
            new_badges.append(badge_id)
            logger.info("User %d earned badge: %s", user.user_id, badge_id)
    
    return new_badges


async def get_todays_challenge(
    session: AsyncSession,
    user_id: int
) -> Optional[UserChallenge]:
    """
    Получает сегодняшний челлендж пользователя.
    """
    today = date.today()
    result = await session.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == user_id,
            UserChallenge.challenge_date == today
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_todays_challenge(
    session: AsyncSession,
    user: User
) -> Optional[UserChallenge]:
    """
    Получает или создаёт сегодняшний челлендж.
    """
    challenge = await get_todays_challenge(session, user.user_id)
    if challenge:
        return challenge
    
    # Получаем или создаём настройки
    settings = await session.get(ChallengeSettings, user.user_id)
    if not settings:
        settings = ChallengeSettings(
            user_id=user.user_id,
            enabled=True,
            difficulty=user.level if user.level in ["A1", "A2", "B1"] else "A2",
            topics=["daily_life", "work", "food"],
            formats=["text", "grammar"]
        )
        session.add(settings)
        await session.flush()
    
    return await generate_daily_challenge(session, user, settings)


async def get_challenge_stats(
    session: AsyncSession,
    user_id: int
) -> Dict[str, Any]:
    """
    Получает статистику челленджей пользователя.
    """
    user = await session.get(User, user_id)
    if not user:
        return {}
    
    # Всего выполнено
    total_result = await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.user_id == user_id,
            UserChallenge.completed == True
        )
    )
    completed_total = total_result.scalar() or 0
    
    # Выполнено в этом месяце
    first_of_month = date.today().replace(day=1)
    month_result = await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.user_id == user_id,
            UserChallenge.completed == True,
            UserChallenge.challenge_date >= first_of_month
        )
    )
    completed_this_month = month_result.scalar() or 0
    
    # Средняя оценка
    avg_result = await session.execute(
        select(func.avg(UserChallenge.score)).where(
            UserChallenge.user_id == user_id,
            UserChallenge.completed == True
        )
    )
    average_score = round(avg_result.scalar() or 0, 1)
    
    # Бейджи
    badges_result = await session.execute(
        select(UserBadge).where(UserBadge.user_id == user_id)
    )
    earned_badges = [b.badge_id for b in badges_result.scalars().all()]
    
    # Формируем список всех бейджей с прогрессом
    badges_list = []
    for badge_id, badge_info in BADGES.items():
        badge_data = {
            "id": badge_id,
            "name": badge_info["name"],
            "emoji": badge_info["emoji"],
            "description": badge_info["description"],
            "earned": badge_id in earned_badges,
            "progress": None
        }
        
        # Добавляем прогресс для streak бейджей
        if not badge_data["earned"] and badge_info["condition_type"] == "streak":
            badge_data["progress"] = f"{user.challenge_streak}/{badge_info['condition_value']}"
        
        badges_list.append(badge_data)
    
    # Прогресс по темам
    topics_progress = {}
    for topic_id in TOPICS:
        topic_result = await session.execute(
            select(func.count(UserChallenge.id)).where(
                UserChallenge.user_id == user_id,
                UserChallenge.completed == True,
                UserChallenge.topic == topic_id
            )
        )
        count = topic_result.scalar() or 0
        # Прогресс: 10 челленджей = 100%
        topics_progress[topic_id] = min(100, count * 10)
    
    # Уровень по XP
    xp = user.total_xp
    if xp >= 3000:
        level = "Expert"
    elif xp >= 1500:
        level = "Advanced"
    elif xp >= 500:
        level = "Intermediate"
    else:
        level = "Beginner"
    
    return {
        "total_xp": user.total_xp,
        "level": level,
        "current_streak": user.challenge_streak,
        "best_streak": user.best_challenge_streak,
        "completed_total": completed_total,
        "completed_this_month": completed_this_month,
        "average_score": average_score,
        "badges": badges_list,
        "topics_progress": topics_progress
    }


async def get_challenge_history(
    session: AsyncSession,
    user_id: int,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    Получает историю челленджей.
    """
    result = await session.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == user_id
        ).order_by(UserChallenge.challenge_date.desc()).limit(limit)
    )
    challenges = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "date": c.challenge_date.isoformat(),
            "title": c.title,
            "topic": c.topic,
            "topic_name": TOPICS.get(c.topic, c.topic),
            "type": c.challenge_type,
            "completed": c.completed,
            "score": c.score,
            "xp_earned": c.xp_earned
        }
        for c in challenges
    ]


def format_challenge_message(challenge: UserChallenge, user: User) -> str:
    """
    Форматирует сообщение о челлендже для Telegram.
    """
    topic_name = TOPICS.get(challenge.topic, challenge.topic)
    format_name = FORMATS.get(challenge.challenge_type, challenge.challenge_type)
    
    message = f"""☀️ Guten Morgen!

🎯 *Твой челлендж на сегодня:*

*ТЕМА:* {topic_name}
*ЗАДАНИЕ:* {challenge.description}
"""

    if challenge.grammar_focus:
        message += f"*ГРАММАТИКА:* {challenge.grammar_focus}\n"
    
    message += f"*ТРЕБОВАНИЯ:* {challenge.min_requirements}\n"
    
    if challenge.example_start:
        message += f"\n💡 *Пример начала:* _{challenge.example_start}_\n"
    
    # Награда
    settings_difficulty = user.level if user.level in ["A1", "A2", "B1"] else "A2"
    base_xp = XP_REWARDS.get(settings_difficulty, 50)
    streak_bonus = STREAK_BONUS_XP * min(user.challenge_streak + 1, 10)
    
    message += f"\n🏆 *Награда:* +{base_xp} XP"
    if user.challenge_streak > 0:
        message += f" (+{streak_bonus} бонус за streak)"
    
    return message


def format_challenge_result(result: Dict[str, Any]) -> str:
    """
    Форматирует результат выполнения челленджа.
    """
    if not result.get("success"):
        # Не выполнено - но даём подробный фидбек
        evaluation = result.get("evaluation", {})
        
        message = "❌ *Не засчитано*\n\n"
        
        # Оценка
        score = evaluation.get("score", 0)
        message += f"📊 Оценка: {score}/10\n\n"
        
        # Что не так
        if evaluation.get("feedback"):
            message += f"💬 {evaluation['feedback']}\n\n"
        else:
            message += "Ответ не соответствует требованиям.\n\n"
        
        # Что исправить
        if evaluation.get("corrections"):
            message += "⚠️ *Что нужно исправить:*\n"
            for corr in evaluation["corrections"][:3]:
                message += f"• {corr}\n"
            message += "\n"
        
        message += "📝 *Попробуй ещё раз!* Твой ответ должен:\n"
        message += "• Быть на немецком языке\n"
        message += "• Содержать разные предложения\n"
        message += "• Соответствовать теме задания\n"
        
        return message
    
    message = f"""🎉 *Челлендж выполнен!*

📊 *Оценка:* {result['score']}/10

"""
    
    # Сильные стороны
    if result.get("strong_points"):
        message += "✅ *Что получилось хорошо:*\n"
        for point in result["strong_points"][:3]:
            message += f"• {point}\n"
        message += "\n"
    
    # Исправления
    if result.get("corrections"):
        message += "⚠️ *Можно улучшить:*\n"
        for correction in result["corrections"][:3]:
            message += f"• {correction}\n"
        message += "\n"
    
    # Фидбек
    if result.get("feedback"):
        message += f"💬 {result['feedback']}\n\n"
    
    # XP и streak
    message += f"⭐ *+{result['xp_earned']} XP*"
    if result.get("streak_bonus", 0) > 0:
        message += f" (базовые {result['base_xp']} + {result['streak_bonus']} бонус)"
    message += f"\n🔥 *Streak:* {result['new_streak']} дней подряд!"
    
    # Новые бейджи
    if result.get("new_badges"):
        message += "\n\n🏅 *Новые бейджи!*\n"
        for badge_id in result["new_badges"]:
            badge = BADGES.get(badge_id, {})
            message += f"{badge.get('emoji', '🎖')} {badge.get('name', badge_id)}\n"
    
    return message

