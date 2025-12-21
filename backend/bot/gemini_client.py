"""
Клиент для работы с Google Gemini API.
Обеспечивает интеграцию с AI для изучения немецкого языка.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Сообщение в чате."""
    role: str  # "user" или "model"
    content: str


@dataclass
class ChatResponse:
    """Ответ от Gemini."""
    text: str
    tokens_used: int
    finish_reason: Optional[str] = None


class GeminiClient:
    """
    Клиент для работы с Google Gemini API.
    
    Пример использования:
        client = GeminiClient(api_key="your_api_key")
        response = await client.send_message(
            user_id=123456,
            message="Привет!",
            user_level="A2",
            user_goal="Разговорный немецкий",
            personality="friendly"
        )
        print(response.text)
    """
    
    MODEL_NAME = "gemini-2.5-flash-lite"
    
    def __init__(self, api_key: str) -> None:
        """
        Инициализация клиента Gemini.
        
        Args:
            api_key: API ключ Google AI Studio
        """
        genai.configure(api_key=api_key)
        
        # Кеш активных чатов: user_id → ChatSession
        self._chats: Dict[int, Any] = {}
        
        # Кеш истории для восстановления контекста
        self._chat_histories: Dict[int, list[ChatMessage]] = {}
        
        # Конфигурация генерации
        self._generation_config = genai.GenerationConfig(
            temperature=0.9,
            top_p=0.95,
            top_k=40,
            max_output_tokens=1024,
        )
        
        # Настройки безопасности (более мягкие для образовательного контента)
        self._safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]
        
        logger.info("GeminiClient initialized with model: %s", self.MODEL_NAME)
    
    def _build_system_prompt(
        self,
        user_level: str = "A2",
        user_goal: Optional[str] = None,
        personality: str = "friendly",
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Создание системного промпта для бота.
        
        Args:
            user_level: Уровень владения языком (A1/A2/B1/B2/C1/C2)
            user_goal: Цель изучения языка
            personality: Тип личности бота (friendly/strict/romantic)
            user_context: Дополнительный контекст пользователя
        
        Returns:
            Системный промпт для Gemini
        """
        goal_text = user_goal or "Свободное общение на немецком"
        
        personality_desc = "Ты дружелюбный и поддерживающий"
        
        # Контекст пользователя
        context_info = ""
        if user_context:
            context_parts = []
            if user_context.get("name"):
                context_parts.append(f"Имя: {user_context['name']}")
            if user_context.get("city"):
                context_parts.append(f"Город: {user_context['city']}")
            if user_context.get("job"):
                context_parts.append(f"Работа: {user_context['job']}")
            if user_context.get("interests"):
                context_parts.append(f"Интересы: {', '.join(user_context['interests'])}")
            if context_parts:
                context_info = f"\n\nИЗВЕСТНО О ПОЛЬЗОВАТЕЛЕ:\n" + "\n".join(context_parts)
        
        return f"""Ты — Макс, виртуальный друг из Германии. {personality_desc}. 
Помогаешь русскоязычному практиковать немецкий в естественной беседе.

ГЛАВНОЕ ПРАВИЛО - ЕСТЕСТВЕННОСТЬ:
Общайся как живой человек в переписке, не как учитель и НЕ как интервьюер!

ЯЗЫК И СТИЛЬ:
- 🇩🇪 Немецкий — основной язык общения
- 🇷🇺 Русский — ВТОРОСТЕПЕННЫЙ, используй его ГИБКО:
  * Если пользователь совсем не понимает — объясни на русском
  * Если тема сложная — используй русский для пояснений
  * Если пользователь пишет на русском — ответь на содержание, НО мягко предложи перейти на немецкий (например: "Auf Deutsch, bitte? 😉" или "Как это будет по-немецки?").
  * Если пользователь "застрял" в русском, дай ему простие фразы-шаблоны на немецком для ответа.
  * САМОСТОЯТЕЛЬНО решай, когда какой язык уместнее, но ТВОЯ ЦЕЛЬ — МАКСИМУМ НЕМЕЦКОГО.
  * Для начинающих (A1-A2) используй больше русского для объяснений, но старайся чтобы ПОЛЬЗОВАТЕЛЬ писал на немецком.

⛔️ ЗАПРЕТ НА АНГЛИЙСКИЙ:
- Никогда не используй английский язык для объяснений!
- Если нужно перевести или объяснить слово — используй ТОЛЬКО РУССКИЙ.
- Пример: "verrückt" означает "сумасшедший" (НЕ "crazy").

ВОВЛЕЧЕНИЕ В РАЗГОВОР:
- Твоя задача — РАЗГОВОРИТЬ пользователя.
- Если ответы односложные ("Ja", "Gut") — задавай открытые вопросы ("Почему?", "А что тебе больше нравится?").
- Предлагай темы, если разговор затухает.
- Будь любопытным другом!

ДЛИНА ОТВЕТОВ:
- Обычно 2-4 предложения
- Можешь написать больше если есть что рассказать
- Не ограничивайся одним предложением

КРИТИЧЕСКИ ВАЖНО - ВОПРОСЫ:
- НЕ задавай вопрос в КАЖДОМ сообщении!
- Задавай вопрос только если это ЕСТЕСТВЕННО для разговора
- В 60-70% случаев ПРОСТО реагируй без вопроса
- Примеры без вопроса: "Cool!", "Das klingt super!", "Interessant!", "Verstehe!"
- Делись своим мнением, рассказывай о себе — не только спрашивай!

⚠️ ОБЯЗАТЕЛЬНОЕ ИСПРАВЛЕНИЕ ОШИБОК:
1. ИСПРАВЛЯЙ ТОЛЬКО НЕМЕЦКИЙ ЯЗЫК!
2. ПРОВЕРЯЙ ВСЁ СООБЩЕНИЕ ЦЕЛИКОМ! Не пропускай ошибки во второй части предложения.
   ❌ "Ich war in Tokyo, tokyo finde ich am liebsten" -> Бот должен исправить "finde ich am liebsten" на "mag ich am liebsten" или "hat mir am besten gefallen".
3. Если ошибок нет - НЕ пиши "Всё правильно", просто отвечай.
4. Если пользователь пишет на РУССКОМ — НЕ исправляй его русский!
5. Если пользователь сделал ошибку В НЕМЕЦКОМ — ОБЯЗАТЕЛЬНО исправь её!

Формат исправления:
1. СНАЧАЛА кратко исправь ВСЕ ошибки (можно списком, если их несколько)
2. ПОТОМ продолжай разговор на немецком

Примеры:

User: "Ich habe heute in das Kino gegangen"
Ты: "📝 *ins Kino* (in + das = ins, + gehen требует sein → ich bin gegangen)

Ah, cool! Was hast du geschaut? 🎬"

User: "Ich wohne in Berlin und ich arbeite als Programmierer"  
Ты: "📝 *Ich wohne... und arbeite* (не нужно повторять 'ich')

Programmierung ist interessant! Ich kenne auch Leute, die programmieren. 👨‍💻"

User: "Die Wetter ist heute schön"
Ты: "📝 *Das Wetter* (Wetter — neutral, не feminine)

Ja, stimmt! Perfekt für einen Spaziergang! ☀️"

User: "Ich bin müde weil ich habe viel gearbeitet"
Ты: "📝 *weil ich viel gearbeitet habe* (после weil глагол идёт в конец)

Verstehe, das klingt anstrengend! Ruh dich aus. 💤"

БЕЗ ОШИБОК — отвечай нормально без 📝:

User: "Ich habe gestern einen Film gesehen"
Ты: "Cool! War er gut? Ich schaue gerade viele Serien. 🎬"

ВАЖНО:
- Уровень: {user_level}
- Цель: {goal_text}
- ВСЕГДА исправляй ошибки! Это главная цель — помочь выучить язык
- После исправления — продолжай разговор естественно
- НЕ будь занудой, исправляй кратко и дружелюбно{context_info}"""
    
    def _create_model(
        self,
        user_level: str = "A2",
        user_goal: Optional[str] = None,
        personality: str = "friendly",
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Создание модели Gemini с системным промптом.
        
        Returns:
            Объект GenerativeModel
        """
        system_prompt = self._build_system_prompt(
            user_level=user_level,
            user_goal=user_goal,
            personality=personality,
            user_context=user_context,
        )
        
        model = genai.GenerativeModel(
            model_name=self.MODEL_NAME,
            generation_config=self._generation_config,
            safety_settings=self._safety_settings,
            system_instruction=system_prompt,
        )
        
        return model
    
    async def create_chat(
        self,
        user_id: int,
        user_level: str = "A2",
        user_goal: Optional[str] = None,
        personality: str = "friendly",
        user_context: Optional[Dict[str, Any]] = None,
        history: Optional[list[ChatMessage]] = None,
    ) -> None:
        """
        Создание нового чата для пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            user_level: Уровень владения языком
            user_goal: Цель изучения
            personality: Тип личности бота
            user_context: Контекст пользователя
            history: История предыдущих сообщений
        """
        model = self._create_model(
            user_level=user_level,
            user_goal=user_goal,
            personality=personality,
            user_context=user_context,
        )
        
        # Конвертация истории в формат Gemini
        gemini_history = []
        if history:
            for msg in history:
                gemini_history.append({
                    "role": msg.role if msg.role != "assistant" else "model",
                    "parts": [msg.content]
                })
        
        # Создание чата с историей
        chat = model.start_chat(history=gemini_history)
        
        self._chats[user_id] = chat
        self._chat_histories[user_id] = history or []
        
        logger.info(
            "Created chat for user %d (level=%s, personality=%s, history_len=%d)",
            user_id, user_level, personality, len(gemini_history)
        )
    
    async def get_or_create_chat(
        self,
        user_id: int,
        user_level: str = "A2",
        user_goal: Optional[str] = None,
        personality: str = "friendly",
        user_context: Optional[Dict[str, Any]] = None,
        history: Optional[list[ChatMessage]] = None,
    ) -> Any:
        """
        Получение существующего чата или создание нового.
        
        Args:
            user_id: ID пользователя Telegram
            user_level: Уровень владения языком
            user_goal: Цель изучения
            personality: Тип личности бота
            user_context: Контекст пользователя
            history: История (используется только при создании нового)
        
        Returns:
            Объект ChatSession
        """
        if user_id not in self._chats:
            await self.create_chat(
                user_id=user_id,
                user_level=user_level,
                user_goal=user_goal,
                personality=personality,
                user_context=user_context,
                history=history,
            )
        
        return self._chats[user_id]
    
    async def send_message(
        self,
        user_id: int,
        message: str,
        user_level: str = "A2",
        user_goal: Optional[str] = None,
        personality: str = "friendly",
        user_context: Optional[Dict[str, Any]] = None,
        history: Optional[list[ChatMessage]] = None,
    ) -> ChatResponse:
        """
        Отправка сообщения в чат и получение ответа.
        
        Args:
            user_id: ID пользователя Telegram
            message: Текст сообщения от пользователя
            user_level: Уровень владения языком
            user_goal: Цель изучения
            personality: Тип личности бота
            user_context: Контекст пользователя
            history: История сообщений (для восстановления контекста)
        
        Returns:
            ChatResponse с текстом ответа и количеством токенов
        
        Raises:
            Exception: При ошибке API
        """
        try:
            # Получаем или создаём чат
            chat = await self.get_or_create_chat(
                user_id=user_id,
                user_level=user_level,
                user_goal=user_goal,
                personality=personality,
                user_context=user_context,
                history=history,
            )
            
            logger.debug("Sending message to Gemini for user %d: %s", user_id, message[:100])
            
            # Отправка сообщения (синхронный вызов, но Gemini SDK handle это)
            response: GenerateContentResponse = await chat.send_message_async(message)
            
            # Извлечение текста ответа
            response_text = response.text
            
            # Подсчет токенов
            tokens_used = self._count_tokens(message, response_text)
            
            # Сохраняем в локальную историю
            if user_id in self._chat_histories:
                self._chat_histories[user_id].append(ChatMessage(role="user", content=message))
                self._chat_histories[user_id].append(ChatMessage(role="model", content=response_text))
            
            logger.info(
                "Gemini response for user %d: %d chars, ~%d tokens",
                user_id, len(response_text), tokens_used
            )
            
            return ChatResponse(
                text=response_text,
                tokens_used=tokens_used,
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else None
            )
            
        except Exception as e:
            logger.error("Gemini API error for user %d: %s", user_id, str(e))
            
            # Очищаем кеш чата при ошибке (пересоздадим при следующем запросе)
            self._chats.pop(user_id, None)
            
            raise
    
    def _count_tokens(self, input_text: str, output_text: str) -> int:
        """
        Приблизительный подсчет токенов.
        
        Gemini использует примерно 1 токен на 4 символа для латиницы
        и 1 токен на 1-2 символа для кириллицы.
        
        Args:
            input_text: Входной текст
            output_text: Выходной текст
        
        Returns:
            Приблизительное количество токенов
        """
        total_chars = len(input_text) + len(output_text)
        
        # Эвристика: средний коэффициент для смешанного русско-немецкого текста
        estimated_tokens = int(total_chars / 2.5)
        
        return max(estimated_tokens, 1)
    
    async def count_tokens_exact(self, text: str) -> int:
        """
        Точный подсчет токенов через API.
        
        Args:
            text: Текст для подсчета
        
        Returns:
            Количество токенов
        """
        try:
            model = genai.GenerativeModel(self.MODEL_NAME)
            result = await model.count_tokens_async(text)
            return result.total_tokens
        except Exception as e:
            logger.warning("Failed to count tokens: %s", str(e))
            return self._count_tokens(text, "")
    
    async def translate_word(self, word: str) -> str:
        """
        Быстрый перевод одного немецкого слова.
        
        Args:
            word: Немецкое слово для перевода
        
        Returns:
            Перевод и пример использования
        """
        prompt = f"""Переведи немецкое слово на русский язык кратко.

Слово: {word}

Формат ответа (только текст, без дополнительных символов):
[перевод на русском]

Пример: [короткое предложение с этим словом на немецком]"""
        
        try:
            model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=256,
                ),
            )
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error("Translation error for word '%s': %s", word, str(e))
            return f"Ошибка перевода: {word}"
    
    async def simple_translate(self, text: str) -> str:
        """
        Простой перевод текста с немецкого на русский.
        
        Args:
            text: Немецкий текст для перевода
        
        Returns:
            Перевод на русский
        """
        prompt = f"""Переведи этот немецкий текст на русский язык.
Дай только перевод, без дополнительных комментариев.

Текст: {text}"""
        
        try:
            model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                ),
            )
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error("Translation error: %s", str(e))
            return "Ошибка перевода"
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Транскрибирует аудио файл в текст через Gemini API.
        
        Args:
            audio_data: Байты аудио файла (OGG format от Telegram)
        
        Returns:
            Транскрибированный текст
        """
        import tempfile
        import pathlib
        
        try:
            # Сохраняем аудио во временный файл
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Загружаем файл в Gemini
            audio_file = genai.upload_file(path=temp_path, mime_type="audio/ogg")
            
            # Транскрипция
            prompt = """Transcribe this voice message to text accurately. 
The message may contain German, Russian, or a mix of both languages.
Preserve the exact words in their original language.
Output ONLY the transcribed text, nothing else."""
            
            model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )
            
            response = await model.generate_content_async([prompt, audio_file])
            transcription = response.text.strip()
            
            # Удаляем временный файл
            pathlib.Path(temp_path).unlink()
            
            # Удаляем файл из Gemini
            audio_file.delete()
            
            logger.info("Transcribed audio: %d bytes → %d chars", len(audio_data), len(transcription))
            return transcription
            
        except Exception as e:
            logger.error("Transcription error: %s", str(e))
            # Cleanup
            try:
                if 'temp_path' in locals():
                    pathlib.Path(temp_path).unlink(missing_ok=True)
                if 'audio_file' in locals():
                    audio_file.delete()
            except:
                pass
            return "[Не удалось распознать аудио]"
    
    async def analyze_pronunciation(self, transcription: str) -> dict:
        """
        Анализирует произношение по транскрипции через Gemini.
        
        Args:
            transcription: Распознанный текст
        
        Returns:
            {
                "score": 8.5,
                "good": ["Termin - четкое произношение"],
                "improve": ["möchte - звук ö слабый"],
                "tip": "Округляй губы для ö"
            }
        """
        import json
        
        prompt = f"""Ты эксперт по немецкому произношению для русскоязычных учеников.

ТРАНСКРИПЦИЯ РЕЧИ: "{transcription}"

Проанализируй произношение и дай оценку:

1. Оценка качества от 1.0 до 10.0
2. Что звучит хорошо (1-2 конкретных момента)
3. Что можно улучшить (1-2 главных момента)
4. Один практичный совет

ВАЖНО:
- Фокусируйся на типичных проблемах русскоговорящих: r, h, ch, ü, ö, ä, sch
- Всегда начинай с позитива
- Будь кратким и мотивирующим
- Не более 2-3 пунктов в "improve"

Верни ТОЛЬКО валидный JSON в формате:
{{
  "score": 8.5,
  "good": ["конкретный пример 1", "пример 2"],
  "improve": ["конкретная рекомендация 1", "рекомендация 2"],
  "tip": "один главный совет"
}}"""

        try:
            model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=512,
                ),
            )
            
            response = await model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Убираем markdown code blocks если есть
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Парсим JSON
            feedback = json.loads(text)
            
            # Валидация
            if not all(k in feedback for k in ["score", "good", "improve", "tip"]):
                raise ValueError("Missing keys in feedback")
            
            # Убеждаемся что score в пределах
            feedback["score"] = max(1.0, min(10.0, float(feedback["score"])))
            
            logger.info("Pronunciation analyzed: score=%.1f", feedback["score"])
            return feedback
            
        except Exception as e:
            logger.error("Pronunciation analysis error: %s", str(e))
            # FallbackResponse
            return {
                "score": 7.0,
                "good": ["Общее звучание понятно"],
                "improve": ["Продолжай практиковаться"],
                "tip": "Слушай больше немецкой речи"
            }
    
    def clear_chat(self, user_id: int) -> None:
        """
        Очистка чата пользователя.
        
        Args:
            user_id: ID пользователя
        """
        self._chats.pop(user_id, None)
        self._chat_histories.pop(user_id, None)
        logger.info("Cleared chat for user %d", user_id)
    
    def get_chat_history(self, user_id: int) -> list[ChatMessage]:
        """
        Получение истории чата.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список сообщений
        """
        return self._chat_histories.get(user_id, [])
    
    def has_active_chat(self, user_id: int) -> bool:
        """
        Проверка наличия активного чата.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если чат существует
        """
        return user_id in self._chats
    
    async def generate_grammar_exercise(
        self,
        context_phrase: str,
        topic: str,
        user_level: str = "A2",
    ) -> dict:
        """
        Генерирует грамматическое упражнение на основе контекста разговора.
        
        Args:
            context_phrase: Фраза из диалога пользователя
            topic: Тема упражнения (articles, cases, perfekt, word_order, prepositions, adjectives)
            user_level: Уровень пользователя
        
        Returns:
            {
                "topic": "articles",
                "question": "Kino - welcher Artikel?",
                "option_a": "der Kino",
                "option_b": "die Kino", 
                "option_c": "das Kino",
                "correct": "C",
                "rule": "Слова на -o обычно neutral (das Auto, das Foto)",
                "follow_up": "So, gehst du oft ins Kino? 🎬"
            }
        """
        import json
        
        topic_prompts = {
            "articles": "der/die/das артикль для существительного",
            "cases": "правильный падеж (Nominativ/Akkusativ/Dativ/Genitiv)",
            "perfekt": "правильная форма Perfekt или Präteritum",
            "word_order": "правильный порядок слов в предложении",
            "prepositions": "правильный предлог и/или падеж после предлога",
            "adjectives": "правильное окончание прилагательного",
        }
        
        topic_desc = topic_prompts.get(topic, topic_prompts["articles"])
        
        prompt = f"""Ты создаёшь грамматическое упражнение для изучающего немецкий (уровень {user_level}).

КОНТЕКСТ РАЗГОВОРА:
"{context_phrase}"

ЗАДАНИЕ:
Создай БЫСТРОЕ упражнение на тему: {topic_desc}

ТРЕБОВАНИЯ:
1. Вопрос должен быть связан с контекстом разговора
2. Формат: один вопрос + 3 варианта ответа (A, B, C)
3. Только ОДИН вариант правильный
4. Правило объяснения - КРАТКО (1-2 предложения, на русском)
5. follow_up - вопрос для продолжения разговора (на немецком)

ПРИМЕРЫ ХОРОШИХ УПРАЖНЕНИЙ:

Тема articles, контекст "Ich war gestern im Kino":
Question: "Kino — welcher Artikel?"
A: "der Kino"  B: "die Kino"  C: "das Kino"
Correct: C
Rule: "Слова на -o обычно neutral: das Auto, das Foto, das Kino"
Follow-up: "Was hast du im Kino geschaut? 🎬"

Тема cases, контекст "Ich helfe meinem Freund":
Question: "Mit welchem Fall? 'Ich helfe ___ Freund'"
A: "mein (Nominativ)"  B: "meinen (Akkusativ)"  C: "meinem (Dativ)"
Correct: C
Rule: "helfen требует Dativ: Ich helfe DIR, nicht DICH"
Follow-up: "Das ist nett! Was macht dein Freund? 👍"

Верни ТОЛЬКО валидный JSON:
{{
  "topic": "{topic}",
  "question": "...",
  "option_a": "...",
  "option_b": "...",
  "option_c": "...",
  "correct": "A|B|C",
  "rule": "краткое правило на русском",
  "follow_up": "вопрос для продолжения на немецком"
}}"""

        try:
            model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=512,
                ),
            )
            
            response = await model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Убираем markdown code blocks если есть
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Парсим JSON
            exercise = json.loads(text)
            
            # Валидация обязательных полей
            required = ["topic", "question", "option_a", "option_b", "option_c", "correct", "rule", "follow_up"]
            if not all(k in exercise for k in required):
                raise ValueError(f"Missing keys in exercise: {[k for k in required if k not in exercise]}")
            
            # Нормализуем correct к uppercase
            exercise["correct"] = exercise["correct"].upper()
            if exercise["correct"] not in ["A", "B", "C"]:
                raise ValueError(f"Invalid correct answer: {exercise['correct']}")
            
            logger.info("Generated grammar exercise: topic=%s, correct=%s", topic, exercise["correct"])
            return exercise
            
        except Exception as e:
            logger.error("Grammar exercise generation error: %s", str(e))
            # Fallback упражнение
            return {
                "topic": "articles",
                "question": "Haus — welcher Artikel?",
                "option_a": "der Haus",
                "option_b": "die Haus",
                "option_c": "das Haus",
                "correct": "C",
                "rule": "Haus (дом) — neutral, поэтому das Haus",
                "follow_up": "Wohnst du in einem Haus oder in einer Wohnung? 🏠"
            }



# Singleton instance (инициализируется при импорте с API key из config)
_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Получение singleton экземпляра GeminiClient.
    
    Returns:
        GeminiClient instance
    
    Raises:
        RuntimeError: Если клиент не инициализирован
    """
    global _client
    if _client is None:
        raise RuntimeError("GeminiClient not initialized. Call init_gemini_client() first.")
    return _client


def init_gemini_client(api_key: str) -> GeminiClient:
    """
    Инициализация singleton GeminiClient.
    
    Args:
        api_key: Google AI API key
    
    Returns:
        GeminiClient instance
    """
    global _client
    _client = GeminiClient(api_key=api_key)
    return _client
