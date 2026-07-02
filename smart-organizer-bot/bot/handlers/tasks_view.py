from datetime import date
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from calendar_core.local_calendar import LocalCalendarService

router = Router()


@router.message(Command("tasks"))
async def cmd_tasks(message: Message, calendar_service: LocalCalendarService):
    user_id = str(message.from_user.id)
    today = date.today()

    tasks = await calendar_service.get_tasks(user_id, date_filter=today)

    if not tasks:
        await message.answer("📭 На сегодня задач нет.")
        return

    lines = [f"📋 <b>Задачи на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"]
    for task in tasks:
        title = task.get("title", "Без названия")
        time_str = task.get("event_time", "")
        time_part = f" в {time_str}" if time_str else ""
        is_all_day = task.get("is_all_day", 0)
        if is_all_day:
            time_part = " (весь день)"
        lines.append(f"• {title}{time_part}")

    await message.answer("\n".join(lines), parse_mode="HTML")