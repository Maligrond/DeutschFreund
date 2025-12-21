"""
Pydantic модели для API запросов и ответов.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============ MESSAGE MODELS ============

class MessageItem(BaseModel):
    """Сообщение в истории."""
    role: str = Field(..., description="user или assistant")
    content: str = Field(..., description="Текст сообщения")
    created_at: datetime = Field(..., description="Время создания")
    tokens_used: Optional[int] = Field(None, description="Использовано токенов")


class HistoryResponse(BaseModel):
    """Ответ с историей сообщений."""
    messages: List[MessageItem] = Field(..., description="Список сообщений")
    total: int = Field(..., description="Общее количество сообщений")
    limit: int = Field(..., description="Лимит на страницу")
    offset: int = Field(..., description="Смещение")


# ============ STATS MODELS ============

class MessagesByDay(BaseModel):
    """Статистика сообщений за день."""
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    count: int = Field(..., description="Количество сообщений")


class StatsResponse(BaseModel):
    """Статистика пользователя."""
    streak_days: int = Field(..., description="Дней подряд")
    total_messages: int = Field(..., description="Всего сообщений")
    level: str = Field(..., description="Уровень A1-C2")
    goal: Optional[str] = Field(None, description="Цель обучения")
    new_words_count: int = Field(..., description="Количество новых слов")
    learned_words_count: int = Field(0, description="Количество выученных слов")
    recent_words: List['VocabularyItem'] = Field(default_factory=list, description="Последние добавленные слова")
    messages_by_day: List[MessagesByDay] = Field(..., description="Сообщения по дням")
    accuracy: float = Field(..., description="Процент правильных сообщений")
    created_at: datetime = Field(..., description="Дата регистрации")
    
    # Progress fields
    total_xp: int = Field(0, description="Всего XP")
    next_level: Optional[str] = Field(None, description="Следующий уровень")
    level_xp_start: int = Field(0, description="XP начала уровня")
    level_xp_end: Optional[int] = Field(None, description="XP конца уровня")
    progress_percent: int = Field(0, description="Процент прогресса текущего уровня")
    xp_needed: int = Field(0, description="XP до следующего уровня")


# ============ VOCABULARY MODELS ============

class VocabularyItem(BaseModel):
    """Слово в словаре."""
    id: int
    word_de: str = Field(..., description="Немецкое слово")
    word_ru: str = Field(..., description="Русский перевод")
    times_seen: int = Field(..., description="Сколько раз встречалось")
    learned: bool = Field(..., description="Выучено или нет")
    created_at: datetime = Field(..., description="Когда добавлено")


class VocabularyResponse(BaseModel):
    """Ответ со словарём пользователя."""
    words: List[VocabularyItem] = Field(..., description="Список слов")
    total: int = Field(..., description="Всего слов")
    total_learned: int = Field(..., description="Выучено слов")


# ============ SETTINGS MODELS ============

class SettingsUpdate(BaseModel):
    """Обновление настроек пользователя."""
    level: Optional[str] = Field(None, description="Уровень")
    goal: Optional[str] = Field(None, max_length=500, description="Цель обучения")
    reminder_enabled: Optional[bool] = Field(None, description="Напоминания вкл/выкл")
    reminder_frequency: Optional[int] = Field(None, ge=1, le=14, description="Частота напоминаний (дни)")
    bot_personality: Optional[str] = Field(None, pattern="^(friendly|strict|romantic)$", description="Личность бота")


class SettingsResponse(BaseModel):
    """Текущие настройки пользователя."""
    level: str
    goal: Optional[str]
    reminder_enabled: bool
    reminder_frequency: int
    bot_personality: str
    practice_mode_enabled: bool = False


class UpdateResponse(BaseModel):
    """Ответ на обновление."""
    status: str = "ok"
    message: str = "Updated successfully"


# ============ CONTEXT MODELS ============

class UserContext(BaseModel):
    """Контекст пользователя."""
    name: Optional[str] = Field(None, description="Имя")
    city: Optional[str] = Field(None, description="Город проживания")
    job: Optional[str] = Field(None, description="Работа/профессия")
    interests: Optional[List[str]] = Field(None, description="Интересы")
    problems: Optional[List[str]] = Field(None, description="Проблемы/сложности")
    extra: Optional[dict] = Field(None, description="Дополнительные данные")


class ContextResponse(BaseModel):
    """Ответ с контекстом."""
    context: UserContext
    updated_at: Optional[datetime] = None


# ============ USER MODELS ============

class UserProfile(BaseModel):
    """Профиль пользователя."""
    user_id: int
    username: Optional[str]
    first_name: str
    level: str
    goal: Optional[str]
    streak_days: int
    total_messages: int
    reminder_enabled: bool
    bot_personality: str
    created_at: datetime


# ============ ERROR MODELS ============

class ErrorResponse(BaseModel):
    """Ответ с ошибкой."""
    detail: str = Field(..., description="Описание ошибки")
    error_code: Optional[str] = Field(None, description="Код ошибки")


# ============ INTERACTIVE TEXT MODELS ============

class SingleMessageResponse(BaseModel):
    """Ответ с одним сообщением."""
    id: int = Field(..., description="ID сообщения")
    content: str = Field(..., description="Текст сообщения")
    created_at: datetime = Field(..., description="Время создания")


class TranslateWordRequest(BaseModel):
    """Запрос на перевод слова."""
    word: str = Field(..., min_length=1, max_length=100, description="Слово для перевода")


class TranslateWordResponse(BaseModel):
    """Ответ с переводом слова."""
    word: str = Field(..., description="Исходное слово")
    translation: str = Field(..., description="Перевод")


class TranslateAllResponse(BaseModel):
    """Ответ с полным переводом."""
    original: str = Field(..., description="Оригинальный текст")
    translation: str = Field(..., description="Перевод")


class AddFavoriteRequest(BaseModel):
    """Запрос на добавление слова в избранное."""
    user_id: int = Field(..., description="Telegram User ID")
    word_de: str = Field(..., min_length=1, max_length=255, description="Немецкое слово")
    word_ru: str = Field(..., min_length=1, max_length=255, description="Русский перевод")
    context: Optional[str] = Field(None, max_length=500, description="Контекст использования")


class FavoriteWordItem(BaseModel):
    """Слово в избранном."""
    id: int
    word_de: str
    word_ru: str
    times_seen: int
    learned: bool
    created_at: datetime



class FavoritesResponse(BaseModel):
    """Ответ со списком избранных слов."""
    words: List[FavoriteWordItem]
    total: int


# ============ PRONUNCIATION MODELS ============

class PronunciationFeedback(BaseModel):
    """Детали фидбека по произношению."""
    score: float = Field(..., description="Оценка от 1.0 до 10.0")
    good: List[str] = Field(..., description="Что звучит хорошо")
    improve: List[str] = Field(..., description="Что можно улучшить")
    tip: str = Field(..., description="Главный совет")


class PronunciationPracticeItem(BaseModel):
    """Одна практика произношения."""
    id: int
    transcription: str
    score: float
    feedback: PronunciationFeedback
    attempt_number: int
    created_at: datetime


class PronunciationHistoryResponse(BaseModel):
    """История практик произношения."""
    practices: List[PronunciationPracticeItem]
    total: int


class ScoreByDay(BaseModel):
    """Оценка за день."""
    date: str = Field(..., description="Дата YYYY-MM-DD")
    avg_score: float = Field(..., description="Средняя оценка")
    count: int = Field(..., description="Количество практик")


class ProblematicSound(BaseModel):
    """Проблемный звук."""
    sound: str = Field(..., description="Звук (например 'ö')")
    frequency: int = Field(..., description="Сколько раз встречался в ошибках")


class PronunciationStatsResponse(BaseModel):
    """Статистика произношения."""
    average_score: float = Field(..., description="Средняя оценка за период")
    total_practices: int = Field(..., description="Всего практик")
    scores_by_day: List[ScoreByDay] = Field(..., description="Оценки по дням за 30 дней")
    problematic_sounds: List[ProblematicSound] = Field(..., description="Проблемные звуки")
    recent_practices: List[PronunciationPracticeItem] = Field(..., description="Последние 5 практик")


# ============ CHALLENGE MODELS ============

class ChallengeSettingsResponse(BaseModel):
    """Настройки челленджей пользователя."""
    enabled: bool = Field(..., description="Включены ли челленджи")
    notification_time: str = Field(..., description="Время уведомления HH:MM")
    difficulty: str = Field(..., description="Сложность A1/A2/B1")
    topics: List[str] = Field(..., description="Выбранные темы")
    formats: List[str] = Field(..., description="Выбранные форматы")


class ChallengeSettingsUpdate(BaseModel):
    """Обновление настроек челленджей."""
    enabled: Optional[bool] = Field(None, description="Включить/выключить")
    notification_time: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Время HH:MM")
    difficulty: Optional[str] = Field(None, pattern="^(A1|A2|B1)$", description="Сложность")
    topics: Optional[List[str]] = Field(None, description="Темы")
    formats: Optional[List[str]] = Field(None, description="Форматы")


class TodayChallengeResponse(BaseModel):
    """Сегодняшний челлендж."""
    id: int = Field(..., description="ID челленджа")
    date: str = Field(..., description="Дата YYYY-MM-DD")
    title: str = Field(..., description="Название")
    description: str = Field(..., description="Описание задания")
    topic: str = Field(..., description="Тема")
    topic_name: str = Field(..., description="Название темы на русском")
    challenge_type: str = Field(..., description="Тип челленджа")
    grammar_focus: Optional[str] = Field(None, description="Грамматический фокус")
    min_requirements: str = Field(..., description="Минимальные требования")
    example_start: Optional[str] = Field(None, description="Пример начала")
    completed: bool = Field(..., description="Выполнен ли")
    score: Optional[int] = Field(None, description="Оценка 1-10")
    xp_earned: int = Field(0, description="Заработано XP")
    deadline: str = Field("21:00", description="Дедлайн")


class ChallengeSubmitRequest(BaseModel):
    """Запрос на отправку ответа."""
    user_id: int = Field(..., description="Telegram User ID")
    challenge_id: int = Field(..., description="ID челленджа")
    response: str = Field(..., min_length=10, description="Ответ пользователя")


class ChallengeSubmitResponse(BaseModel):
    """Ответ на отправку ответа."""
    success: bool = Field(..., description="Успешно ли")
    completed: bool = Field(False, description="Засчитан ли челлендж")
    score: Optional[int] = Field(None, description="Оценка 1-10")
    xp_earned: int = Field(0, description="Заработано XP")
    feedback: str = Field("", description="Фидбек")
    corrections: List[str] = Field(default_factory=list, description="Исправления")
    strong_points: List[str] = Field(default_factory=list, description="Сильные стороны")
    new_streak: int = Field(0, description="Новый streak")
    new_badges: List[str] = Field(default_factory=list, description="Новые бейджи")
    message: Optional[str] = Field(None, description="Сообщение если не успешно")


class BadgeItem(BaseModel):
    """Бейдж."""
    id: str = Field(..., description="ID бейджа")
    name: str = Field(..., description="Название")
    emoji: str = Field(..., description="Эмодзи")
    description: str = Field(..., description="Описание")
    earned: bool = Field(..., description="Получен ли")
    progress: Optional[str] = Field(None, description="Прогресс (например 5/7)")


class ChallengeStatsResponse(BaseModel):
    """Статистика челленджей."""
    total_xp: int = Field(..., description="Всего XP")
    level: str = Field(..., description="Уровень: Beginner/Intermediate/Advanced/Expert")
    current_streak: int = Field(..., description="Текущий streak")
    best_streak: int = Field(..., description="Лучший streak")
    completed_total: int = Field(..., description="Всего выполнено")
    completed_this_month: int = Field(..., description="Выполнено в этом месяце")
    average_score: float = Field(..., description="Средняя оценка")
    badges: List[BadgeItem] = Field(..., description="Бейджи")
    topics_progress: dict = Field(..., description="Прогресс по темам {topic_id: percent}")


class ChallengeHistoryItem(BaseModel):
    """Элемент истории челленджей."""
    id: int
    date: str
    title: str
    topic: str
    topic_name: str
    type: str
    completed: bool
    score: Optional[int]
    xp_earned: int


class ChallengeHistoryResponse(BaseModel):
    """История челленджей."""
    challenges: List[ChallengeHistoryItem] = Field(..., description="Челленджи")
    total: int = Field(..., description="Всего")


# ============ GRAMMAR EXERCISE MODELS ============

class GrammarSettingsResponse(BaseModel):
    """Настройки грамматических упражнений."""
    enabled: bool = Field(..., description="Включены ли упражнения")
    frequency: str = Field(..., description="Частота: rare/medium/often")


class GrammarSettingsUpdate(BaseModel):
    """Обновление настроек грамматических упражнений."""
    enabled: Optional[bool] = Field(None, description="Включить/выключить")
    frequency: Optional[str] = Field(None, pattern="^(rare|medium|often)$", description="Частота")


class WeakTopicItem(BaseModel):
    """Слабая тема."""
    topic: str = Field(..., description="ID темы")
    name: str = Field(..., description="Название на русском")
    accuracy: float = Field(..., description="Процент правильных ответов")
    total: int = Field(..., description="Всего упражнений")
    correct: int = Field(..., description="Правильных ответов")


class TopicStatsItem(BaseModel):
    """Статистика по одной теме."""
    name: str = Field(..., description="Название темы")
    total: int = Field(..., description="Всего упражнений")
    correct: int = Field(..., description="Правильных ответов")
    accuracy: float = Field(..., description="Процент правильных")


class GrammarExercisesByDay(BaseModel):
    """Упражнения по дням."""
    date: str = Field(..., description="Дата YYYY-MM-DD")
    total: int = Field(..., description="Всего за день")
    correct: int = Field(..., description="Правильных")


class GrammarStatsResponse(BaseModel):
    """Статистика грамматических упражнений."""
    total_exercises: int = Field(..., description="Всего упражнений")
    correct_answers: int = Field(..., description="Правильных ответов")
    accuracy: float = Field(..., description="Процент правильных")
    weak_topics: List[WeakTopicItem] = Field(..., description="Слабые темы")
    by_topic: dict = Field(..., description="Статистика по каждой теме")


class GrammarTopicInfo(BaseModel):
    """Информация о теме."""
    id: str = Field(..., description="ID темы")
    name: str = Field(..., description="Название на русском")
    name_de: str = Field(..., description="Название на немецком")
    description: str = Field(..., description="Описание")
    premium: bool = Field(..., description="Только для premium")


class GrammarTopicsResponse(BaseModel):
    """Список доступных тем."""
    topics: List[GrammarTopicInfo] = Field(..., description="Все темы")


# ============ STREAK MODELS ============

class DailyActivity(BaseModel):
    """Активность за один день."""
    date: str = Field(..., description="Дата YYYY-MM-DD")
    weekday: str = Field(..., description="День недели")
    messages: int = Field(..., description="Количество сообщений")
    completed: bool = Field(..., description="Цель дня достигнута")


class StreakBadge(BaseModel):
    """Бейдж за streak."""
    id: str = Field(..., description="ID бейджа")
    day: int = Field(..., description="Milestone день")
    name: str = Field(..., description="Название")
    emoji: str = Field(..., description="Эмодзи")
    description: str = Field(..., description="Описание")
    earned: bool = Field(..., description="Получен ли")
    xp: int = Field(..., description="XP за достижение")


class NextMilestoneReward(BaseModel):
    """Награда за следующий milestone."""
    name: str = Field(..., description="Название")
    emoji: str = Field(..., description="Эмодзи")
    xp: int = Field(..., description="XP")
    premium_days: int = Field(..., description="Дни Premium")


class StreakInfoResponse(BaseModel):
    """Полная информация о streak пользователя."""
    streak_days: int = Field(..., description="Текущий streak")
    best_streak: int = Field(..., description="Лучший streak")
    streak_start_date: Optional[str] = Field(None, description="Начало streak")
    daily_progress: int = Field(..., description="Сообщений сегодня")
    daily_goal: int = Field(5, description="Цель на день")
    daily_goal_reached: bool = Field(..., description="Цель достигнута")
    next_milestone: Optional[int] = Field(None, description="Следующий milestone")
    next_milestone_reward: Optional[NextMilestoneReward] = Field(None, description="Награда")
    xp_today: int = Field(0, description="XP за сегодня")
    xp_week: int = Field(..., description="XP за неделю")
    xp_month: int = Field(..., description="XP за месяц")
    total_xp: int = Field(..., description="Всего XP")
    freeze_available: int = Field(..., description="Доступных freeze")
    freeze_used_today: bool = Field(..., description="Freeze использован сегодня")
    weekly_activity: List[DailyActivity] = Field(..., description="Активность за 7 дней")
    streak_badges: List[StreakBadge] = Field(..., description="Бейджи за streak")


class StreakFreezeResponse(BaseModel):
    """Результат использования streak freeze."""
    success: bool = Field(..., description="Успешно ли")
    message: str = Field(..., description="Сообщение")
    remaining: int = Field(..., description="Осталось freeze")


class StreakSettingsUpdate(BaseModel):
    """Обновление настроек streak."""
    reminder_enabled: Optional[bool] = Field(None, description="Напоминания")
    anonymous_leaderboard: Optional[bool] = Field(None, description="Анонимность")


# ============ LEADERBOARD MODELS ============

class LeaderboardEntry(BaseModel):
    """Запись в leaderboard."""
    rank: int = Field(..., description="Позиция")
    user_id: int = Field(..., description="ID пользователя")
    username: Optional[str] = Field(None, description="Username")
    display_name: str = Field(..., description="Отображаемое имя")
    level: str = Field(..., description="Уровень немецкого")
    xp: int = Field(..., description="XP")
    streak: int = Field(..., description="Streak дней")
    badges_count: int = Field(0, description="Количество бейджей")
    is_current_user: bool = Field(False, description="Это текущий пользователь")


class LeaderboardResponse(BaseModel):
    """Ответ с leaderboard."""
    entries: List[LeaderboardEntry] = Field(..., description="Записи")
    total_participants: int = Field(..., description="Всего участников")
    user_rank: Optional[int] = Field(None, description="Позиция пользователя")
    user_entry: Optional[LeaderboardEntry] = Field(None, description="Запись пользователя")
    category: str = Field(..., description="Категория: weekly_xp, monthly_xp, streak")


class UserPositionResponse(BaseModel):
    """Позиция пользователя в разных leaderboard."""
    weekly_rank: int = Field(..., description="Позиция по неделе")
    weekly_total: int = Field(..., description="Всего участников")
    monthly_rank: int = Field(..., description="Позиция по месяцу")
    streak_rank: int = Field(..., description="Позиция по streak")
    change_from_last_week: int = Field(0, description="Изменение позиции")


class PublicProfileResponse(BaseModel):
    """Публичный профиль пользователя."""
    user_id: int = Field(..., description="ID")
    display_name: str = Field(..., description="Имя")
    level: str = Field(..., description="Уровень")
    streak_days: int = Field(..., description="Streak")
    total_xp: int = Field(..., description="Всего XP")
    badges: List[BadgeItem] = Field(..., description="Бейджи")
    studying_since: str = Field(..., description="Учится с")
    recent_achievements: List[dict] = Field(default_factory=list, description="Достижения")


# ============ FRIENDS MODELS ============

class FriendItem(BaseModel):
    """Друг в списке."""
    user_id: int = Field(..., description="ID")
    username: Optional[str] = Field(None, description="Username")
    display_name: str = Field(..., description="Имя")
    level: str = Field(..., description="Уровень")
    streak: int = Field(..., description="Streak")
    weekly_xp: int = Field(..., description="XP за неделю")
    status: str = Field(..., description="Статус: pending, accepted")


class FriendsListResponse(BaseModel):
    """Список друзей."""
    friends: List[FriendItem] = Field(..., description="Друзья")
    total: int = Field(..., description="Всего")


    friend_username: str = Field(..., min_length=1, max_length=255, description="Username друга")


# ============ PLACEMENT TEST MODELS ============

class PlacementQuestion(BaseModel):
    """Вопрос теста на определение уровня."""
    id: int = Field(..., description="ID вопроса")
    level: str = Field(..., description="Уровень (A1-C1)")
    question: str = Field(..., description="Текст вопроса")
    options: List[str] = Field(..., description="Варианты ответов")
    correct_index: int = Field(..., description="Индекс правильного ответа")


class PlacementTestQuestionsResponse(BaseModel):
    """Список вопросов для теста."""
    questions: List[PlacementQuestion] = Field(..., description="Список вопросов")


class PlacementTestSubmit(BaseModel):
    """Отправка результатов теста."""
    user_id: int = Field(..., description="Telegram User ID")
    level_result: str = Field(..., description="Определенный уровень")
    questions_total: int = Field(..., description="Всего пройдено вопросов")
    correct_total: int = Field(..., description="Всего правильных ответов")
    details: dict = Field(..., description="Детализация по уровням")
