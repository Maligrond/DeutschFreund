"""
Text-to-Speech helper для генерации правильного произношения.
Использует Google Cloud TTS.
"""

import logging
import tempfile
import pathlib
from typing import Optional

logger = logging.getLogger(__name__)

# Будем использовать gTTS (бесплатный) вместо Google Cloud TTS
# Если нужен Google Cloud TTS - раскомментить соответствующий код

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    logger.warning("gTTS not installed. Install with: pip install gtts")


async def generate_speech(
    text: str,
    language: str = "de",
    slow: bool = False
) -> Optional[bytes]:
    """
    Генерирует аудио из текста на немецком языке.
    
    Args:
        text: Текст для озвучки
        language: Код языка (de для немецкого)
        slow: Медленное произношение для обучения
    
    Returns:
        Байты MP3 аудио или None если ошибка
    """
    if not HAS_GTTS:
        logger.error("gTTS library not available")
        return None
    
    try:
        # Создаём TTS объект
        tts = gTTS(text=text, lang=language, slow=slow)
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name
        
        tts.save(temp_path)
        
        # Читаем байты
        with open(temp_path, 'rb') as f:
            audio_bytes = f.read()
        
        # Удаляем временный файл
        pathlib.Path(temp_path).unlink()
        
        logger.info("Generated TTS audio: %d bytes for text '%s'", len(audio_bytes), text[:30])
        return audio_bytes
        
    except Exception as e:
        logger.error("TTS generation error: %s", str(e))
        return None


# ============ Google Cloud TTS (альтернатива) ============
# 
# Раскомментить если хочешь использовать Google Cloud TTS вместо gTTS:
#
# from google.cloud import texttospeech
# 
# async def generate_speech_google(text: str) -> Optional[bytes]:
#     """Генерация через Google Cloud TTS (требует API key)."""
#     try:
#         client = texttospeech.TextToSpeechClient()
#         
#         synthesis_input = texttospeech.SynthesisInput(text=text)
#         voice = texttospeech.VoiceSelectionParams(
#             language_code="de-DE",
#             name="de-DE-Neural2-B",  # Мужской голос
#             ssml_gender=texttospeech.SsmlVoiceGender.MALE
#         )
#         audio_config = texttospeech.AudioConfig(
#             audio_encoding=texttospeech.AudioEncoding.MP3
#         )
#         
#         response = client.synthesize_speech(
#             input=synthesis_input,
#             voice=voice,
#             audio_config=audio_config
#         )
#         
#         return response.audio_content
#         
#     except Exception as e:
#         logger.error("Google TTS error: %s", str(e))
#         return None
