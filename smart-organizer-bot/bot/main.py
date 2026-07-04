import asyncio
import logging
import threading

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from bot.handlers import (
    start, task_input, tasks_view, calendar_view,
    callbacks, voice_input, export_calendar, menu_handlers,
    stats, delete_task, settings_handler, unknown
)
from bot.middlewares.dependency_injection import DIMiddleware
from bot.scheduler import TaskScheduler
from bot.web_server import run_web_server
from calendar_core.local_calendar import LocalCalendarService
from adaptation.habit_tracker import HabitTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для доступа из обработчиков
_calendar_service = None


async def main():
    global _calendar_service

    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация календаря
    calendar_service = LocalCalendarService()
    await calendar_service.initialize()
    _calendar_service = calendar_service

    # Инициализация трекера привычек
    habit_tracker = HabitTracker()
    await habit_tracker.initialize()

    # Создание планировщика
    scheduler = TaskScheduler(bot, calendar_service)
    dp["scheduler"] = scheduler
    dp["habit_tracker"] = habit_tracker
    scheduler.start()

    # Внедрение зависимостей
    dp.update.middleware(DIMiddleware(calendar_service, scheduler))

    # Подключение роутеров (порядок важен!)
    dp.include_router(start.router)
    dp.include_router(calendar_view.router)
    dp.include_router(tasks_view.router)
    dp.include_router(export_calendar.router)
    dp.include_router(stats.router)
    dp.include_router(settings_handler.router)
    dp.include_router(callbacks.router)
    dp.include_router(voice_input.router)
    dp.include_router(delete_task.router)
    dp.include_router(menu_handlers.router)
    dp.include_router(task_input.router)
    dp.include_router(unknown.router)

    # Запуск веб-сервера в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("Web server started on port 8080")

    logger.info("Бот запущен со всеми модулями")

    try:
        await dp.start_polling(bot)
    finally:
        await scheduler.stop()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())