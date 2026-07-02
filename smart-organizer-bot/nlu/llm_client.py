"""
Клиент для LLM-провайдеров: DeepSeek, Google Gemini, OpenRouter, Groq, заглушка.
"""
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional

from pydantic import ValidationError

from common.schemas import TaskDraft
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.deepseek_client = None
        self.gemini_client = None
        self.openrouter_client = None
        self.groq_client = None

        if self.provider == "deepseek" and settings.DEEPSEEK_API_KEY:
            import openai
            self.deepseek_client = openai.AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            )
            logger.info("LLM: DeepSeek enabled")
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            from google import genai
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("LLM: Gemini enabled")
        elif self.provider == "openrouter" and settings.OPENROUTER_API_KEY:
            import openai
            self.openrouter_client = openai.AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
            )
            logger.info(f"LLM: OpenRouter enabled (model: {settings.OPENROUTER_MODEL})")
        elif self.provider == "groq" and settings.GROQ_API_KEY:
            import openai
            self.groq_client = openai.AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
            )
            logger.info(f"LLM: Groq enabled (model: {settings.GROQ_MODEL})")
        else:
            logger.warning("No LLM provider configured. Using stub extractor.")

    async def extract_task(self, text: str, current_dt: datetime) -> Optional[TaskDraft]:
        if self.deepseek_client:
            return await self._deepseek_extract(text, current_dt)
        if self.gemini_client:
            return await self._gemini_extract(text, current_dt)
        if self.openrouter_client:
            return await self._openrouter_extract(text, current_dt)
        if self.groq_client:
            return await self._groq_extract(text, current_dt)
        return self._stub_extract(text, current_dt)

    async def _groq_extract(self, text: str, current_dt: datetime) -> Optional[TaskDraft]:
        prompt = self._build_prompt(text, current_dt)
        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Ты — ассистент-органайзер. Отвечай только JSON. Не добавляй комментарии."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            content = response.choices[0].message.content
            logger.debug(f"Groq raw: {content}")
            return self._parse_json_to_draft(content)
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None

    async def _deepseek_extract(self, text: str, current_dt: datetime) -> Optional[TaskDraft]:
        prompt = self._build_prompt(text, current_dt)
        try:
            response = await self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты — ассистент-органайзер. Отвечай только JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            content = response.choices[0].message.content
            logger.debug(f"DeepSeek raw: {content}")
            return self._parse_json_to_draft(content)
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return None

    async def _gemini_extract(self, text: str, current_dt: datetime) -> Optional[TaskDraft]:
        prompt = self._build_prompt(text, current_dt)
        try:
            response = await self.gemini_client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"temperature": 0.1, "max_output_tokens": 300},
            )
            content = response.text
            logger.debug(f"Gemini raw: {content}")
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return self._parse_json_to_draft(content.strip())
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

    async def _openrouter_extract(self, text: str, current_dt: datetime) -> Optional[TaskDraft]:
        prompt = self._build_prompt(text, current_dt)
        try:
            response = await self.openrouter_client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": "Ты — ассистент-органайзер. Отвечай только JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=300,
                extra_headers={
                    "HTTP-Referer": "https://t.me/UmniyOrganaizerBot",
                    "X-Title": "SmartOrganizer",
                },
            )
            content = response.choices[0].message.content
            logger.debug(f"OpenRouter raw: {content}")
            return self._parse_json_to_draft(content)
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return None

    def _build_prompt(self, text: str, current_dt: datetime) -> str:
        today_str = current_dt.strftime("%Y-%m-%d")
        time_str = current_dt.strftime("%H:%M")
        weekday = current_dt.strftime("%A")
        return f"""Ты — умный ассистент-органайзер. Извлеки из сообщения пользователя данные для задачи.
    Верни СТРОГО ТОЛЬКО JSON, без пояснений и комментариев.
    Поля:
    - title: краткое название задачи (только суть, без "напомни", "запланируй", предлогов)
    - due_date: дата в формате ГГГГ-ММ-ДД или null
    - event_time: время в формате ЧЧ:ММ или null
    - is_all_day: true/false
    - recurrence: "daily","weekly","monthly","yearly" или null
    - reminder_minutes_before: число минут или null
    - notes: дополнительные заметки или null

    ПРАВИЛА КОНВЕРТАЦИИ ВРЕМЕНИ (это критически важно!):
    - "к 7 вечера" → event_time: "19:00"
    - "в 7 вечера" → event_time: "19:00"  
    - "к 8 утра" → event_time: "08:00"
    - "в 3 дня" → event_time: "15:00"
    - "в 10 вечера" → event_time: "22:00"
    - "в обед" → event_time: "12:00"
    - "к полуночи" → event_time: "23:59"
    - Всегда конвертируй "вечера" в 24-часовой формат (19-23)
    - "утра" = 04-11, "дня" = 12-17, "вечера" = 18-23, "ночи" = 00-03

    ДРУГИЕ ПРАВИЛА:
    1. "пойти на работу" → title: "Пойти на работу"
    2. "завтра", "сегодня", "послезавтра" — вычисли точную дату относительно {today_str}
    3. "в пятницу", "в понедельник" — вычисли ближайшую дату
    4. Если дата не указана — due_date: null
    5. Убери из title: "напомни", "запланируй", "добавь", "надо", "нужно"

    Сегодня: {today_str}, текущее время: {time_str}, день недели: {weekday}.

    Сообщение: {text}

    Верни ТОЛЬКО JSON:"""

    def _parse_json_to_draft(self, json_text: str) -> Optional[TaskDraft]:
        try:
            cleaned = json_text.strip()
            # Убираем маркдаун-обёртки
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                if len(parts) >= 2:
                    cleaned = parts[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            # Находим JSON объект
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                cleaned = cleaned[start:end]

            data = json.loads(cleaned)
            return TaskDraft(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            return None

    # Заглушка
    def _stub_extract(self, text: str, current_dt: datetime) -> Optional[TaskDraft]:
        import re
        task = TaskDraft()
        text_lower = text.lower()

        # Дата
        if "завтра" in text_lower:
            task.due_date = current_dt.date() + timedelta(days=1)
        elif "послезавтра" in text_lower:
            task.due_date = current_dt.date() + timedelta(days=2)
        elif "сегодня" in text_lower:
            task.due_date = current_dt.date()
        else:
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            for i, day in enumerate(days):
                if day in text_lower:
                    today_idx = current_dt.weekday()
                    diff = (i - today_idx) % 7
                    if diff == 0:
                        diff = 7
                    task.due_date = current_dt.date() + timedelta(days=diff)
                    break

        # Время — расширенный поиск
        hour = None
        minute = 0

        # Формат "к 7 вечера", "в 8 утра"
        period_match = re.search(r'[кв]\s+(\d{1,2})\s*(вечера|утра|дня|ночи|час|часов)', text_lower)
        if period_match:
            hour = int(period_match.group(1))
            period = period_match.group(2)
            if period in ("вечера", "час", "часов") and hour < 12 and hour >= 5:
                hour += 12
            elif period == "ночи" and hour < 4:
                hour += 12
            elif period == "дня" and hour == 12:
                hour = 12
            task.event_time = time(hour, minute)

        # Формат "в 19:00", "к 19:00"
        if not task.event_time:
            time_match = re.search(r'[кв]\s+(\d{1,2}):(\d{2})', text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                if 0 <= hour < 24 and 0 <= minute < 60:
                    task.event_time = time(hour, minute)

        # Формат "в 19", "к 19"
        if not task.event_time:
            time_match = re.search(r'[кв]\s+(\d{1,2})\b', text)
            if time_match:
                hour = int(time_match.group(1))
                if 5 <= hour <= 23:
                    task.event_time = time(hour, 0)

        # Очистка заголовка
        title = text
        for word in ["завтра", "сегодня", "послезавтра", "утром", "днём", "вечером", "ночью"]:
            title = re.sub(r'\b' + word + r'\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'[кв]\s+\d{1,2}:?\d{0,2}\s*(вечера|утра|дня|ночи|часов)?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()
        task.title = title[:100] or text[:100]

        return task