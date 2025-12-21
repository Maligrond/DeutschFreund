"""
Модуль для встроенных грамматических упражнений.
Генерирует упражнения на основе контекста разговора.
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

from sqlalchemy import select, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, GrammarExercise

logger = logging.getLogger(__name__)


# ============ КОНСТАНТЫ ============

# Темы упражнений
GRAMMAR_TOPICS = {
    "articles": {
        "name": "Артикли",
        "name_de": "Artikel",
        "description": "der/die/das",
        "premium": False,
    },
    "cases": {
        "name": "Падежи",
        "name_de": "Fälle",
        "description": "Nominativ/Akkusativ/Dativ",
        "premium": False,
    },
    "perfekt": {
        "name": "Perfekt vs Präteritum",
        "name_de": "Perfekt/Präteritum",
        "description": "Выбор времени",
        "premium": True,
    },
    "word_order": {
        "name": "Порядок слов",
        "name_de": "Wortstellung",
        "description": "Структура предложения",
        "premium": True,
    },
    "prepositions": {
        "name": "Предлоги",
        "name_de": "Präpositionen",
        "description": "Предлоги + падежи",
        "premium": True,
    },
    "adjectives": {
        "name": "Склонение прилагательных", 
        "name_de": "Adjektivdeklination",
        "description": "Окончания прилагательных",
        "premium": True,
    },
}

# Настройки частоты
FREQUENCY_SETTINGS = {
    "rare": {
        "min_messages": 8,
        "max_messages": 12,
        "cooldown_minutes": 10,
    },
    "medium": {
        "min_messages": 5,
        "max_messages": 7,
        "cooldown_minutes": 5,
    },
    "often": {
        "min_messages": 3,
        "max_messages": 5,
        "cooldown_minutes": 3,
    },
}

# XP за правильный ответ
XP_PER_CORRECT_ANSWER = 10


# ============ ФУНКЦИИ ПРОВЕРКИ ============

def should_trigger_exercise(user: User, is_user_question: bool = False) -> bool:
    """
    Проверяет, нужно ли показать грамматическое упражнение.
    
    Args:
        user: Пользователь
        is_user_question: Пользователь задал вопрос (не прерываем)
        
    Returns:
        True если нужно показать упражнение
    """
    # Отключено в настройках
    if not user.grammar_exercises_enabled:
        return False
    
    # Не прерываем если пользователь задал вопрос
    if is_user_question:
        return False
    
    # Получаем настройки частоты
    freq_settings = FREQUENCY_SETTINGS.get(user.grammar_frequency, FREQUENCY_SETTINGS["medium"])
    
    # Проверяем cooldown
    if user.last_grammar_exercise:
        cooldown = timedelta(minutes=freq_settings["cooldown_minutes"])
        last_exercise = user.last_grammar_exercise
        # Ensure timezone-aware comparison
        if last_exercise.tzinfo is None:
            last_exercise = last_exercise.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_exercise < cooldown:
            return False
    
    # Проверяем счётчик сообщений
    min_messages = freq_settings["min_messages"]
    max_messages = freq_settings["max_messages"]
    
    if user.grammar_message_counter < min_messages:
        return False
    
    # Случайный триггер после min_messages
    if user.grammar_message_counter >= max_messages:
        return True
    
    # Вероятность увеличивается с каждым сообщением после min
    probability = (user.grammar_message_counter - min_messages + 1) / (max_messages - min_messages + 1)
    return random.random() < probability


def is_user_asking_question(text: str) -> bool:
    """Проверяет, задаёт ли пользователь вопрос."""
    text = text.strip().lower()
    
    # Явные признаки вопроса
    if text.endswith("?"):
        return True
    
    # Вопросительные слова
    question_words = [
        "was", "wie", "wo", "wann", "warum", "wer", "welche", "welcher", "welches",
        "wie viel", "wie viele", "woher", "wohin", "weshalb", "wieso",
        "что", "как", "где", "когда", "почему", "кто", "какой", "сколько"
    ]
    
    for word in question_words:
        if text.startswith(word + " ") or text.startswith(word + ","):
            return True
    
    return False


def get_available_topics(is_premium: bool = False) -> List[str]:
    """Возвращает доступные темы для пользователя."""
    topics = []
    for topic_id, topic_info in GRAMMAR_TOPICS.items():
        if not topic_info["premium"] or is_premium:
            topics.append(topic_id)
    return topics


# ============ СТАТИСТИКА ============

async def get_weak_topics(
    session: AsyncSession, 
    user_id: int,
    min_exercises: int = 3
) -> List[Dict[str, Any]]:
    """
    Определяет слабые темы пользователя на основе истории ошибок.
    
    Returns:
        Список тем с процентом ошибок, отсортированный по слабости
    """
    # Статистика по темам
    result = await session.execute(
        select(
            GrammarExercise.topic,
            func.count(GrammarExercise.id).label("total"),
            func.sum(
                func.cast(GrammarExercise.is_correct == True, Integer)
            ).label("correct")
        )
        .where(
            GrammarExercise.user_id == user_id,
            GrammarExercise.user_answer.isnot(None)
        )
        .group_by(GrammarExercise.topic)
    )
    
    weak_topics = []
    for row in result.all():
        if row.total >= min_exercises:
            accuracy = (row.correct or 0) / row.total * 100
            if accuracy < 70:  # Менее 70% правильных = слабая тема
                topic_info = GRAMMAR_TOPICS.get(row.topic, {})
                weak_topics.append({
                    "topic": row.topic,
                    "name": topic_info.get("name", row.topic),
                    "accuracy": round(accuracy, 1),
                    "total": row.total,
                    "correct": row.correct or 0,
                })
    
    # Сортируем по слабости (меньше accuracy = слабее)
    weak_topics.sort(key=lambda x: x["accuracy"])
    
    return weak_topics


async def get_grammar_stats(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    """
    Получает полную статистику грамматических упражнений.
    """
    user = await session.get(User, user_id)
    
    if not user:
        return {
            "total_exercises": 0,
            "correct_answers": 0,
            "accuracy": 0.0,
            "weak_topics": [],
            "by_topic": {},
        }
    
    # Общая статистика
    total = user.total_grammar_exercises
    correct = user.correct_grammar_exercises
    accuracy = (correct / total * 100) if total > 0 else 0.0
    
    # Статистика по темам
    result = await session.execute(
        select(
            GrammarExercise.topic,
            func.count(GrammarExercise.id).label("total"),
            func.sum(
                func.case(
                    (GrammarExercise.is_correct == True, 1),
                    else_=0
                )
            ).label("correct")
        )
        .where(
            GrammarExercise.user_id == user_id,
            GrammarExercise.user_answer.isnot(None)
        )
        .group_by(GrammarExercise.topic)
    )
    
    by_topic = {}
    for row in result.all():
        topic_info = GRAMMAR_TOPICS.get(row.topic, {})
        by_topic[row.topic] = {
            "name": topic_info.get("name", row.topic),
            "total": row.total,
            "correct": row.correct or 0,
            "accuracy": round((row.correct or 0) / row.total * 100, 1) if row.total > 0 else 0.0,
        }
    
    # Слабые темы
    weak_topics = await get_weak_topics(session, user_id)
    
    return {
        "total_exercises": total,
        "correct_answers": correct,
        "accuracy": round(accuracy, 1),
        "weak_topics": weak_topics,
        "by_topic": by_topic,
    }


# ============ ВЫБОР ТЕМЫ ============

async def choose_topic(
    session: AsyncSession,
    user_id: int,
    context_phrase: str,
    is_premium: bool = False
) -> str:
    """
    Выбирает тему для упражнения на основе контекста и слабых мест.
    
    Приоритет:
    1. Слабые темы (50% шанс)
    2. Тема из контекста (30% шанс) 
    3. Случайная тема (20% шанс)
    """
    available_topics = get_available_topics(is_premium)
    
    # Слабые темы
    weak_topics = await get_weak_topics(session, user_id, min_exercises=2)
    weak_topic_ids = [t["topic"] for t in weak_topics if t["topic"] in available_topics]
    
    # Выбор темы
    roll = random.random()
    
    if roll < 0.5 and weak_topic_ids:
        # 50% - слабая тема
        return random.choice(weak_topic_ids)
    elif roll < 0.8:
        # 30% - на основе контекста (пока просто articles как самая частая)
        context_topic = detect_topic_from_context(context_phrase)
        if context_topic and context_topic in available_topics:
            return context_topic
    
    # 20% или fallback - случайная тема
    return random.choice(available_topics)


def detect_topic_from_context(text: str) -> Optional[str]:
    """
    Определяет подходящую тему на основе текста.
    Простая эвристика.
    """
    text_lower = text.lower()
    
    # Артикли - если есть существительные
    nouns_indicators = ["der", "die", "das", "ein", "eine", "einen", "einem", "einer"]
    if any(word in text_lower.split() for word in nouns_indicators):
        return "articles"
    
    # Perfekt - если есть причастия или вспомогательные глаголы
    perfekt_indicators = ["habe", "hat", "haben", "bin", "ist", "sind", "gewesen", "gemacht", "gegangen"]
    if any(word in text_lower.split() for word in perfekt_indicators):
        return "perfekt"
    
    # Предлоги
    prepositions = ["in", "an", "auf", "mit", "bei", "nach", "zu", "von", "aus", "für", "durch", "gegen", "ohne"]
    if any(word in text_lower.split() for word in prepositions):
        return "prepositions"
    
    # По умолчанию - артикли (самая базовая тема)
    return "articles"


# ============ СОХРАНЕНИЕ РЕЗУЛЬТАТА ============

async def save_exercise_answer(
    session: AsyncSession,
    exercise_id: int,
    user_answer: str,
    user: User
) -> Dict[str, Any]:
    """
    Сохраняет ответ пользователя и обновляет статистику.
    
    Returns:
        Словарь с результатом и начисленным XP
    """
    exercise = await session.get(GrammarExercise, exercise_id)
    
    if not exercise or exercise.user_id != user.user_id:
        raise ValueError("Exercise not found")
    
    if exercise.user_answer is not None:
        raise ValueError("Already answered")
    
    # Проверяем ответ
    is_correct = user_answer.upper() == exercise.correct_answer.upper()
    
    # Сохраняем ответ
    exercise.user_answer = user_answer.upper()
    exercise.is_correct = is_correct
    exercise.answered_at = datetime.now(timezone.utc)
    
    # Обновляем статистику пользователя
    user.total_grammar_exercises += 1
    if is_correct:
        user.correct_grammar_exercises += 1
        user.total_xp += XP_PER_CORRECT_ANSWER
    
    await session.commit()
    
    return {
        "is_correct": is_correct,
        "correct_answer": exercise.correct_answer,
        "rule": exercise.rule_explanation,
        "follow_up": exercise.follow_up_message,
        "xp_earned": XP_PER_CORRECT_ANSWER if is_correct else 0,
        "total_xp": user.total_xp,
    }
