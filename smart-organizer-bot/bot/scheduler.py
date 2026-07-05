import asyncio
import logging
import pytz
from datetime import datetime, date, time as dt_time
import aioschedule
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from calendar_core.local_calendar import LocalCalendarService
from bot.keyboards.main_menu import get_task_actions_keyboard

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self, bot: Bot, calendar_service: LocalCalendarService):
        self.bot = bot
        self.calendar_service = calendar_service
        self.user_timezones = {}  # user_id -> timezone
        self._task = None
        self._reminder_checks = {}  # user_id -> set of task_ids уже отправленных

    def set_user_timezone(self, user_id: str, timezone: str):
        """Сохраняет часовой пояс пользователя."""
        self.user_timezones[user_id] = timezone
        logger.info(f"User {user_id} timezone set to {timezone}")

    async def _send_morning_greeting(self):
        """Утреннее приветствие с планами на день (8:00 МСК)."""
        logger.info("Morning greeting triggered")
        today = date.today()
        users = list(self.user_timezones.keys())

        for user_id in users:
            try:
                tasks = await self.calendar_service.get_tasks(str(user_id), today)
                if tasks:
                    lines = [f"🌅 <b>Доброе утро! Планы на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"]
                    for task in tasks:
                        title = task.get("title", "Без названия")
                        time_str = task.get("event_time", "")
                        time_part = f" в {time_str}" if time_str else ""
                        is_all_day = task.get("is_all_day", 0)
                        if is_all_day:
                            time_part = " (весь день)"
                        lines.append(f"• {title}{time_part}")
                    await self.bot.send_message(int(user_id), "\n".join(lines), parse_mode="HTML")
                else:
                    await self.bot.send_message(
                        int(user_id),
                        f"🌅 <b>Доброе утро!</b> На сегодня задач нет. Хорошего дня!",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Failed to send morning greeting to {user_id}: {e}")

    async def _check_reminders(self):
        """Проверяет задачи, для которых наступило время, и отправляет напоминания."""
        users = list(self.user_timezones.keys())

        for user_id in users:
            try:
                # Получаем часовой пояс пользователя
                timezone_str = self.user_timezones.get(user_id, "Europe/Moscow")

                # Получаем текущее время в UTC и конвертируем
                from datetime import timezone as tz
                import pytz

                user_tz = pytz.timezone(timezone_str)
                now = datetime.now(user_tz)
                current_time = now.strftime("%H:%M")
                today = now.date()

                tasks = await self.calendar_service.get_tasks(str(user_id), today)

                for task in tasks:
                    task_id = task.get("id")
                    task_time = task.get("event_time")
                    is_all_day = task.get("is_all_day", 0)

                    if is_all_day or not task_time:
                        continue

                    if task_time == current_time:
                        if user_id not in self._reminder_checks:
                            self._reminder_checks[user_id] = set()

                        if task_id not in self._reminder_checks[user_id]:
                            title = task.get("title", "Без названия")

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="✅ Выполнено", callback_data=f"task_done:{task_id}"),
                                    InlineKeyboardButton(text="🔄 Перенести", callback_data=f"task_move:{task_id}")
                                ]
                            ])

                            await self.bot.send_message(
                                int(user_id),
                                f"🔔 <b>Напоминание!</b>\n\n"
                                f"Задача: {title}\n"
                                f"Время: {task_time}\n\n"
                                f"Пора выполнять!",
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )

                            self._reminder_checks[user_id].add(task_id)
                            logger.info(f"Reminder sent to {user_id} for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to check reminders for {user_id}: {e}")

        # Очистка старых напоминаний в полночь
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            self._reminder_checks.clear()

    async def _send_evening_review(self):
        """Вечерний опрос с кнопками «Выполнено / Перенести / Удалить»."""
        logger.info("Evening review triggered")
        today = date.today()
        users = list(self.user_timezones.keys())

        for user_id in users:
            try:
                tasks = await self.calendar_service.get_tasks(str(user_id), today)
                if not tasks:
                    continue

                for task in tasks:
                    task_id = task.get("id")
                    title = task.get("title", "Без названия")
                    time_str = task.get("event_time", "")

                    # Используем общую клавиатуру с тремя кнопками
                    keyboard = get_task_actions_keyboard(task_id)

                    text = f"🌙 <b>Вечерняя проверка</b>\n\nЗадача: {title}"
                    if time_str:
                        text += f"\nВремя: {time_str}"
                    text += "\n\nЧто с ней?"

                    await self.bot.send_message(
                        int(user_id),
                        text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to send evening review to {user_id}: {e}")

    def start(self):
        """Запуск планировщика."""
        # Утреннее приветствие в 8:00
        aioschedule.every().day.at("08:00").do(self._send_morning_greeting)

        # Проверка напоминаний каждую минуту
        aioschedule.every(1).minutes.do(self._check_reminders)

        # Вечерний опрос в 21:00
        aioschedule.every().day.at("21:00").do(self._send_evening_review)

        logger.info("Scheduler started: morning 08:00, reminders every minute, evening 21:00")
        self._task = asyncio.create_task(self._run_scheduler())

    async def _run_scheduler(self):
        while True:
            await aioschedule.run_pending()
            await asyncio.sleep(30)  # Проверка каждые 30 секунд

    async def stop(self):
        if self._task:
            self._task.cancel()