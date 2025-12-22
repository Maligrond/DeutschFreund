"""
API routes для Telegram Mini App.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_session
from database.models import User, Message, UserContext as UserContextDB, Vocabulary, VoicePractice
from .models import (
    StatsResponse, MessagesByDay,
    HistoryResponse, MessageItem,
    VocabularyResponse, VocabularyItem,
    SettingsUpdate, SettingsResponse, UpdateResponse,
    ContextResponse, UserContext,
    UserProfile, ErrorResponse,
    SingleMessageResponse, TranslateWordRequest, TranslateWordResponse,
    TranslateAllResponse, AddFavoriteRequest, FavoriteWordItem, FavoritesResponse,
    PronunciationStatsResponse, PronunciationHistoryResponse,
    PronunciationPracticeItem, PronunciationFeedback, ScoreByDay, ProblematicSound,
    ChallengeSettingsResponse, ChallengeSettingsUpdate, TodayChallengeResponse,
    ChallengeSubmitRequest, ChallengeSubmitResponse, ChallengeStatsResponse,
    ChallengeHistoryResponse, ChallengeHistoryItem, BadgeItem,
    GrammarSettingsResponse, GrammarSettingsUpdate, GrammarStatsResponse,
    GrammarTopicsResponse, GrammarTopicInfo, WeakTopicItem,
    GrammarTopicsResponse, GrammarTopicInfo, WeakTopicItem,
    StreakSettingsUpdate,
    PlacementTestQuestionsResponse, PlacementTestSubmit,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User API"])


# ============ HELPER FUNCTIONS ============

async def get_or_create_user(session: AsyncSession, user_id: int) -> User:
    """
    Получить пользователя или создать нового автоматически.
    Используется когда пользователь открывает Mini App.
    """
    user = await session.get(User, user_id)
    
    if not user:
        # Автоматически создаём нового пользователя
        user = User(
            user_id=user_id,
            username=None,
            first_name=f"User_{user_id}",  # Будет обновлено при взаимодействии с ботом
            level="A2",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.flush()
        logger.info("Auto-created user %d from Mini App", user_id)
    
    return user


# ============ ENDPOINTS ============

@router.get(
    "/user/{user_id}/stats",
    response_model=StatsResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Получить статистику пользователя"
)
async def get_user_stats(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
) -> StatsResponse:
    """
    Возвращает статистику обучения пользователя:
    - Streak дней
    - Количество сообщений
    - Слова и т.д.
    """
    user = await get_or_create_user(session, user_id)
    
    # Количество слов в словаре
    vocab_result = await session.execute(
        select(func.count(Vocabulary.id))
        .where(Vocabulary.user_id == user_id)
    )
    new_words_count = vocab_result.scalar() or 0
    
    # Количество выученных слов
    learned_result = await session.execute(
        select(func.count(Vocabulary.id))
        .where(
            Vocabulary.user_id == user_id,
            Vocabulary.learned == True
        )
    )
    learned_words_count = learned_result.scalar() or 0
    
    # Последние 10 добавленных слов
    recent_result = await session.execute(
        select(Vocabulary)
        .where(Vocabulary.user_id == user_id)
        .order_by(Vocabulary.created_at.desc())
        .limit(10)
    )
    recent_vocab = recent_result.scalars().all()
    
    recent_words = [
        VocabularyItem(
            id=w.id,
            word_de=w.word_de,
            word_ru=w.word_ru,
            times_seen=w.times_seen,
            learned=w.learned,
            created_at=w.created_at
        )
        for w in recent_vocab
    ]
    
    # Статистика сообщений по дням (последние 30 дней)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    messages_result = await session.execute(
        select(Message)
        .where(
            Message.user_id == user_id,
            Message.role == "user",
            Message.created_at >= thirty_days_ago
        )
        .order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()
    
    # Группировка по дням
    by_day: dict[str, int] = defaultdict(int)
    for msg in messages:
        date_str = msg.created_at.strftime("%Y-%m-%d")
        by_day[date_str] += 1
    
    messages_by_day = [
        MessagesByDay(date=date, count=count)
        for date, count in sorted(by_day.items())
    ]
    
    # Accuracy (прогресс на основе выученных слов)
    # Прогресс = (выученные слова / 100) * 100, макс 95%
    if new_words_count > 0:
        accuracy = min(95.0, (learned_words_count / 100) * 100)
    else:
        accuracy = 0.0
    
    # Calculate level progress
    from bot.levels import calculate_user_progress
    progress_info = calculate_user_progress(user.total_xp)
    
    return StatsResponse(
        streak_days=user.streak_days,
        total_messages=user.total_messages,
        level=progress_info["current_level"], # Use calculated level
        goal=user.goal,
        new_words_count=new_words_count,
        learned_words_count=learned_words_count,
        recent_words=recent_words,
        messages_by_day=messages_by_day,
        accuracy=round(accuracy, 1),
        created_at=user.created_at,
        # Progress info
        total_xp=user.total_xp,
        next_level=progress_info["next_level"],
        level_xp_start=progress_info["level_xp_start"],
        level_xp_end=progress_info["level_xp_end"],
        progress_percent=progress_info["progress_percent"],
        xp_needed=progress_info["xp_needed"]
    )


@router.get(
    "/user/{user_id}/history",
    response_model=HistoryResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Получить историю сообщений"
)
async def get_user_history(
    user_id: int = Path(..., description="Telegram User ID"),
    limit: int = Query(50, ge=1, le=100, description="Лимит сообщений"),
    offset: int = Query(0, ge=0, description="Смещение"),
    session: AsyncSession = Depends(get_session)
) -> HistoryResponse:
    """
    Возвращает историю сообщений с пагинацией.
    """
    await get_or_create_user(session, user_id)
    
    # Общее количество
    total_result = await session.execute(
        select(func.count(Message.id))
        .where(Message.user_id == user_id)
    )
    total = total_result.scalar() or 0
    
    # Сообщения с пагинацией
    messages_result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = list(reversed(messages_result.scalars().all()))
    
    return HistoryResponse(
        messages=[
            MessageItem(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                tokens_used=msg.tokens_used,
            )
            for msg in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/user/{user_id}/vocabulary",
    response_model=VocabularyResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Получить словарь пользователя"
)
async def get_user_vocabulary(
    user_id: int = Path(..., description="Telegram User ID"),
    learned_only: bool = Query(False, description="Только выученные слова"),
    session: AsyncSession = Depends(get_session)
) -> VocabularyResponse:
    """
    Возвращает изученные слова пользователя.
    """
    await get_or_create_user(session, user_id)
    
    # Базовый запрос
    query = select(Vocabulary).where(Vocabulary.user_id == user_id)
    
    if learned_only:
        query = query.where(Vocabulary.learned == True)
    
    result = await session.execute(
        query.order_by(Vocabulary.created_at.desc())
    )
    words = result.scalars().all()
    
    # Подсчёт выученных
    total_learned = sum(1 for w in words if w.learned)
    
    return VocabularyResponse(
        words=[
            VocabularyItem(
                id=w.id,
                word_de=w.word_de,
                word_ru=w.word_ru,
                times_seen=w.times_seen,
                learned=w.learned,
                created_at=w.created_at,
            )
            for w in words
        ],
        total=len(words),
        total_learned=total_learned,
    )


@router.get(
    "/user/{user_id}/settings",
    response_model=SettingsResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Получить настройки пользователя"
)
async def get_user_settings(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
) -> SettingsResponse:
    """
    Возвращает текущие настройки пользователя.
    """
    user = await get_or_create_user(session, user_id)
    
    return SettingsResponse(
        level=user.level,
        goal=user.goal,
        reminder_enabled=user.reminder_enabled,
        reminder_frequency=user.reminder_frequency,
        bot_personality=user.bot_personality,
        practice_mode_enabled=user.practice_mode_enabled,
    )


@router.put(
    "/user/{user_id}/settings",
    response_model=UpdateResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Обновить настройки пользователя"
)
async def update_user_settings(
    settings: SettingsUpdate,
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Обновляет настройки пользователя.
    Передаются только те поля, которые нужно изменить.
    """
    user = await get_or_create_user(session, user_id)
    
    # Обновляем только переданные поля
    updated_fields = []
    
    if settings.level is not None:
        user.level = settings.level
        updated_fields.append("level")
        
    if settings.goal is not None:
        user.goal = settings.goal
        updated_fields.append("goal")
        
    if settings.reminder_enabled is not None:
        user.reminder_enabled = settings.reminder_enabled
        updated_fields.append("reminder_enabled")
        
    if settings.reminder_frequency is not None:
        user.reminder_frequency = settings.reminder_frequency
        updated_fields.append("reminder_frequency")
        
    if settings.bot_personality is not None:
        user.bot_personality = settings.bot_personality
        updated_fields.append("bot_personality")
    
    user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    
    logger.info("Updated settings for user %d: %s", user_id, updated_fields)
    
    return UpdateResponse(
        status="ok",
        message=f"Updated: {', '.join(updated_fields) or 'nothing'}"
    )


@router.get(
    "/user/{user_id}/context",
    response_model=ContextResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Получить контекст пользователя"
)
async def get_user_context(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
) -> ContextResponse:
    """
    Возвращает контекст пользователя (город, работа, интересы и т.д.).
    """
    await get_or_create_user(session, user_id)
    
    context_db = await session.get(UserContextDB, user_id)
    
    if not context_db:
        return ContextResponse(
            context=UserContext(),
            updated_at=None,
        )
    
    data = context_db.context_data or {}
    
    return ContextResponse(
        context=UserContext(
            name=data.get("name"),
            city=data.get("city"),
            job=data.get("job"),
            interests=data.get("interests"),
            problems=data.get("problems"),
            extra=data.get("extra"),
        ),
        updated_at=context_db.updated_at,
    )


@router.put(
    "/user/{user_id}/context",
    response_model=UpdateResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Обновить контекст пользователя"
)
async def update_user_context(
    context: UserContext,
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Обновляет контекст пользователя.
    """
    await get_or_create_user(session, user_id)
    
    context_db = await session.get(UserContextDB, user_id)
    
    # Собираем данные
    context_data = {
        k: v for k, v in context.model_dump().items() if v is not None
    }
    
    if context_db:
        # Обновляем существующий
        context_db.context_data = context_data
        context_db.updated_at = datetime.now(timezone.utc)
    else:
        # Создаём новый
        context_db = UserContextDB(
            user_id=user_id,
            context_data=context_data,
        )
        session.add(context_db)
    
    await session.commit()
    
    return UpdateResponse(status="ok", message="Context updated")


@router.get(
    "/user/{user_id}/profile",
    response_model=UserProfile,
    responses={404: {"model": ErrorResponse}},
    summary="Получить профиль пользователя"
)
async def get_user_profile(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
) -> UserProfile:
    """
    Возвращает полный профиль пользователя.
    """
    user = await get_or_create_user(session, user_id)
    
    return UserProfile(
        user_id=user.user_id,
        username=user.username,
        first_name=user.first_name,
        level=user.level,
        goal=user.goal,
        streak_days=user.streak_days,
        total_messages=user.total_messages,
        reminder_enabled=user.reminder_enabled,
        bot_personality=user.bot_personality,
        created_at=user.created_at,
    )


# ============ INTERACTIVE TEXT ENDPOINTS ============

@router.get(
    "/message/{message_id}",
    response_model=SingleMessageResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Получить сообщение по ID",
    tags=["Interactive Text"]
)
async def get_message_by_id(
    message_id: int = Path(..., description="ID сообщения"),
    session: AsyncSession = Depends(get_session)
) -> SingleMessageResponse:
    """
    Возвращает текст сообщения по его ID.
    Используется для интерактивного просмотра текста.
    """
    message = await session.get(Message, message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return SingleMessageResponse(
        id=message.id,
        content=message.content,
        created_at=message.created_at
    )


@router.post(
    "/message/{message_id}/translate",
    response_model=TranslateWordResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Перевести слово из сообщения",
    tags=["Interactive Text"]
)
async def translate_word(
    request: TranslateWordRequest,
    message_id: int = Path(..., description="ID сообщения"),
    session: AsyncSession = Depends(get_session)
) -> TranslateWordResponse:
    """
    Переводит отдельное слово из сообщения.
    """
    # Проверяем существование сообщения
    message = await session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Импортируем Gemini клиент
    from bot.gemini_client import get_gemini_client
    
    try:
        gemini = get_gemini_client()
        translation = await gemini.translate_word(request.word)
    except RuntimeError:
        # Если клиент не инициализирован
        translation = f"Перевод недоступен: {request.word}"
    
    return TranslateWordResponse(
        word=request.word,
        translation=translation
    )


@router.post(
    "/message/{message_id}/translate-all",
    response_model=TranslateAllResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Перевести всё сообщение",
    tags=["Interactive Text"]
)
async def translate_full_message(
    message_id: int = Path(..., description="ID сообщения"),
    session: AsyncSession = Depends(get_session)
) -> TranslateAllResponse:
    """
    Переводит всё сообщение целиком на русский язык.
    """
    message = await session.get(Message, message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Импортируем Gemini клиент
    from bot.gemini_client import get_gemini_client
    
    try:
        gemini = get_gemini_client()
        translation = await gemini.simple_translate(message.content)
    except RuntimeError:
        translation = "Перевод недоступен"
    
    return TranslateAllResponse(
        original=message.content,
        translation=translation
    )


@router.post(
    "/vocabulary/favorite",
    response_model=UpdateResponse,
    summary="Добавить слово в избранное",
    tags=["Interactive Text"]
)
async def add_to_favorites(
    request: AddFavoriteRequest,
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Добавляет слово в избранное пользователя.
    Если слово уже есть - увеличивает счётчик просмотров.
    """
    await get_or_create_user(session, request.user_id)
    
    # Проверяем есть ли уже такое слово
    existing_result = await session.execute(
        select(Vocabulary).where(
            Vocabulary.user_id == request.user_id,
            Vocabulary.word_de == request.word_de
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.times_seen += 1
        existing.learned = False  # Пометить что нужно повторить
        await session.commit()
        return UpdateResponse(status="updated", message=f"Word '{request.word_de}' updated")
    else:
        new_word = Vocabulary(
            user_id=request.user_id,
            word_de=request.word_de,
            word_ru=request.word_ru,
            times_seen=1,
            learned=False,
            next_review=datetime.now(timezone.utc)  # Explicitly set to now
        )
        session.add(new_word)
        await session.commit()
        return UpdateResponse(status="added", message=f"Word '{request.word_de}' added to favorites")


@router.post(
    "/vocabulary/{word_id}/reset",
    response_model=UpdateResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Сбросить прогресс и отправить на повторение",
    tags=["Vocabulary"]
)
async def reset_word_progress(
    word_id: int = Path(..., description="ID слова"),
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Сбрасывает прогресс слова (уровень 0) и ставит next_review на сейчас.
    Позволяет пользователю принудительно добавить слово в карточки.
    """
    word = await session.get(Vocabulary, word_id)
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    word.learned = False
    word.times_seen = 0
    word.interval = 0
    word.ease_factor = 2.5
    word.next_review = datetime.now(timezone.utc)
    
    await session.commit()
    
    return UpdateResponse(status="ok", message="Word reset for review")


@router.get(
    "/vocabulary/favorites/{user_id}",
    response_model=FavoritesResponse,
    summary="Получить избранные слова",
    tags=["Interactive Text"]
)
async def get_favorites(
    user_id: int = Path(..., description="Telegram User ID"),
    limit: int = Query(50, ge=1, le=100, description="Лимит слов"),
    session: AsyncSession = Depends(get_session)
) -> FavoritesResponse:
    """
    Возвращает все избранные слова пользователя.
    """
    await get_or_create_user(session, user_id)
    
    result = await session.execute(
        select(Vocabulary)
        .where(Vocabulary.user_id == user_id)
        .order_by(Vocabulary.created_at.desc())
        .limit(limit)
    )
    words = result.scalars().all()
    
    return FavoritesResponse(
        words=[
            FavoriteWordItem(
                id=w.id,
                word_de=w.word_de,
                word_ru=w.word_ru,
                times_seen=w.times_seen,
                learned=w.learned,
                created_at=w.created_at
            )
            for w in words
        ],
        total=len(words)
    )


@router.post(
    "/vocabulary/{word_id}/toggle-learned",
    response_model=UpdateResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Переключить статус выучено",
    tags=["Interactive Text"]
)
async def toggle_learned_status(
    word_id: int = Path(..., description="ID слова"),
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Переключает статус слова: выучено / не выучено.
    """
    word = await session.get(Vocabulary, word_id)
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    word.learned = not word.learned
    await session.commit()
    
    status = "learned" if word.learned else "not learned"
    return UpdateResponse(status="ok", message=f"Word marked as {status}")


# ============ FLASHCARDS (SRS) ENDPOINTS ============

@router.get(
    "/vocabulary/review",
    response_model=VocabularyResponse,
    summary="Получить слова для повторения (SRS)",
    tags=["Flashcards"]
)
async def get_due_flashcards(
    user_id: int = Query(..., description="ID пользователя"),
    limit: int = Query(15, description="Лимит карточек"),
    session: AsyncSession = Depends(get_session)
) -> VocabularyResponse:
    """
    Возвращает список слов, которые нужно повторить прямо сейчас
    на основе next_review даты.
    """
    now = datetime.now(timezone.utc)
    
    # Ищем слова, где next_review <= now (или null)
    # Сортируем по давности (самые просроченные первыми)
    result = await session.execute(
        select(Vocabulary)
        .where(
            Vocabulary.user_id == user_id,
            (Vocabulary.next_review <= now) | (Vocabulary.next_review.is_(None))
        )
        .order_by(Vocabulary.next_review.asc())
        .limit(limit)
    )
    words = result.scalars().all()
    
    return VocabularyResponse(
        words=[
            VocabularyItem(
                id=w.id,
                word_de=w.word_de,
                word_ru=w.word_ru,
                times_seen=w.times_seen,
                learned=w.learned,
                created_at=w.created_at,
            )
            for w in words
        ],
        total=len(words),
        total_learned=0 # Irrelevant here
    )


@router.post(
    "/vocabulary/review/{word_id}",
    response_model=UpdateResponse,
    summary="Отправить результат повторения (SRS)",
    tags=["Flashcards"]
)
async def submit_flashcard_review(
    word_id: int = Path(..., description="ID слова"),
    quality: int = Query(..., ge=1, le=4, description="Оценка: 1=Again, 2=Hard, 3=Good, 4=Easy"),
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Сохраняет результат повторения и обновляет интервалы (SM-2).
    """
    from bot.srs import calculate_next_review
    
    word = await session.get(Vocabulary, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
        
    # Рассчитываем новые параметры SM-2
    result = calculate_next_review(
        quality=quality,
        interval=word.interval,
        ease_factor=word.ease_factor
    )
    
    # Обновляем слово
    word.interval = result["interval"]
    word.ease_factor = result["ease_factor"]
    word.next_review = result["next_review"]
    word.times_seen += 1
    
    if word.interval > 21: # Считаем выученным если интервал > 3 недель
        word.learned = True
        
    await session.commit()
    
    # Начисляем XP (немного)
    user = await session.get(User, word.user_id)
    if user:
        xp_gain = 2
        user.total_xp += xp_gain
        user.weekly_xp += xp_gain
        user.monthly_xp += xp_gain
        await session.commit()
        
    return UpdateResponse(
        status="ok",
        message=f"Review saved. Next review: {word.next_review}"
    )


# ============ PRONUNCIATION ENDPOINTS ============

@router.get(
    "/user/{user_id}/pronunciation/stats",
    response_model=PronunciationStatsResponse,
    summary="Статистика произношения",
    tags=["Pronunciation"]
)
async def get_pronunciation_stats(
    user_id: int = Path(..., description="ID пользователя"),
    days: int = Query(30, description="За сколько дней"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить статистику практик произношения:
    - Средняя оценка
    - Оценки по дням
    - Проблемные звуки
    - Последние практики
    """
    from database.models import VoicePractice
    from .models import (
        PronunciationStatsResponse, ScoreByDay, ProblematicSound,
        PronunciationPracticeItem, PronunciationFeedback
    )
    
    # Временной период
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Все практики за период
    result = await session.execute(
        select(VoicePractice)
        .where(VoicePractice.user_id == user_id)
        .where(VoicePractice.created_at >= cutoff_date)
        .order_by(VoicePractice.created_at.desc())
    )
    practices = result.scalars().all()
    
    if not practices:
        return PronunciationStatsResponse(
            average_score=0.0,
            total_practices=0,
            scores_by_day=[],
            problematic_sounds=[],
            recent_practices=[]
        )
    
    # Средняя оценка
    avg_score = sum(p.score for p in practices) / len(practices) / 10.0
    
    # Оценки по дням
    scores_by_day_dict = defaultdict(lambda: {"scores": [], "count": 0})
    for p in practices:
        day = p.created_at.date().isoformat()
        scores_by_day_dict[day]["scores"].append(p.score / 10.0)
        scores_by_day_dict[day]["count"] += 1
    
    scores_by_day = [
        ScoreByDay(
            date=day,
            avg_score=sum(data["scores"]) / len(data["scores"]),
            count=data["count"]
        )
        for day, data in sorted(scores_by_day_dict.items())
    ]
    
    # Проблемные звуки (из improve в feedback)
    sound_counter = defaultdict(int)
    common_sounds = ["ö", "ü", "ä", "ch", "r", "h", "sch", "ei", "eu", "ß"]
    
    for p in practices:
        improve_list = p.feedback_json.get("improve", [])
        for item in improve_list:
            item_lower = item.lower()
            for sound in common_sounds:
                if sound in item_lower:
                    sound_counter[sound] += 1
    
    problematic_sounds = [
        ProblematicSound(sound=sound, frequency=count)
        for sound, count in sorted(sound_counter.items(), key=lambda x: -x[1])[:5]
    ]
    
    # Последние 5 практик
    recent = practices[:5]
    recent_practices = [
        PronunciationPracticeItem(
            id=p.id,
            transcription=p.transcription,
            score=p.score / 10.0,
            feedback=PronunciationFeedback(**p.feedback_json),
            attempt_number=p.attempt_number,
            created_at=p.created_at
        )
        for p in recent
    ]
    
    return PronunciationStatsResponse(
        average_score=avg_score,
        total_practices=len(practices),
        scores_by_day=scores_by_day,
        problematic_sounds=problematic_sounds,
        recent_practices=recent_practices
    )


@router.get(
    "/user/{user_id}/pronunciation/history",
    response_model=PronunciationHistoryResponse,
    summary="История практик произношения",
    tags=["Pronunciation"]
)
async def get_pronunciation_history(
    user_id: int = Path(..., description="ID пользователя"),
    limit: int = Query(20, description="Лимит практик"),
    offset: int = Query(0, description="Смещение"),
    session: AsyncSession = Depends(get_session)
):
    """Получить историю практик произношения с пагинацией."""
    from database.models import VoicePractice
    from .models import (
        PronunciationHistoryResponse, PronunciationPracticeItem,
        PronunciationFeedback
    )
    
    # Подсчет total
    total_result = await session.execute(
        select(func.count()).select_from(VoicePractice).where(VoicePractice.user_id == user_id)
    )
    total = total_result.scalar() or 0
    
    # Получаем практики
    result = await session.execute(
        select(VoicePractice)
        .where(VoicePractice.user_id == user_id)
        .order_by(VoicePractice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    practices = result.scalars().all()
    
    items = [
        PronunciationPracticeItem(
            id=p.id,
            transcription=p.transcription,
            score=p.score / 10.0,
            feedback=PronunciationFeedback(**p.feedback_json),
            attempt_number=p.attempt_number,
            created_at=p.created_at
        )
        for p in practices
    ]
    
    return PronunciationHistoryResponse(
        practices=items,
        total=total
    )


# ============ PLACEMENT TEST ENDPOINTS ============

@router.get(
    "/test/questions",
    response_model=PlacementTestQuestionsResponse,
    summary="Получить вопросы для теста",
    tags=["Placement Test"]
)
async def get_placement_questions():
    """
    Возвращает список вопросов для адаптивного теста.
    """
    import json
    import os
    from .models import PlacementTestQuestionsResponse
    
    # Путь к файлу с вопросами
    # Предполагаем, что файл лежит в backend/data/placement_questions.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "data", "placement_questions.json")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            return PlacementTestQuestionsResponse(questions=questions)
    except FileNotFoundError:
        # Если файла нет, возвращаем пустой список (или можно ошибку)
        logger.error(f"Placement questions file not found at {file_path}")
        return PlacementTestQuestionsResponse(questions=[])


@router.post(
    "/test/complete",
    response_model=UpdateResponse,
    summary="Сохранить результаты теста",
    tags=["Placement Test"]
)
async def complete_placement_test(
    data: PlacementTestSubmit,
    session: AsyncSession = Depends(get_session)
) -> UpdateResponse:
    """
    Сохраняет результаты прохождения теста и обновляет уровень пользователя.
    """
    from database.models import PlacementTest, User
    from .models import UpdateResponse
    
    user_id = data.user_id
    
    # Получаем или создаем пользователя
    user = await get_or_create_user(session, user_id)
    
    # Обновляем уровень пользователя
    user.level = data.level_result
    user.updated_at = datetime.now(timezone.utc)
    
    # Создаем запись о прохождении теста
    test_record = PlacementTest(
        user_id=user_id,
        level_result=data.level_result,
        questions_total=data.questions_total,
        correct_total=data.correct_total,
        details_json=data.details
    )
    
    session.add(test_record)
    await session.commit()
    
    return UpdateResponse(
        status="ok",
        message=f"Test completed. New level: {data.level_result}"
    )


@router.post(
    "/user/{user_id}/pronunciation/toggle",
    response_model=UpdateResponse,
    summary="Включить/выключить режим практики",
    tags=["Pronunciation"]
)
async def toggle_practice_mode(
    user_id: int = Path(..., description="ID пользователя"),
    session: AsyncSession = Depends(get_session)
):
    """Переключает режим практики произношения для пользователя."""
    user = await session.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Toggle
    user.practice_mode_enabled = not user.practice_mode_enabled
    user.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()
    
    status = "enabled" if user.practice_mode_enabled else "disabled"
    return UpdateResponse(
        status="ok",
        message=f"Practice mode {status}"
    )


# ============ CHALLENGES ENDPOINTS ============

MAX_CHALLENGES_PER_DAY = 2


@router.get(
    "/challenges/today/{user_id}",
    summary="Получить сегодняшний челлендж",
    tags=["Challenges"]
)
async def get_todays_challenge(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить активный незавершённый челлендж или None.
    Также возвращает сколько челленджей осталось на сегодня.
    """
    from .models import TodayChallengeResponse
    from bot.challenges import get_todays_challenge as get_challenge, TOPICS
    from database.models import UserChallenge
    from sqlalchemy import select, func
    from datetime import date
    
    user = await get_or_create_user(session, user_id)
    
    # Считаем сколько челленджей уже создано сегодня
    today = date.today()
    count_query = select(func.count(UserChallenge.id)).where(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_date == today
    )
    result = await session.execute(count_query)
    today_count = result.scalar() or 0
    remaining = max(0, MAX_CHALLENGES_PER_DAY - today_count)
    
    # Получаем активный (незавершённый) челлендж
    challenge = await get_challenge(session, user_id)
    
    if not challenge:
        return {
            "challenge": None,
            "remaining_today": remaining,
            "max_per_day": MAX_CHALLENGES_PER_DAY
        }
    
    return {
        "challenge": TodayChallengeResponse(
            id=challenge.id,
            date=challenge.challenge_date.isoformat(),
            title=challenge.title,
            description=challenge.description,
            topic=challenge.topic,
            topic_name=TOPICS.get(challenge.topic, challenge.topic),
            challenge_type=challenge.challenge_type,
            grammar_focus=challenge.grammar_focus,
            min_requirements=challenge.min_requirements,
            example_start=challenge.example_start,
            completed=challenge.completed,
            score=challenge.score,
            xp_earned=challenge.xp_earned,
            deadline="21:00"
        ),
        "remaining_today": remaining,
        "max_per_day": MAX_CHALLENGES_PER_DAY
    }


@router.post(
    "/challenges/request/{user_id}",
    summary="Запросить новый челлендж",
    tags=["Challenges"]
)
async def request_new_challenge(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Запросить новый челлендж вручную. Максимум 2 челленджа в день.
    """
    from .models import TodayChallengeResponse
    from bot.challenges import generate_daily_challenge, format_challenge_message, TOPICS
    from database.models import UserChallenge, ChallengeSettings
    from sqlalchemy import select, func
    from datetime import date
    import logging
    
    logger = logging.getLogger(__name__)
    user = await get_or_create_user(session, user_id)
    
    # Проверяем есть ли незавершённый челлендж
    today = date.today()
    active_query = select(UserChallenge).where(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_date == today,
        UserChallenge.completed == False
    )
    result = await session.execute(active_query)
    active = result.scalar_one_or_none()
    
    if active:
        raise HTTPException(
            status_code=400,
            detail="У тебя уже есть активный челлендж. Заверши его сначала!"
        )
    
    # Считаем сколько сегодня
    count_query = select(func.count(UserChallenge.id)).where(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_date == today
    )
    result = await session.execute(count_query)
    today_count = result.scalar() or 0
    
    if today_count >= MAX_CHALLENGES_PER_DAY:
        raise HTTPException(status_code=429, detail=f"Лимит {MAX_CHALLENGES_PER_DAY} челленджа в день!")
    
    # Настройки
    settings = await session.get(ChallengeSettings, user_id)
    if not settings:
        settings = ChallengeSettings(
            user_id=user_id, enabled=True, difficulty=user.level or "A2",
            topics=["daily_life", "work", "food"], formats=["text", "grammar"]
        )
        session.add(settings)
        await session.flush()
    
    # Генерируем
    challenge = await generate_daily_challenge(session, user, settings)
    if not challenge:
        raise HTTPException(status_code=500, detail="Не удалось создать челлендж")
    
    # Отправляем в чат
    try:
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from config import settings as app_settings
        
        bot = Bot(token=app_settings.telegram_bot_token)
        msg = format_challenge_message(challenge, user) + "\n\n✍️ *Напиши свой ответ прямо здесь!*"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отменить челлендж", callback_data=f"cancel_challenge:{challenge.id}")]
        ])
        
        await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown", reply_markup=keyboard)
        await bot.session.close()
        logger.info(f"Challenge sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send challenge: {e}")
    
    remaining = max(0, MAX_CHALLENGES_PER_DAY - today_count - 1)
    
    return {
        "success": True,
        "challenge": TodayChallengeResponse(
            id=challenge.id, date=challenge.challenge_date.isoformat(),
            title=challenge.title, description=challenge.description,
            topic=challenge.topic, topic_name=TOPICS.get(challenge.topic, challenge.topic),
            challenge_type=challenge.challenge_type, grammar_focus=challenge.grammar_focus,
            min_requirements=challenge.min_requirements, example_start=challenge.example_start,
            completed=challenge.completed, score=challenge.score,
            xp_earned=challenge.xp_earned, deadline="21:00"
        ),
        "remaining_today": remaining,
        "message": "Челлендж отправлен в чат!"
    }


@router.get(
    "/challenges/options/{user_id}",
    summary="Получить 3 варианта челленджей на выбор",
    tags=["Challenges"]
)
async def get_challenge_options(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Генерирует 3 варианта челленджей для выбора пользователем.
    """
    from bot.challenges import TOPICS, FORMATS
    from database.models import UserChallenge, ChallengeSettings
    from sqlalchemy import select, func
    from datetime import date
    import random
    
    user = await get_or_create_user(session, user_id)
    
    # Проверяем есть ли незавершённый челлендж
    today = date.today()
    active_query = select(UserChallenge).where(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_date == today,
        UserChallenge.completed == False
    )
    result = await session.execute(active_query)
    active = result.scalar_one_or_none()
    
    if active:
        raise HTTPException(
            status_code=400,
            detail="У тебя уже есть активный челлендж. Заверши его сначала!"
        )
    
    # Считаем сколько челленджей уже создано сегодня
    count_query = select(func.count(UserChallenge.id)).where(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_date == today
    )
    result = await session.execute(count_query)
    today_count = result.scalar() or 0
    
    if today_count >= MAX_CHALLENGES_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Лимит достигнут! Максимум {MAX_CHALLENGES_PER_DAY} челленджа в день."
        )
    
    # Получаем настройки
    settings = await session.get(ChallengeSettings, user_id)
    available_topics = settings.topics if settings and settings.topics else list(TOPICS.keys())
    available_formats = settings.formats if settings and settings.formats else list(FORMATS.keys())
    
    # Генерируем 3 варианта (разные комбинации тема + формат)
    options = []
    used_combinations = set()
    
    for i in range(3):
        # Выбираем уникальную комбинацию
        attempts = 0
        while attempts < 10:
            topic = random.choice(available_topics)
            format_type = random.choice(available_formats)
            combo = (topic, format_type)
            if combo not in used_combinations:
                used_combinations.add(combo)
                break
            attempts += 1
        
        topic_name = TOPICS.get(topic, topic)
        format_name = FORMATS.get(format_type, format_type)
        
        # Создаём preview без сохранения в БД
        options.append({
            "id": i + 1,
            "topic": topic,
            "topic_name": topic_name,
            "format": format_type,
            "format_name": format_name,
            "preview": _generate_challenge_preview(topic_name, format_name)
        })
    
    remaining = max(0, MAX_CHALLENGES_PER_DAY - today_count)
    
    return {
        "options": options,
        "remaining_today": remaining,
        "max_per_day": MAX_CHALLENGES_PER_DAY
    }


def _generate_challenge_preview(topic_name: str, format_name: str) -> str:
    """Генерирует короткое превью для варианта челленджа."""
    previews = {
        ("Повседневная жизнь", "Текстовые (написать)"): "Опиши свой день",
        ("Работа и карьера", "Текстовые (написать)"): "Расскажи о работе мечты",
        ("Путешествия", "Текстовые (написать)"): "Опиши идеальное путешествие",
        ("Еда и рестораны", "Текстовые (написать)"): "Напиши рецепт блюда",
        ("Спорт и хобби", "Текстовые (написать)"): "Расскажи о хобби",
        ("Семья и друзья", "Текстовые (написать)"): "Опиши семейную традицию",
        ("Повседневная жизнь", "Грамматические"): "Perfekt в описании дня",
        ("Работа и карьера", "Грамматические"): "Модальные глаголы на работе",
        ("Путешествия", "Грамматические"): "Futur I для планов",
        ("Еда и рестораны", "Грамматические"): "Imperativ в рецепте",
    }
    return previews.get((topic_name, format_name), f"{topic_name}: {format_name}")


@router.post(
    "/challenges/select/{user_id}",
    summary="Выбрать челлендж и начать",
    tags=["Challenges"]
)
async def select_challenge(
    user_id: int = Path(..., description="Telegram User ID"),
    topic: str = Query(..., description="Выбранная тема"),
    format_type: str = Query(..., alias="format", description="Выбранный формат"),
    session: AsyncSession = Depends(get_session)
):
    """
    Создаёт выбранный челлендж, отправляет в чат и возвращает результат.
    """
    from .models import TodayChallengeResponse
    from bot.challenges import generate_daily_challenge, format_challenge_message, TOPICS
    from database.models import UserChallenge, ChallengeSettings
    from sqlalchemy import select, func
    from datetime import date
    import logging
    
    logger = logging.getLogger(__name__)
    user = await get_or_create_user(session, user_id)
    
    # Проверяем лимит
    today = date.today()
    count_query = select(func.count(UserChallenge.id)).where(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_date == today
    )
    result = await session.execute(count_query)
    today_count = result.scalar() or 0
    
    if today_count >= MAX_CHALLENGES_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Лимит достигнут! Максимум {MAX_CHALLENGES_PER_DAY} челленджа в день."
        )
    
    # Создаём настройки с выбранными параметрами
    settings = ChallengeSettings(
        user_id=user_id,
        enabled=True,
        difficulty=user.level or "A2",
        topics=[topic],
        formats=[format_type]
    )
    
    # Генерируем челлендж
    challenge = await generate_daily_challenge(session, user, settings)
    
    if not challenge:
        raise HTTPException(status_code=500, detail="Не удалось создать челлендж")
    
    # Отправляем в чат бота
    try:
        from aiogram import Bot
        from config import settings as app_settings
        
        logger.info(f"Sending selected challenge to user {user_id}")
        
        bot = Bot(token=app_settings.telegram_bot_token)
        message_text = format_challenge_message(challenge, user)
        message_text += "\n\n✍️ *Напиши свой ответ прямо здесь!*"
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="Markdown"
        )
        await bot.session.close()
        logger.info(f"Challenge sent to user {user_id} successfully")
    except Exception as e:
        import traceback
        logger.error(f"Failed to send challenge to bot: {e}")
        logger.error(traceback.format_exc())
    
    remaining = max(0, MAX_CHALLENGES_PER_DAY - today_count - 1)
    
    return {
        "success": True,
        "challenge": TodayChallengeResponse(
            id=challenge.id,
            date=challenge.challenge_date.isoformat(),
            title=challenge.title,
            description=challenge.description,
            topic=challenge.topic,
            topic_name=TOPICS.get(challenge.topic, challenge.topic),
            challenge_type=challenge.challenge_type,
            grammar_focus=challenge.grammar_focus,
            min_requirements=challenge.min_requirements,
            example_start=challenge.example_start,
            completed=challenge.completed,
            score=challenge.score,
            xp_earned=challenge.xp_earned,
            deadline="21:00"
        ),
        "remaining_today": remaining,
        "message": "Челлендж отправлен в чат! Напиши ответ боту."
    }


@router.post(
    "/challenges/submit",
    summary="Отправить ответ на челлендж",
    tags=["Challenges"]
)
async def submit_challenge_response(
    data: "ChallengeSubmitRequest",
    session: AsyncSession = Depends(get_session)
):
    """
    Отправить ответ на челлендж и получить оценку.
    """
    from .models import ChallengeSubmitRequest, ChallengeSubmitResponse
    from bot.challenges import complete_challenge
    from database.models import UserChallenge
    
    user = await get_or_create_user(session, data.user_id)
    challenge = await session.get(UserChallenge, data.challenge_id)
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge.user_id != data.user_id:
        raise HTTPException(status_code=403, detail="Not your challenge")
    
    if challenge.completed:
        raise HTTPException(status_code=400, detail="Challenge already completed")
    
    result = await complete_challenge(session, challenge, data.response, user)
    
    return ChallengeSubmitResponse(
        success=result.get("success", False),
        completed=result.get("completed", False),
        score=result.get("score"),
        xp_earned=result.get("xp_earned", 0),
        feedback=result.get("feedback", ""),
        corrections=result.get("corrections", []),
        strong_points=result.get("strong_points", []),
        new_streak=result.get("new_streak", 0),
        new_badges=result.get("new_badges", []),
        message=result.get("message")
    )


@router.get(
    "/challenges/settings/{user_id}",
    summary="Получить настройки челленджей",
    tags=["Challenges"]
)
async def get_challenge_settings(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить настройки челленджей пользователя.
    """
    from .models import ChallengeSettingsResponse
    from database.models import ChallengeSettings
    
    await get_or_create_user(session, user_id)
    
    settings = await session.get(ChallengeSettings, user_id)
    
    if not settings:
        # Возвращаем дефолтные настройки
        return ChallengeSettingsResponse(
            enabled=False,
            notification_time="09:00",
            difficulty="A2",
            topics=["daily_life", "work", "food"],
            formats=["text", "grammar"]
        )
    
    return ChallengeSettingsResponse(
        enabled=settings.enabled,
        notification_time=settings.notification_time,
        difficulty=settings.difficulty,
        topics=settings.topics or [],
        formats=settings.formats or []
    )


@router.put(
    "/challenges/settings/{user_id}",
    response_model=UpdateResponse,
    summary="Обновить настройки челленджей",
    tags=["Challenges"]
)
async def update_challenge_settings(
    user_id: int = Path(..., description="Telegram User ID"),
    settings_update: "ChallengeSettingsUpdate" = None,
    session: AsyncSession = Depends(get_session)
):
    """
    Обновить настройки челленджей.
    """
    from .models import ChallengeSettingsUpdate
    from database.models import ChallengeSettings
    
    await get_or_create_user(session, user_id)
    
    settings = await session.get(ChallengeSettings, user_id)
    
    if not settings:
        # Создаём новые настройки
        settings = ChallengeSettings(user_id=user_id)
        session.add(settings)
    
    updated_fields = []
    
    if settings_update.enabled is not None:
        settings.enabled = settings_update.enabled
        updated_fields.append("enabled")
        
    if settings_update.notification_time is not None:
        settings.notification_time = settings_update.notification_time
        updated_fields.append("notification_time")
        
    if settings_update.difficulty is not None:
        settings.difficulty = settings_update.difficulty
        updated_fields.append("difficulty")
        
    if settings_update.topics is not None:
        settings.topics = settings_update.topics
        updated_fields.append("topics")
        
    if settings_update.formats is not None:
        settings.formats = settings_update.formats
        updated_fields.append("formats")
    
    await session.flush()
    
    logger.info("Updated challenge settings for user %d: %s", user_id, updated_fields)
    
    return UpdateResponse(
        status="ok",
        message=f"Updated: {', '.join(updated_fields) or 'nothing'}"
    )


@router.get(
    "/challenges/stats/{user_id}",
    summary="Статистика челленджей",
    tags=["Challenges"]
)
async def get_challenge_stats(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить статистику челленджей: streak, XP, бейджи, прогресс.
    """
    from .models import ChallengeStatsResponse, BadgeItem
    from bot.challenges import get_challenge_stats
    
    await get_or_create_user(session, user_id)
    
    stats = await get_challenge_stats(session, user_id)
    
    if not stats:
        return ChallengeStatsResponse(
            total_xp=0,
            level="Beginner",
            current_streak=0,
            best_streak=0,
            completed_total=0,
            completed_this_month=0,
            average_score=0.0,
            badges=[],
            topics_progress={}
        )
    
    return ChallengeStatsResponse(
        total_xp=stats["total_xp"],
        level=stats["level"],
        current_streak=stats["current_streak"],
        best_streak=stats["best_streak"],
        completed_total=stats["completed_total"],
        completed_this_month=stats["completed_this_month"],
        average_score=stats["average_score"],
        badges=[
            BadgeItem(
                id=b["id"],
                name=b["name"],
                emoji=b["emoji"],
                description=b["description"],
                earned=b["earned"],
                progress=b.get("progress")
            )
            for b in stats["badges"]
        ],
        topics_progress=stats["topics_progress"]
    )


@router.get(
    "/challenges/history/{user_id}",
    summary="История челленджей",
    tags=["Challenges"]
)
async def get_challenges_history(
    user_id: int = Path(..., description="Telegram User ID"),
    limit: int = Query(30, ge=1, le=100, description="Лимит"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить историю выполненных челленджей.
    """
    from .models import ChallengeHistoryResponse, ChallengeHistoryItem
    from bot.challenges import get_challenge_history
    
    await get_or_create_user(session, user_id)
    
    history = await get_challenge_history(session, user_id, limit)
    
    return ChallengeHistoryResponse(
        challenges=[
            ChallengeHistoryItem(
                id=h["id"],
                date=h["date"],
                title=h["title"],
                topic=h["topic"],
                topic_name=h["topic_name"],
                type=h["type"],
                completed=h["completed"],
                score=h["score"],
                xp_earned=h["xp_earned"]
            )
            for h in history
        ],
        total=len(history)
    )


# ============ GRAMMAR EXERCISES ENDPOINTS ============

@router.get(
    "/user/{user_id}/grammar/settings",
    response_model=GrammarSettingsResponse,
    summary="Получить настройки грамматических упражнений",
    tags=["Grammar Exercises"]
)
async def get_grammar_settings(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить текущие настройки грамматических упражнений.
    """
    user = await get_or_create_user(session, user_id)
    
    return GrammarSettingsResponse(
        enabled=user.grammar_exercises_enabled,
        frequency=user.grammar_frequency
    )


@router.put(
    "/user/{user_id}/grammar/settings",
    response_model=UpdateResponse,
    summary="Обновить настройки грамматических упражнений",
    tags=["Grammar Exercises"]
)
async def update_grammar_settings(
    settings: GrammarSettingsUpdate,
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Обновить настройки грамматических упражнений.
    """
    user = await get_or_create_user(session, user_id)
    
    updated_fields = []
    
    if settings.enabled is not None:
        user.grammar_exercises_enabled = settings.enabled
        updated_fields.append("enabled")
    
    if settings.frequency is not None:
        user.grammar_frequency = settings.frequency
        updated_fields.append("frequency")
    
    user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    
    logger.info("Updated grammar settings for user %d: %s", user_id, updated_fields)
    
    return UpdateResponse(
        status="ok",
        message=f"Updated: {', '.join(updated_fields) or 'nothing'}"
    )


@router.get(
    "/user/{user_id}/grammar/stats",
    response_model=GrammarStatsResponse,
    summary="Статистика грамматических упражнений",
    tags=["Grammar Exercises"]
)
async def get_grammar_stats_endpoint(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить статистику грамматических упражнений.
    """
    from bot.grammar_exercises import get_grammar_stats
    
    await get_or_create_user(session, user_id)
    stats = await get_grammar_stats(session, user_id)
    
    weak_topics = [
        WeakTopicItem(
            topic=t["topic"],
            name=t["name"],
            accuracy=t["accuracy"],
            total=t["total"],
            correct=t["correct"]
        )
        for t in stats["weak_topics"]
    ]
    
    return GrammarStatsResponse(
        total_exercises=stats["total_exercises"],
        correct_answers=stats["correct_answers"],
        accuracy=stats["accuracy"],
        weak_topics=weak_topics,
        by_topic=stats["by_topic"]
    )


@router.get(
    "/grammar/topics",
    response_model=GrammarTopicsResponse,
    summary="Список тем грамматических упражнений",
    tags=["Grammar Exercises"]
)
async def get_grammar_topics():
    """
    Получить список всех доступных тем для упражнений.
    """
    from bot.grammar_exercises import GRAMMAR_TOPICS
    
    topics = [
        GrammarTopicInfo(
            id=topic_id,
            name=topic_info["name"],
            name_de=topic_info["name_de"],
            description=topic_info["description"],
            premium=topic_info["premium"]
        )
        for topic_id, topic_info in GRAMMAR_TOPICS.items()
    ]
    
    return GrammarTopicsResponse(topics=topics)


# ============ STREAK ENDPOINTS ============

@router.get(
    "/streak/{user_id}",
    summary="Получить информацию о streak",
    tags=["Streak"]
)
async def get_streak_info(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить полную информацию о streak пользователя:
    - Текущий и лучший streak
    - Прогресс сегодня
    - Следующий milestone
    - Доступные freeze
    - Активность за неделю
    - Бейджи за streak
    """
    from .models import (
        StreakInfoResponse, DailyActivity, StreakBadge, NextMilestoneReward
    )
    from bot.streak_service import get_streak_info as get_info
    
    user = await get_or_create_user(session, user_id)
    info = await get_info(session, user)
    
    weekly_activity = [
        DailyActivity(
            date=a["date"],
            weekday=a["weekday"],
            messages=a["messages"],
            completed=a["completed"]
        )
        for a in info["weekly_activity"]
    ]
    
    streak_badges = [
        StreakBadge(
            id=b["id"],
            day=b["day"],
            name=b["name"],
            emoji=b["emoji"],
            description=b["description"],
            earned=b["earned"],
            xp=b["xp"]
        )
        for b in info["streak_badges"]
    ]
    
    next_milestone_reward = None
    if info.get("next_milestone_reward"):
        r = info["next_milestone_reward"]
        next_milestone_reward = NextMilestoneReward(
            name=r["name"],
            emoji=r["emoji"],
            xp=r["xp"],
            premium_days=r["premium_days"]
        )
    
    return StreakInfoResponse(
        streak_days=info["streak_days"],
        best_streak=info["best_streak"],
        streak_start_date=info["streak_start_date"],
        daily_progress=info["daily_progress"],
        daily_goal=info["daily_goal"],
        daily_goal_reached=info["daily_goal_reached"],
        next_milestone=info["next_milestone"],
        next_milestone_reward=next_milestone_reward,
        xp_today=info["xp_today"],
        xp_week=info["xp_week"],
        xp_month=info["xp_month"],
        total_xp=info["total_xp"],
        freeze_available=info["freeze_available"],
        freeze_used_today=info["freeze_used_today"],
        weekly_activity=weekly_activity,
        streak_badges=streak_badges
    )


@router.post(
    "/streak/{user_id}/freeze",
    summary="Использовать streak freeze",
    tags=["Streak"]
)
async def use_streak_freeze(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Использовать streak freeze для защиты streak.
    """
    from .models import StreakFreezeResponse
    from bot.streak_service import use_streak_freeze as use_freeze
    
    user = await get_or_create_user(session, user_id)
    result = await use_freeze(session, user)
    await session.commit()
    
    return StreakFreezeResponse(
        success=result["success"],
        message=result["message"],
        remaining=result["remaining"]
    )


@router.put(
    "/streak/{user_id}/settings",
    response_model=UpdateResponse,
    summary="Обновить настройки streak",
    tags=["Streak"]
)
async def update_streak_settings(
    settings: StreakSettingsUpdate,
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Обновить настройки streak напоминаний и анонимности.
    """
    
    user = await get_or_create_user(session, user_id)
    updated = []
    
    if settings.reminder_enabled is not None:
        user.streak_reminder_enabled = settings.reminder_enabled
        updated.append("reminder_enabled")
    
    if settings.anonymous_leaderboard is not None:
        user.is_anonymous_leaderboard = settings.anonymous_leaderboard
        updated.append("anonymous")
    
    user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    
    return UpdateResponse(
        status="ok",
        message=f"Updated: {', '.join(updated) or 'nothing'}"
    )


# ============ LEADERBOARD ENDPOINTS ============

@router.get(
    "/leaderboard/{category}",
    summary="Получить leaderboard",
    tags=["Leaderboard"]
)
async def get_leaderboard(
    category: str = Path(..., description="Категория: weekly, monthly, streak"),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = Query(None, description="ID пользователя для подсветки"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить глобальный leaderboard по категории.
    """
    from .models import LeaderboardResponse, LeaderboardEntry
    from database.models import UserBadge
    
    if category == "weekly":
        order_by = User.weekly_xp.desc()
        xp_field = "weekly_xp"
    elif category == "monthly":
        order_by = User.monthly_xp.desc()
        xp_field = "monthly_xp"
    elif category == "streak":
        order_by = User.streak_days.desc()
        xp_field = "streak_days"
    else:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    # Получаем топ пользователей
    result = await session.execute(
        select(User).where(
            User.is_anonymous_leaderboard == False
        ).order_by(order_by).limit(limit)
    )
    users = result.scalars().all()
    
    # Считаем общее количество участников
    total_result = await session.execute(
        select(func.count()).select_from(User).where(
            User.is_anonymous_leaderboard == False
        )
    )
    total = total_result.scalar() or 0
    
    entries = []
    user_entry = None
    user_rank = None
    
    for i, u in enumerate(users):
        # Считаем бейджи
        badges_result = await session.execute(
            select(func.count()).select_from(UserBadge).where(UserBadge.user_id == u.user_id)
        )
        badges_count = badges_result.scalar() or 0
        
        xp = getattr(u, xp_field) if category != "streak" else u.weekly_xp
        streak = u.streak_days
        
        entry = LeaderboardEntry(
            rank=i + 1,
            user_id=u.user_id,
            username=u.username,
            display_name=u.first_name or u.username or f"User{u.user_id}",
            level=u.level,
            xp=xp,
            streak=streak,
            badges_count=badges_count,
            is_current_user=(u.user_id == user_id)
        )
        entries.append(entry)
        
        if u.user_id == user_id:
            user_entry = entry
            user_rank = i + 1
    
    # Если пользователь не в топе, найдём его позицию
    if user_id and not user_entry:
        target_user = await session.get(User, user_id)
        if target_user and not target_user.is_anonymous_leaderboard:
            # Считаем позицию пользователя
            if category == "weekly":
                rank_result = await session.execute(
                    select(func.count()).select_from(User).where(
                        User.weekly_xp > target_user.weekly_xp,
                        User.is_anonymous_leaderboard == False
                    )
                )
            elif category == "monthly":
                rank_result = await session.execute(
                    select(func.count()).select_from(User).where(
                        User.monthly_xp > target_user.monthly_xp,
                        User.is_anonymous_leaderboard == False
                    )
                )
            else:
                rank_result = await session.execute(
                    select(func.count()).select_from(User).where(
                        User.streak_days > target_user.streak_days,
                        User.is_anonymous_leaderboard == False
                    )
                )
            user_rank = (rank_result.scalar() or 0) + 1
            
            badges_result = await session.execute(
                select(func.count()).select_from(UserBadge).where(UserBadge.user_id == user_id)
            )
            badges_count = badges_result.scalar() or 0
            
            xp = getattr(target_user, xp_field) if category != "streak" else target_user.weekly_xp
            
            user_entry = LeaderboardEntry(
                rank=user_rank,
                user_id=target_user.user_id,
                username=target_user.username,
                display_name=target_user.first_name or target_user.username or f"User{target_user.user_id}",
                level=target_user.level,
                xp=xp,
                streak=target_user.streak_days,
                badges_count=badges_count,
                is_current_user=True
            )
    
    return LeaderboardResponse(
        entries=entries,
        total_participants=total,
        user_rank=user_rank,
        user_entry=user_entry,
        category=category
    )


@router.get(
    "/leaderboard/position/{user_id}",
    summary="Позиция пользователя во всех leaderboard",
    tags=["Leaderboard"]
)
async def get_user_position(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить позицию пользователя во всех категориях leaderboard.
    """
    from .models import UserPositionResponse
    
    user = await get_or_create_user(session, user_id)
    
    # Позиция по недельному XP
    weekly_result = await session.execute(
        select(func.count()).select_from(User).where(
            User.weekly_xp > user.weekly_xp,
            User.is_anonymous_leaderboard == False
        )
    )
    weekly_rank = (weekly_result.scalar() or 0) + 1
    
    # Позиция по месячному XP
    monthly_result = await session.execute(
        select(func.count()).select_from(User).where(
            User.monthly_xp > user.monthly_xp,
            User.is_anonymous_leaderboard == False
        )
    )
    monthly_rank = (monthly_result.scalar() or 0) + 1
    
    # Позиция по streak
    streak_result = await session.execute(
        select(func.count()).select_from(User).where(
            User.streak_days > user.streak_days,
            User.is_anonymous_leaderboard == False
        )
    )
    streak_rank = (streak_result.scalar() or 0) + 1
    
    # Общее количество участников
    total_result = await session.execute(
        select(func.count()).select_from(User).where(
            User.is_anonymous_leaderboard == False
        )
    )
    total = total_result.scalar() or 0
    
    return UserPositionResponse(
        weekly_rank=weekly_rank,
        weekly_total=total,
        monthly_rank=monthly_rank,
        streak_rank=streak_rank,
        change_from_last_week=0  # TODO: track position changes
    )


@router.get(
    "/profile/{user_id}/public",
    summary="Публичный профиль пользователя",
    tags=["Profile"]
)
async def get_public_profile(
    user_id: int = Path(..., description="Telegram User ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить публичный профиль пользователя для leaderboard.
    """
    from .models import PublicProfileResponse, BadgeItem
    from database.models import UserBadge
    from bot.streak_service import STREAK_MILESTONES
    
    user = await session.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_anonymous_leaderboard:
        raise HTTPException(status_code=403, detail="Profile is private")
    
    # Получаем бейджи
    badges_result = await session.execute(
        select(UserBadge).where(UserBadge.user_id == user_id)
    )
    user_badges = badges_result.scalars().all()
    
    badges = []
    for badge in user_badges:
        # Ищем информацию о бейдже в STREAK_MILESTONES
        for day, info in STREAK_MILESTONES.items():
            if info["badge_id"] == badge.badge_id:
                badges.append(BadgeItem(
                    id=badge.badge_id,
                    name=info["name"],
                    emoji=info["emoji"],
                    description=info["description"],
                    earned=True,
                    progress=None
                ))
                break
    
    return PublicProfileResponse(
        user_id=user.user_id,
        display_name=user.first_name or user.username or f"User{user.user_id}",
        level=user.level,
        streak_days=user.streak_days,
        total_xp=user.total_xp,
        badges=badges,
        studying_since=user.created_at.strftime("%d.%m.%Y"),
        recent_achievements=[]
    )
