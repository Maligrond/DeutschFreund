"""
SQLAlchemy модели для приложения изучения немецкого языка.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, 
    DateTime, Date, ForeignKey, Index, JSON, Float
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from .db import Base


class User(Base):
    """Модель пользователя Telegram."""
    
    __tablename__ = "users"
    
    # Primary key - Telegram user ID
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Telegram данные
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Настройки обучения
    level: Mapped[str] = mapped_column(String(10), default="A2", nullable=False)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Статистика (сообщения)
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_proactive_message_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Система XP и челленджей
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    challenge_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_challenge_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_challenge_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Streak система (расширенная)
    streak_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_daily_reset: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Streak Freeze
    streak_freeze_available: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    streak_freeze_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    streak_freeze_week_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Награды
    last_streak_reward_day: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Leaderboard
    is_anonymous_leaderboard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weekly_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_week_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    xp_month_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Timezone пользователя (для корректного расчёта streak)
    user_timezone: Mapped[str] = mapped_column(String(50), default="Europe/Berlin", nullable=False)
    
    # Настройки streak напоминаний
    streak_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Настройки напоминаний (proactive messages)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_frequency: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    
    # Персональность бота
    bot_personality: Mapped[str] = mapped_column(
        String(50), default="friendly", nullable=False
    )  # friendly / strict / romantic
    
    # Режим практики произношения
    practice_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Грамматические упражнения
    grammar_exercises_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    grammar_frequency: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )  # rare / medium / often
    last_grammar_exercise: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    grammar_message_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_grammar_exercises: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_grammar_exercises: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="user", cascade="all, delete-orphan"
    )
    context: Mapped[Optional["UserContext"]] = relationship(
        "UserContext", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    vocabulary: Mapped[List["Vocabulary"]] = relationship(
        "Vocabulary", back_populates="user", cascade="all, delete-orphan"
    )
    challenge_settings: Mapped[Optional["ChallengeSettings"]] = relationship(
        "ChallengeSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    challenges: Mapped[List["UserChallenge"]] = relationship(
        "UserChallenge", back_populates="user", cascade="all, delete-orphan"
    )
    badges: Mapped[List["UserBadge"]] = relationship(
        "UserBadge", back_populates="user", cascade="all, delete-orphan"
    )
    grammar_exercises: Mapped[List["GrammarExercise"]] = relationship(
        "GrammarExercise", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, username={self.username}, level={self.level})>"


class Message(Base):
    """История сообщений между пользователем и ботом."""
    
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Содержимое сообщения
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" или "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Метаданные
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index("ix_messages_user_id", "user_id"),
        Index("ix_messages_created_at", "created_at"),
        Index("ix_messages_user_id_created_at", "user_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, user_id={self.user_id}, role={self.role})>"


class UserContext(Base):
    """Контекст пользователя для персонализации диалогов."""
    
    __tablename__ = "user_contexts"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    
    # JSON с контекстом: город, работа, проблемы, интересы, etc.
    context_data: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    
    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="context")
    
    def __repr__(self) -> str:
        return f"<UserContext(user_id={self.user_id})>"


class Vocabulary(Base):
    """Словарь изученных слов пользователя."""
    
    __tablename__ = "vocabulary"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Слово
    word_de: Mapped[str] = mapped_column(String(255), nullable=False)  # Немецкое слово
    word_ru: Mapped[str] = mapped_column(String(255), nullable=False)  # Перевод
    
    # Прогресс
    times_seen: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    learned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # SRS fields (Anki-style)
    next_review: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    interval: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="vocabulary")
    
    # Indexes
    __table_args__ = (
        Index("ix_vocabulary_user_id", "user_id"),
        Index("ix_vocabulary_user_word", "user_id", "word_de", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Vocabulary(id={self.id}, word_de={self.word_de}, learned={self.learned})>"


class VoicePractice(Base):
    """Практики произношения с голосовыми сообщениями."""
    
    __tablename__ = "voice_practice"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Аудио данные
    audio_file_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Telegram file_id
    transcription: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Для повторных попыток одной фразы
    target_phrase: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Анализ произношения
    score: Mapped[float] = mapped_column(Integer, nullable=False)  # 1.0 - 10.0 * 10 для хранения
    feedback_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # Детали анализа
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("ix_voice_practice_user_id", "user_id"),
        Index("ix_voice_practice_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<VoicePractice(id={self.id}, user_id={self.user_id}, score={self.score/10})>"


class ChallengeSettings(Base):
    """Настройки челленджей пользователя."""
    
    __tablename__ = "challenge_settings"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    
    # Вкл/выкл
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Время напоминания (HH:MM)
    notification_time: Mapped[str] = mapped_column(String(5), default="09:00", nullable=False)
    
    # Сложность (A1/A2/B1)
    difficulty: Mapped[str] = mapped_column(String(2), default="A2", nullable=False)
    
    # Выбранные темы (JSON массив)
    topics: Mapped[list] = mapped_column(
        JSON, default=["daily_life", "work", "food"], nullable=False
    )
    
    # Выбранные форматы (JSON массив)
    formats: Mapped[list] = mapped_column(
        JSON, default=["text", "grammar"], nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="challenge_settings")
    
    def __repr__(self) -> str:
        return f"<ChallengeSettings(user_id={self.user_id}, enabled={self.enabled})>"


class UserChallenge(Base):
    """История челленджей пользователя."""
    
    __tablename__ = "user_challenges"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Дата челленджа (YYYY-MM-DD)
    challenge_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Тип челленджа: text/voice/grammar/vocabulary/roleplay/creative
    challenge_type: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Тема: daily_life/work/travel/food/sports/family
    topic: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Содержимое челленджа
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    grammar_focus: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    min_requirements: Mapped[str] = mapped_column(Text, nullable=False)
    example_start: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Статус выполнения
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Время выполнения
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="challenges")
    
    # Indexes
    __table_args__ = (
        Index("ix_user_challenges_user_id", "user_id"),
        Index("ix_user_challenges_date", "challenge_date"),
        Index("ix_user_challenges_user_date", "user_id", "challenge_date", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<UserChallenge(id={self.id}, user_id={self.user_id}, completed={self.completed})>"


class UserBadge(Base):
    """Бейджи пользователя."""
    
    __tablename__ = "user_badges"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # ID бейджа: 7_day_warrior, 30_day_legend, grammar_master, perfectionist, early_bird, night_owl
    badge_id: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Когда получен
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="badges")
    
    # Indexes
    __table_args__ = (
        Index("ix_user_badges_user_id", "user_id"),
        Index("ix_user_badges_user_badge", "user_id", "badge_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<UserBadge(id={self.id}, user_id={self.user_id}, badge_id={self.badge_id})>"


class GrammarExercise(Base):
    """История грамматических упражнений пользователя."""
    
    __tablename__ = "grammar_exercises"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Тема упражнения: articles, cases, perfekt, word_order, prepositions, adjectives
    topic: Mapped[str] = mapped_column(String(30), nullable=False)
    
    # Содержимое упражнения
    question: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(255), nullable=False)
    option_b: Mapped[str] = mapped_column(String(255), nullable=False)
    option_c: Mapped[str] = mapped_column(String(255), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(1), nullable=False)  # A, B или C
    rule_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Ответ пользователя
    user_answer: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Контекст из диалога
    context_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    answered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="grammar_exercises")
    
    # Indexes
    __table_args__ = (
        Index("ix_grammar_exercises_user_id", "user_id"),
        Index("ix_grammar_exercises_topic", "topic"),
        Index("ix_grammar_exercises_user_topic", "user_id", "topic"),
    )
    
    def __repr__(self) -> str:
        return f"<GrammarExercise(id={self.id}, user_id={self.user_id}, topic={self.topic}, is_correct={self.is_correct})>"


class StreakReward(Base):
    """Полученные награды за streak milestones."""
    
    __tablename__ = "streak_rewards"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Milestone
    milestone_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 3, 7, 14, 30, 50, 100
    badge_id: Mapped[str] = mapped_column(String(50), nullable=False)  # streak_3, streak_7, etc.
    
    # Награда
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    premium_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    freeze_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamp
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("ix_streak_rewards_user_id", "user_id"),
        Index("ix_streak_rewards_user_milestone", "user_id", "milestone_day", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<StreakReward(id={self.id}, user_id={self.user_id}, milestone={self.milestone_day})>"


class Friendship(Base):
    """Друзья для приватного leaderboard."""
    
    __tablename__ = "friendships"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    friend_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Статус: pending, accepted
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_friendships_user_id", "user_id"),
        Index("ix_friendships_friend_id", "friend_id"),
        Index("ix_friendships_pair", "user_id", "friend_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Friendship(user={self.user_id}, friend={self.friend_id}, status={self.status})>"


class Duel(Base):
    """Дуэли 1 на 1 на неделю."""
    
    __tablename__ = "duels"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Участники
    challenger_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    opponent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Период дуэли
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    
    # XP за период дуэли
    challenger_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opponent_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Статус: pending, active, completed, declined
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    winner_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_duels_challenger_id", "challenger_id"),
        Index("ix_duels_opponent_id", "opponent_id"),
        Index("ix_duels_status", "status"),
    )
    
    
    def __repr__(self) -> str:
        return f"<Duel(id={self.id}, challenger={self.challenger_id}, opponent={self.opponent_id}, status={self.status})>"


class PlacementTest(Base):
    """История прохождения тестов на определение уровня."""
    
    __tablename__ = "placement_tests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    
    # Результат
    level_result: Mapped[str] = mapped_column(String(10), nullable=False)  # A1, A2, B1, etc.
    
    # Статистика
    questions_total: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_total: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Детализация (JSON): {"A1": "9/10", "A2": "6/10", ...}
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("ix_placement_tests_user_id", "user_id"),
        Index("ix_placement_tests_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<PlacementTest(id={self.id}, user_id={self.user_id}, level={self.level_result})>"
