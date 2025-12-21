"""
Обработчики сообщений Telegram бота.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.db import get_session_context
from database.models import User, Message as DBMessage, UserContext, Vocabulary, GrammarExercise
from .gemini_client import get_gemini_client, ChatMessage
from .grammar_exercises import (
    should_trigger_exercise, is_user_asking_question, choose_topic,
    save_exercise_answer, GRAMMAR_TOPICS, XP_PER_CORRECT_ANSWER
)
from .streak_service import (
    increment_daily_messages, check_and_update_streak,
    format_milestone_message, MIN_MESSAGES_PER_DAY
)

logger = logging.getLogger(__name__)

router = Router(name="main")

# URL Mini App (из конфигурации)
MINI_APP_URL = settings.api_base_url.replace("/api", "")


# ============ КЛАВИАТУРЫ ============

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура с кнопками."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Моя статистика",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}/stats")
            ),
            InlineKeyboardButton(
                text="⚙️ Настройки",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}/settings")
            ),
        ],
    ])


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для статистики."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📈 Подробная статистика →",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}/stats")
            ),
        ],
    ])


def get_level_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A1 🌱", callback_data="level:A1"),
            InlineKeyboardButton(text="A2 🌿", callback_data="level:A2"),
        ],
        [
            InlineKeyboardButton(text="B1 🌳", callback_data="level:B1"),
            InlineKeyboardButton(text="B2 🌲", callback_data="level:B2"),
        ],
        [
            InlineKeyboardButton(text="C1 🏔️", callback_data="level:C1"),
            InlineKeyboardButton(text="C2 ⭐", callback_data="level:C2"),
        ],
    ])


def get_text_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для интерактивного текста.
    Открывает Mini App с текстом сообщения.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📖 Текст",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}/text/{message_id}")
            )
        ]
    ])

# ============ КОМАНДЫ ============

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Обработка команды /start.
    Регистрация пользователя и приветствие.
    """
    try:
        user = message.from_user
        if not user:
            return
        
        async with get_session_context() as session:
            # Проверяем существующего пользователя
            db_user = await session.get(User, user.id)
            
            if not db_user:
                # Создаём нового пользователя
                db_user = User(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    level="A2",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(db_user)
                await session.commit()
                logger.info("New user registered: %d (%s)", user.id, user.first_name)
            
            # Приветственное сообщение
            welcome_text = """Привет! Я Макс, твой языковой друг 🇩🇪

Я помогу тебе выучить немецкий через простое общение.

Просто пиши мне на немецком (или на русском, если не знаешь как сказать), а я буду:
✅ Исправлять ошибки
✅ Учить новым словам  
✅ Запоминать твою историю

<b>С чего начнем?</b>
Рекомендую пройти быстрый тест, чтобы я подобрал программу под твой уровнь! 👇"""

            # Клавиатура с кнопкой теста
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Пройти тест (в чате)",
                        callback_data="start_test_chat"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Моя статистика",
                        web_app=WebAppInfo(url=f"{MINI_APP_URL}/stats")
                    ),
                    InlineKeyboardButton(
                        text="⚙️ Настройки",
                        web_app=WebAppInfo(url=f"{MINI_APP_URL}/settings")
                    ),
                ],
            ])

            await message.answer(
                welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        import traceback
        await message.answer(f"⚠️ <b>Fatal Error:</b> {str(e)}\n<pre>{traceback.format_exc()}</pre>", parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Справка по командам."""
    help_text = """🤖 *Как со мной общаться:*

• Пиши на немецком — я исправлю ошибки
• Пиши на русском — я помогу перевести
• Отправляй голосовые — оценю произношение 🎤

*Команды:*
/start — начать заново
/stats — твоя статистика
/level — изменить уровень
/settings — настройки бота
/clear — очистить историю чата

*Советы:*
💡 Пиши каждый день для streak
💡 Не бойся ошибаться — это нормально!
💡 Используй новые слова в разговоре"""

    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Показать краткую статистику."""
    user = message.from_user
    if not user:
        return
    
    async with get_session_context() as session:
        db_user = await session.get(User, user.id)
        
        if not db_user:
            await message.answer("Сначала напиши /start 😊")
            return
        
        # Подсчёт слов в словаре
        vocab_count = await session.scalar(
            select(func.count(Vocabulary.id))
            .where(Vocabulary.user_id == user.id)
        )
        
        stats_text = f"""📊 *Твоя статистика:*

🔥 Стрик: *{db_user.streak_days}* дней подряд
💬 Всего сообщений: *{db_user.total_messages}*
📚 Новых слов: *{vocab_count or 0}*
📈 Уровень: *{db_user.level}*"""

        await message.answer(
            stats_text,
            reply_markup=get_stats_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )


@router.message(Command("level"))
async def cmd_level(message: Message) -> None:
    """Выбор уровня владения языком."""
    await message.answer(
        "Выбери свой уровень немецкого:",
        reply_markup=get_level_keyboard()
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """Открыть настройки."""
    user = message.from_user
    if not user:
        return
    
    async with get_session_context() as session:
        db_user = await session.get(User, user.id)
        
        if not db_user:
            await message.answer("Сначала напиши /start")
            return
        
        reminder_status = "✅ Вкл" if db_user.reminder_enabled else "❌ Выкл"
        personality_names = {
            "friendly": "😊 Дружелюбный",
            "strict": "📚 Строгий",
            "romantic": "💕 Романтичный"
        }
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Напоминания: {reminder_status}",
                callback_data="toggle:reminder"
            )],
            [InlineKeyboardButton(
                text=f"Стиль: {personality_names.get(db_user.bot_personality, db_user.bot_personality)}",
                callback_data="personality:menu"
            )],
            [InlineKeyboardButton(
                text="⚙️ Все настройки →",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}/settings")
            )],
        ])
        
        await message.answer(
            f"⚙️ *Настройки*\n\nУровень: *{db_user.level}*",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    """Очистка истории чата с Gemini."""
    user = message.from_user
    if not user:
        return
    
    # Очищаем кеш чата в Gemini
    try:
        gemini = get_gemini_client()
        gemini.clear_chat(user.id)
    except RuntimeError:
        pass  # Клиент ещё не инициализирован
    
    await message.answer(
            "🗑️ История чата очищена!\n\n"
        "Начнём разговор заново? Напиши что-нибудь! 😊"
    )




@router.message(Command("freeze"))
async def cmd_freeze(message: Message) -> None:
    """Использовать streak freeze."""
    from .streak_service import use_streak_freeze
    
    if not message.from_user:
        return
    
    async with get_session_context() as session:
        user = await session.get(User, message.from_user.id)
        
        if not user:
            await message.answer("Сначала напиши /start чтобы начать!")
            return
        
        result = await use_streak_freeze(session, user)
        await session.commit()
        
        if result["success"]:
            await message.answer(
                f"❄️ *Streak Freeze активирован!*\n\n"
                f"Твой {user.streak_days}-дневный streak сохранится даже если пропустишь сегодня.\n\n"
                f"Осталось заморозок: {result['remaining']}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.answer(
                f"❌ {result['message']}\n\n"
                f"Доступные заморозки: {result['remaining']}"
            )


@router.message(Command("streak"))
async def cmd_streak(message: Message) -> None:
    """Показать информацию о streak."""
    from .streak_service import get_streak_info, MIN_MESSAGES_PER_DAY
    
    if not message.from_user:
        return
    
    async with get_session_context() as session:
        user = await session.get(User, message.from_user.id)
        
        if not user:
            await message.answer("Сначала напиши /start чтобы начать!")
            return
        
        info = await get_streak_info(session, user)
        
        # Формируем прогресс-бар
        progress = info["daily_progress"]
        goal = info["daily_goal"]
        filled = min(int((progress / goal) * 10), 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        # Статус дня
        if info["daily_goal_reached"]:
            status = "✅ Цель достигнута!"
        else:
            remaining = goal - progress
            status = f"⏳ Осталось: {remaining} сообщений"
        
        text = (
            f"🔥 *Твой Streak: {info['streak_days']} дней*\n\n"
            f"📊 Прогресс сегодня:\n"
            f"`[{bar}]` {progress}/{goal}\n"
            f"{status}\n\n"
            f"🏆 Лучший результат: {info['best_streak']} дней\n"
            f"⭐ XP за неделю: {info['xp_week']}\n"
            f"❄️ Заморозок: {info['freeze_available']}\n"
        )
        
        if info["next_milestone"]:
            days_left = info["next_milestone"] - info["streak_days"]
            text += f"\n🎯 До награды \"{info['next_milestone_reward']['name']}\": {days_left} дней"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 Подробнее",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}/streak")
            )]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# ============ CALLBACK HANDLERS ============

@router.callback_query(F.data.startswith("level:"))
async def callback_level(callback: CallbackQuery) -> None:
    """Обработка выбора уровня."""
    if not callback.data or not callback.from_user:
        return
    
    level = callback.data.split(":")[1]
    
    async with get_session_context() as session:
        db_user = await session.get(User, callback.from_user.id)
        if db_user:
            db_user.level = level
            db_user.updated_at = datetime.now(timezone.utc)
            await session.commit()
    
    # Очищаем кеш чата (пересоздадим с новым промптом)
    try:
        gemini = get_gemini_client()
        gemini.clear_chat(callback.from_user.id)
    except RuntimeError:
        pass
    
    await callback.answer(f"Уровень изменён на {level}!")
    await callback.message.edit_text(
        f"✅ Отлично! Теперь твой уровень: *{level}*\n\n"
        "Я буду адаптировать сложность под тебя.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "toggle:reminder")
async def callback_toggle_reminder(callback: CallbackQuery) -> None:
    """Переключение напоминаний."""
    if not callback.from_user:
        return
    
    async with get_session_context() as session:
        db_user = await session.get(User, callback.from_user.id)
        if db_user:
            db_user.reminder_enabled = not db_user.reminder_enabled
            db_user.updated_at = datetime.now(timezone.utc)
            await session.commit()
            
            status = "включены ✅" if db_user.reminder_enabled else "выключены ❌"
            await callback.answer(f"Напоминания {status}")


@router.callback_query(F.data == "personality:menu")
async def callback_personality_menu(callback: CallbackQuery) -> None:
    """Меню выбора личности бота."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😊 Дружелюбный", callback_data="personality:friendly")],
        [InlineKeyboardButton(text="📚 Строгий учитель", callback_data="personality:strict")],
        [InlineKeyboardButton(text="💕 Романтичный", callback_data="personality:romantic")],
        [InlineKeyboardButton(text="← Назад", callback_data="settings:back")],
    ])
    
    await callback.message.edit_text(
        "Выбери стиль общения бота:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("personality:"))
async def callback_personality(callback: CallbackQuery) -> None:
    """Установка личности бота."""
    if not callback.data or not callback.from_user:
        return
    
    personality = callback.data.split(":")[1]
    if personality == "menu":
        return
    
    async with get_session_context() as session:
        db_user = await session.get(User, callback.from_user.id)
        if db_user:
            db_user.bot_personality = personality
            db_user.updated_at = datetime.now(timezone.utc)
            await session.commit()
    
    # Очищаем кеш чата
    try:
        gemini = get_gemini_client()
        gemini.clear_chat(callback.from_user.id)
    except RuntimeError:
        pass
    
    names = {"friendly": "Дружелюбный 😊", "strict": "Строгий 📚", "romantic": "Романтичный 💕"}
    await callback.answer(f"Стиль: {names.get(personality, personality)}")
    await callback.message.edit_text(
        f"✅ Стиль общения: *{names.get(personality, personality)}*",
        parse_mode=ParseMode.MARKDOWN
    )


# ============ PRONUNCIATION CALLBACKS ============



# ============ GRAMMAR EXERCISE CALLBACKS ============

@router.callback_query(F.data.startswith("grammar:"))
async def callback_grammar_answer(callback: CallbackQuery) -> None:
    """Обработка ответа на грамматическое упражнение."""
    if not callback.from_user or not callback.data:
        return
    
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Ошибка формата данных", show_alert=True)
            return
        
        exercise_id = int(parts[1])
        user_answer = parts[2].upper()
        
        if user_answer not in ["A", "B", "C"]:
            await callback.answer("Неверный ответ", show_alert=True)
            return
        
        async with get_session_context() as session:
            # Получаем пользователя и упражнение
            user = await session.get(User, callback.from_user.id)
            exercise = await session.get(GrammarExercise, exercise_id)
            
            if not user or not exercise:
                await callback.answer("Упражнение не найдено", show_alert=True)
                return
            
            if exercise.user_id != callback.from_user.id:
                await callback.answer("Это не твоё упражнение", show_alert=True)
                return
            
            if exercise.user_answer is not None:
                await callback.answer("Ты уже ответил на это упражнение", show_alert=True)
                return
            
            # Сохраняем ответ и обновляем статистику
            result = await save_exercise_answer(session, exercise_id, user_answer, user)
            
            # Определяем какой вариант был правильным
            correct_text = {
                "A": exercise.option_a,
                "B": exercise.option_b,
                "C": exercise.option_c,
            }[result["correct_answer"]]
            
            # Формируем ответ
            if result["is_correct"]:
                response_text = (
                    f"✅ *Richtig!* {result['correct_answer']}) {correct_text}\n\n"
                    f"📚 *Regel:* {result['rule']}\n\n"
                    f"🎉 +{XP_PER_CORRECT_ANSWER} XP!"
                )
            else:
                response_text = (
                    f"❌ *Leider falsch!* Die richtige Antwort: {result['correct_answer']}) {correct_text}\n\n"
                    f"📚 *Regel:* {result['rule']}"
                )
            
            # Добавляем follow-up если есть
            if result.get("follow_up"):
                response_text += f"\n\n{result['follow_up']}"
            
            # Обновляем сообщение (убираем кнопки и показываем результат)
            await callback.message.edit_text(
                response_text,
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Отправляем toast
            if result["is_correct"]:
                await callback.answer(f"Richtig! +{XP_PER_CORRECT_ANSWER} XP 🎉")
            else:
                await callback.answer("Schade! Beim nächsten Mal klappt's! 💪")
            
            logger.info(
                "Grammar exercise %d answered by user %d: answer=%s, correct=%s, xp=%d",
                exercise_id, callback.from_user.id, user_answer, 
                result["is_correct"], result["xp_earned"]
            )
            
    except Exception as e:
        logger.error("Error processing grammar answer: %s", str(e), exc_info=True)
        await callback.answer("Произошла ошибка 😔", show_alert=True)




# ============ ОБРАБОТКА СООБЩЕНИЙ ============

async def handle_pronunciation_practice(
    message: Message,
    session: AsyncSession,
    transcription: str,
    file_id: str,
    db_user: User
) -> None:
    """
    Обработка голосового в режиме практики произношения.
    """
    from database.models import VoicePractice
    
    try:
        # Проверяем retry mode
        is_retry = db_user.user_id in retry_target
        retry_info = retry_target.get(db_user.user_id, {})
        
        # Анализ произношения через Gemini
        gemini = get_gemini_client()
        feedback = await gemini.analyze_pronunciation(transcription)
        
        # Сохраняем практику в БД
        practice = VoicePractice(
            user_id=db_user.user_id,
            audio_file_id=file_id,
            transcription=transcription,
            target_phrase=retry_info.get("phrase"),
            attempt_number=retry_info.get("attempt", 1),
            score=int(feedback["score"] * 10),  # Храним как 10x для int
            feedback_json=feedback
        )
        session.add(practice)
        await session.commit()
        await session.refresh(practice)
        
        # Очищаем retry mode если был
        if is_retry:
            del retry_target[db_user.user_id]
        
        # Форматируем ответ
        score = feedback["score"]
        stars = "⭐" * int(score)
        
        good_text = "\n".join(f"• {item}" for item in feedback["good"])
        improve_text = "\n".join(f"• {item}" for item in feedback["improve"])
        
        # Прогресс для retry
        progress_text = ""
        if is_retry and "previous_score" in retry_info:
            prev_score = retry_info["previous_score"]
            diff = score - prev_score
            if diff > 0:
                progress_text = f"📈 *Прогресс:* {prev_score:.1f} → {score:.1f} (+{diff:.1f})!\n\n"
            elif diff < 0:
                progress_text = f"📉 *Попытка {retry_info['attempt']}:* {prev_score:.1f} → {score:.1f} ({diff:.1f})\n\n"
            else:
                progress_text = f"➡️ *Попытка {retry_info['attempt']}:* Та же оценка {score:.1f}/10\n\n"
        
        response = f"""{progress_text}🎙️ *Я услышал:*
_{transcription}_

📊 *Оценка произношения:* {score}/10 {stars}

✅ *Отлично звучит:*
{good_text}

⚠️ *Можно улучшить:*
{improve_text}

💡 *Совет:* {feedback["tip"]}

_Отправь ещё одно голосовое для новой оценки!_
_Чтобы выйти из режима практики: /stop_"""
        
        # Inline кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔊 Послушать правильное",
                    callback_data=f"tts:{practice.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Попробовать ещё раз",
                    callback_data=f"retry:{practice.id}"
                ),
                InlineKeyboardButton(
                    text="✅ Понятно",
                    callback_data=f"done:{practice.id}"
                )
            ]
        ])
        
        await message.reply(response, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info("Pronunciation practice completed for user %d: score=%.1f", db_user.user_id, score)
        
    except Exception as e:
        logger.error("Error in pronunciation practice for user %d: %s", db_user.user_id, str(e), exc_info=True)
        await message.reply(
            "Произошла ошибка при анализе 😔\n"
            "Попробуй ещё раз или используй /stop чтобы выйти из режима практики."
        )


@router.message(F.voice)
async def handle_voice_message(message: Message, bot: Bot) -> None:
    """
    Обработчик голосовых сообщений.
    Транскрибирует голос через Gemini и обрабатывает как текст.
    """
    user = message.from_user
    
    if not user or not message.voice:
        return
    
    logger.info("Received voice message from user %d (duration: %ds)", user.id, message.voice.duration or 0)
    
    async with get_session_context() as session:
        # Получаем или создаём пользователя
        db_user = await session.get(User, user.id)
        
        if not db_user:
            db_user = User(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                level="A2",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(db_user)
            await session.flush()
        
        try:
            # Скачиваем голосовое сообщение
            voice_file = await bot.download(message.voice.file_id)
            
            if not voice_file:
                await message.reply("Не удалось скачать голосовое сообщение 😔")
                return
            
            # Читаем байты
            voice_bytes = voice_file.read()
            
            # Транскрибируем через Gemini
            gemini = get_gemini_client()
            transcription = await gemini.transcribe_audio(voice_bytes)
            
            if transcription == "[Не удалось распознать аудио]":
                await message.reply("Не удалось распознать голос 😔\nПопробуй ещё раз или отправь текстом!")
                return
            
            logger.info("Voice transcribed: '%s'", transcription[:50])
            
            # ПРОВЕРКА РЕЖИМА ПРАКТИКИ (из БД)
            if db_user.practice_mode_enabled:
                # ===== РЕЖИМ ПРАКТИКИ ПРОИЗНОШЕНИЯ =====
                await handle_pronunciation_practice(
                    message, session, transcription, message.voice.file_id, db_user
                )
                return
            
            # ===== ОБЫЧНЫЙ РЕЖИМ: РАЗГОВОР =====
            # Сохраняем пользовательское сообщение (транскрипцию)
            user_msg = DBMessage(
                user_id=user.id,
                role="user",
                content=transcription,
                tokens_used=len(transcription) // 4,
                created_at=datetime.now(timezone.utc),
            )
            session.add(user_msg)
            
            # Загружаем историю для контекста
            history_query = await session.execute(
                select(DBMessage)
                .where(DBMessage.user_id == user.id)
                .order_by(DBMessage.created_at.desc())
                .limit(20)
            )
            history = list(reversed(history_query.scalars().all()))
            
            # Конвертация в формат ChatMessage
            chat_history = []
            for msg in history[:-1]:  # Исключаем только что добавленное сообщение
                chat_history.append(ChatMessage(role=msg.role, content=msg.content))
            
            # Контекст пользователя
            context_result = await session.execute(
                select(UserContext).where(UserContext.user_id == user.id)
            )
            user_context = context_result.scalar_one_or_none()
            context_data = user_context.context_data if user_context else {}
            
            # Получаем или создаём чат
            if not gemini.has_active_chat(user.id):
                await gemini.create_chat(
                    user_id=user.id,
                    user_level=db_user.level,
                    user_goal=db_user.goal,
                    personality=db_user.bot_personality,
                    user_context=context_data,
                    history=chat_history,
                )
            
            chat = await gemini.get_or_create_chat(
                user_id=user.id,
                user_level=db_user.level,
                user_goal=db_user.goal,
                personality=db_user.bot_personality,
                user_context=context_data,
            )
            
            # Отправляем в Gemini
            response = await chat.send_message_async(transcription)
            response_text = response.text
            response_tokens = gemini._count_tokens(transcription, response_text)
            
            # Сохраняем ответ бота
            assistant_msg = DBMessage(
                user_id=user.id,
                role="assistant",
                content=response_text,
                tokens_used=response_tokens,
                created_at=datetime.now(timezone.utc),
            )
            session.add(assistant_msg)
            
            # Flush чтобы получить ID для кнопки
            await session.flush()
            await session.refresh(assistant_msg)
            message_id = assistant_msg.id
            
            # Обновляем streak
            _update_streak(db_user, datetime.now(timezone.utc))
            
            db_user.total_messages += 1
            db_user.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            # Отправляем ответ с транскрипцией и кнопкой
            await message.reply(
                f"🎤 *Ты сказал:*\n_{transcription}_\n\n{response_text}",
                reply_markup=get_text_keyboard(message_id),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info("Voice message processed for user %d (msg_id=%d)", user.id, message_id)
            
        except Exception as e:
            logger.error("Error handling voice for user %d: %s", user.id, str(e), exc_info=True)
            await message.reply("Произошла ошибка при обработке сообщения 😔")


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """
    Основной обработчик текстовых сообщений.
    Отправляет в Gemini и сохраняет историю.
    """
    user = message.from_user
    text = message.text
    
    if not user or not text:
        return
    
    # Пропускаем команды (на всякий случай)
    if text.startswith("/"):
        return
    
    async with get_session_context() as session:
        # Получаем или создаём пользователя
        db_user = await session.get(User, user.id)
        
        if not db_user:
            db_user = User(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                level="A2",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(db_user)
            await session.flush()
        
        
        # Начисляем XP за сообщение (активность)
        XP_PER_MESSAGE = 5
        db_user.total_xp += XP_PER_MESSAGE
        
        # Обновляем streak
        from .streak_service import update_streak
        await update_streak(session, db_user)
        
        # Загружаем контекст пользователя
        user_context_db = await session.get(UserContext, user.id)
        user_context = user_context_db.context_data if user_context_db else None
        
        # Загружаем последние сообщения для истории
        history_result = await session.execute(
            select(DBMessage)
            .where(DBMessage.user_id == user.id)
            .order_by(DBMessage.created_at.desc())
            .limit(20)
        )
        history_messages = list(reversed(history_result.scalars().all()))
        
        history = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in history_messages
        ]
        
        # Показываем "печатает..."
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        try:
            # Отправляем в Gemini
            gemini = get_gemini_client()
            response = await gemini.send_message(
                user_id=user.id,
                message=text,
                user_level=db_user.level,
                user_goal=db_user.goal,
                personality=db_user.bot_personality,
                user_context=user_context,
                history=history,
            )
            
            now = datetime.now(timezone.utc)
            
            # Сохраняем сообщение пользователя
            user_msg = DBMessage(
                user_id=user.id,
                role="user",
                content=text,
                created_at=now,
            )
            session.add(user_msg)
            
            # Сохраняем ответ бота
            assistant_msg = DBMessage(
                user_id=user.id,
                role="assistant",
                content=response.text,
                tokens_used=response.tokens_used,
                created_at=now,
            )
            session.add(assistant_msg)
            
            # Flush чтобы получить ID сообщения для интерактивной кнопки
            await session.flush()
            await session.refresh(assistant_msg)
            message_id = assistant_msg.id
            
            # Обновляем daily messages и статистику
            db_user.total_messages += 1
            db_user.last_message_date = now
            db_user.updated_at = now
            
            # Обновляем streak через новый сервис
            await increment_daily_messages(session, db_user)
            streak_result = await check_and_update_streak(session, db_user)
            
            await session.commit()
            
            # Отправляем уведомление о milestone если достигнут
            if streak_result.get("milestone_reached"):
                milestone_msg = format_milestone_message(streak_result["reward"])
                await message.answer(milestone_msg, parse_mode=ParseMode.MARKDOWN)
            
            # Отправляем ответ с кнопкой для интерактивного текста
            try:
                await message.answer(
                    response.text,
                    reply_markup=get_text_keyboard(message_id),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as markdown_error:
                # Fallback: отправляем без форматирования если markdown невалидный
                logger.warning("Markdown parse error, sending without formatting: %s", str(markdown_error))
                await message.answer(
                    response.text,
                    reply_markup=get_text_keyboard(message_id)
                )
            
            logger.info(
                "Message processed for user %d: %d chars → %d chars (msg_id=%d)",
                user.id, len(text), len(response.text), message_id
            )
            
            # ===== ПРОВЕРКА ТРИГГЕРА ГРАММАТИЧЕСКОГО УПРАЖНЕНИЯ =====
            # Увеличиваем счётчик сообщений
            db_user.grammar_message_counter += 1
            
            # Проверяем нужно ли показать упражнение
            is_question = is_user_asking_question(text)
            if should_trigger_exercise(db_user, is_user_question=is_question):
                try:
                    # Выбираем тему
                    topic = await choose_topic(session, user.id, text, is_premium=False)
                    
                    # Генерируем упражнение
                    exercise_data = await gemini.generate_grammar_exercise(
                        context_phrase=text,
                        topic=topic,
                        user_level=db_user.level,
                    )
                    
                    # Сохраняем упражнение в БД
                    exercise = GrammarExercise(
                        user_id=user.id,
                        topic=exercise_data["topic"],
                        question=exercise_data["question"],
                        option_a=exercise_data["option_a"],
                        option_b=exercise_data["option_b"],
                        option_c=exercise_data["option_c"],
                        correct_answer=exercise_data["correct"],
                        rule_explanation=exercise_data["rule"],
                        context_phrase=text,
                        follow_up_message=exercise_data.get("follow_up"),
                    )
                    session.add(exercise)
                    await session.flush()
                    await session.refresh(exercise)
                    
                    # Обновляем время последнего упражнения и сбрасываем счётчик
                    db_user.last_grammar_exercise = datetime.now(timezone.utc)
                    db_user.grammar_message_counter = 0
                    await session.commit()
                    
                    # Формируем сообщение с упражнением
                    exercise_text = (
                        f"📝 *Übrigens, schnelle Frage!*\n\n"
                        f"{exercise_data['question']}\n\n"
                        f"A) {exercise_data['option_a']}\n"
                        f"B) {exercise_data['option_b']}\n"
                        f"C) {exercise_data['option_c']}"
                    )
                    
                    # Кнопки ответов
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="A",
                                callback_data=f"grammar:{exercise.id}:A"
                            ),
                            InlineKeyboardButton(
                                text="B",
                                callback_data=f"grammar:{exercise.id}:B"
                            ),
                            InlineKeyboardButton(
                                text="C",
                                callback_data=f"grammar:{exercise.id}:C"
                            ),
                        ]
                    ])
                    
                    await message.answer(
                        exercise_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    logger.info(
                        "Grammar exercise sent to user %d: topic=%s, id=%d",
                        user.id, topic, exercise.id
                    )
                    
                except Exception as ex:
                    logger.error("Error generating grammar exercise for user %d: %s", user.id, str(ex))
                    # Не прерываем основной флоу если не удалось сгенерировать упражнение
            else:
                await session.commit()
            
        except Exception as e:
            logger.error("Error processing message for user %d: %s", user.id, str(e))
            
            await message.answer(
                "😔 Упс, что-то пошло не так. Попробуй ещё раз!\n\n"
                "Если ошибка повторяется, напиши /clear"
            )


@router.message(F.voice)
async def handle_voice_message(message: Message) -> None:
    """Обработка голосовых сообщений."""
    await message.answer(
        "🎤 Голосовые сообщения скоро будут работать!\n\n"
        "Я смогу слушать твоё произношение и давать обратную связь. "
        "А пока — пиши текстом! 📝"
    )


@router.message(F.photo | F.document | F.sticker)
async def handle_other_content(message: Message) -> None:
    """Обработка других типов контента."""
    await message.answer(
        "Пока я понимаю только текст и голосовые сообщения 😊\n\n"
        "Напиши мне что-нибудь на немецком!"
    )


# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def _update_streak(user: User, now: datetime) -> None:
    """
    Обновление streak пользователя.
    
    Логика:
    - last_message_date = сегодня → ничего не меняем
    - last_message_date = вчера → streak += 1
    - last_message_date > 1 дня назад → streak = 1
    - last_message_date = None → streak = 1
    """
    today = now.date()
    
    if user.last_message_date is None:
        # Первое сообщение
        user.streak_days = 1
        return
    
    last_date = user.last_message_date.date()
    days_diff = (today - last_date).days
    
    if days_diff == 0:
        # Тот же день — streak не меняется
        pass
    elif days_diff == 1:
        # Вчера — увеличиваем streak
        user.streak_days += 1
    else:
        # Пропустили больше 1 дня — сбрасываем
        user.streak_days = 1
