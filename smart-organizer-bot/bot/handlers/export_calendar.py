from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from calendar_core.local_calendar import LocalCalendarService
import tempfile
import os

router = Router()


def generate_ics(tasks: list) -> str:
    """Генерирует ICS-контент из списка задач."""
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SmartOrganizerBot//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for task in tasks:
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"SUMMARY:{task.get('title', 'Без названия')}")

        if task.get("due_date"):
            dt = task["due_date"]
            if task.get("is_all_day"):
                ics_content.append(f"DTSTART;VALUE=DATE:{dt.replace('-', '')}")
                ics_content.append(f"DTEND;VALUE=DATE:{dt.replace('-', '')}")
            else:
                time_str = task.get("event_time", "00:00")
                dt_start = f"{dt.replace('-', '')}T{time_str.replace(':', '')}00"
                ics_content.append(f"DTSTART:{dt_start}")
                ics_content.append(f"DTEND:{dt_start}")

        ics_content.append(f"UID:{task.get('id')}@smartorganizer")
        ics_content.append("END:VEVENT")

    ics_content.append("END:VCALENDAR")
    return "\r\n".join(ics_content)


@router.message(Command("export"))
async def cmd_export_calendar(message: Message, calendar_service: LocalCalendarService):
    """Экспорт задач в iCalendar (.ics) файл."""
    user_id = str(message.from_user.id)
    tasks = await calendar_service.get_tasks(user_id)

    if not tasks:
        await message.answer("Нет задач для экспорта.")
        return

    # Используем функцию generate_ics
    ics_content = generate_ics(tasks)

    # Сохраняем во временный файл
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ics", delete=False, encoding="utf-8") as f:
        f.write(ics_content)
        temp_path = f.name

    # Отправляем файл
    await message.answer_document(
        FSInputFile(temp_path, filename="tasks.ics"),
        caption="📅 Ваши задачи в формате iCalendar. Можно импортировать в Google Calendar, Apple Calendar и другие."
    )

    os.remove(temp_path)