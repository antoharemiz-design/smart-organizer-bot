import io
import logging
import os
from aiogram import Router, F
from aiogram.types import Message
from nlu.service import parse_message
from calendar_core.local_calendar import LocalCalendarService

router = Router()
logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("Whisper model loaded (tiny)")
    return _model


@router.message(F.voice)
async def handle_voice(message: Message, calendar_service):
    """Обработка голосовых сообщений."""
    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}") as resp:
                audio_data = await resp.read()

        temp_path = f"temp_{message.from_user.id}.ogg"
        with open(temp_path, "wb") as f:
            f.write(audio_data)

        model = get_whisper_model()
        segments, info = model.transcribe(temp_path, language="ru")
        text = " ".join(segment.text for segment in segments)

        os.remove(temp_path)

        if not text.strip():
            await message.answer("Не удалось распознать речь. Попробуйте ещё раз.")
            return

        await message.answer(f"🎤 Распознано: {text}")

        nlu_result = await parse_message(text)
        if nlu_result and nlu_result.intent == "task" and nlu_result.task_draft:
            task = nlu_result.task_draft
            user_id = str(message.from_user.id)
            await calendar_service.add_task(user_id, task)
            time_str = task.event_time.strftime("%H:%M") if task.event_time else "не указано"
            await message.answer(
                f"✅ Задача сохранена:\n"
                f"• {task.title}\n"
                f"• Дата: {task.due_date}\n"
                f"• Время: {time_str}"
            )
        else:
            await message.answer("Не удалось создать задачу из голосового сообщения. Попробуйте текстом.")
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await message.answer("Ошибка при обработке голосового сообщения.")