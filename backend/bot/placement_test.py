
import json
import logging
import os
import random
from typing import List, Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_session_context
from database.models import User, PlacementTest

logger = logging.getLogger(__name__)

router = Router(name="placement_test")

# --- DATA LOADING ---
QUESTIONS: List[Dict[str, Any]] = []

def load_questions():
    """Load questions from JSON file."""
    global QUESTIONS
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "data", "placement_questions.json")
        with open(file_path, "r", encoding="utf-8") as f:
            QUESTIONS = json.load(f)
        logger.info(f"Loaded {len(QUESTIONS)} placement questions.")
    except Exception as e:
        logger.error(f"Failed to load placement questions: {e}")
        QUESTIONS = []

# Load on module import (or improved to load on startup)
load_questions()

# --- STATES ---
class TestStates(StatesGroup):
    intro = State()
    question = State()

# --- LOGIC HELPERS ---
LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1']

def get_block_questions(level: str) -> List[Dict[str, Any]]:
    return [q for q in QUESTIONS if q['level'] == level]

# --- HANDLERS ---

@router.callback_query(F.data == "start_test_chat")
async def start_test_intro(callback: CallbackQuery, state: FSMContext) -> None:
    """Show intro screen for the test."""
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поехали! 🚀", callback_data="test_next_question")]
    ])
    
    intro_text = (
        "🇩🇪 <b>Тест на уровень немецкого</b>\n\n"
        "Я задам тебе несколько вопросов от A1 до C1.\n"
        "Тест адаптивный: если справляешься — идём дальше, если сложно — останавливаемся.\n\n"
        "⏱️ Время: ~5-10 минут\n"
        "🎯 Результат: Сразу после завершения"
    )
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(TestStates.intro)

@router.callback_query(F.data == "test_next_question", TestStates.intro)
async def start_first_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Initialize test state and show first question."""
    # Init state
    await state.set_data({
        "current_level_index": 0,  # Start at A1
        "block_question_index": 0, # 0-9 inside the block
        "level_score": 0,          # Correct answers in this block
        "total_questions": 0,
        "total_correct": 0,
        "level_results": {}        # {"A1": "8/10", ...}
    })
    
    await show_question(callback, state)
    await state.set_state(TestStates.question)

async def show_question(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    level_idx = data["current_level_index"]
    block_idx = data["block_question_index"]
    
    current_level = LEVELS[level_idx]
    questions_pool = get_block_questions(current_level)
    
    if block_idx >= len(questions_pool):
        # Should not happen if logic is correct, but safety net
        await finish_test(callback, state)
        return

    question = questions_pool[block_idx]
    
    # Store current correct index in state so we can check answer
    await state.update_data(current_correct_index=question['correct_index'])
    
    # Build keyboard
    buttons = []
    for i, option in enumerate(question['options']):
        # Callback data: test_ans:{option_index}
        buttons.append([InlineKeyboardButton(text=option, callback_data=f"test_ans:{i}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    text = (
        f"📊 <b>Уровень {current_level}</b> (Вопрос {block_idx + 1}/10)\n\n"
        f"<b>{question['question']}</b>"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("test_ans:"), TestStates.question)
async def process_answer(callback: CallbackQuery, state: FSMContext):
    """Process user answer."""
    ans_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    correct_idx = data["current_correct_index"]
    is_correct = (ans_idx == correct_idx)
    
    # Update stats
    new_level_score = data["level_score"] + (1 if is_correct else 0)
    new_total_correct = data["total_correct"] + (1 if is_correct else 0) # Global counter
    new_block_idx = data["block_question_index"] + 1
    new_total_questions = data["total_questions"] + 1
    
    await state.update_data(
        level_score=new_level_score,
        block_question_index=new_block_idx,
        total_questions=new_total_questions,
        total_correct=new_total_correct
    )
    
    # Check if block is finished (10 questions or end of pool)
    current_level = LEVELS[data["current_level_index"]]
    questions_pool = get_block_questions(current_level)
    
    if new_block_idx >= 10 or new_block_idx >= len(questions_pool):
        await evaluate_block(callback, state)
    else:
        # Next question
        await show_question(callback, state)

async def evaluate_block(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data["level_score"]
    level_idx = data["current_level_index"]
    current_level = LEVELS[level_idx]
    
    # Record result
    results = data["level_results"]
    results[current_level] = f"{score}/10"
    await state.update_data(level_results=results)
    
    # Logic:
    # >= 7 -> Next Level
    # 5-6 -> Stay at this level (Finished)
    # < 5 -> Previous level is your level (or A1) (Finished)
    
    stop_reason = ""
    
    if score >= 7:
        if level_idx < len(LEVELS) - 1:
            # Promote
            await state.update_data(
                current_level_index=level_idx + 1,
                block_question_index=0,
                level_score=0
            )
            await callback.answer(f"🎉 {current_level} пройден! ({score}/10). Идём дальше!", show_alert=False)
            await show_question(callback, state)
            return
        else:
            # Finished C1 perfectly
            final_level = "C1"
            stop_reason = "Ты прошел все уровни до конца! 🏆"
    elif score >= 5:
        final_level = current_level
        stop_reason = f"Ты неплохо знаешь {current_level}, но для перехода на следующий уровень нужно чуть больше практики. 📚"
    else:
        # Failed this level
        final_level = LEVELS[level_idx - 1] if level_idx > 0 else "A1"
        stop_reason = f"Уровень {current_level} пока сложноват. Начнём с более комфортного {final_level}. 💪"
        
    await finish_test(callback, state, final_level, stop_reason)

async def finish_test(callback: CallbackQuery, state: FSMContext, final_level: str = "A1", stop_reason: str = ""):
    data = await state.get_data()
    
    # Save to DB
    user_id = callback.from_user.id
    
    async with get_session_context() as session:
        # 1. Create PlacementTest record
        test_record = PlacementTest(
            user_id=user_id,
            level_result=final_level,
            questions_total=data["total_questions"],
            correct_total=data["total_correct"],
            details_json=data["level_results"]
        )
        session.add(test_record)
        
        # 2. Update User level
        user = await session.get(User, user_id)
        if user:
            user.level = final_level
            
        await session.commit()
        
    # Show results
    await state.clear()
    
    text = (
        f"🎉 <b>Тест завершён!</b>\n\n"
        f"Твой уровень: <b>{final_level}</b>\n\n"
        f"✅ Всего правильных: {data['total_correct']}/{data['total_questions']}\n\n"
    )
    
    if stop_reason:
        text += f"<i>{stop_reason}</i>\n\n"
        
    text += f"Я обновил твой профиль. Теперь мы будем учиться на уровне <b>{final_level}</b>. 🎓\n\n"
    text += "Давай начнем практику! Расскажи мне немного о себе на немецком (или на русском). Как тебя зовут и чем ты занимаешься? 👇"
    
    # No keyboard - encourages typing
    await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
    
    # Clear Gemini context to ensure fresh start with new level prompt instructions (handled implicitly by next message)
    from .gemini_client import get_gemini_client
    try:
        get_gemini_client().clear_chat(user_id)
    except:
        pass
