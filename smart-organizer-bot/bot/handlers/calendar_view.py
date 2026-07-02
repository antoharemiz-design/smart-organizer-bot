import calendar
from datetime import date, datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from calendar_core.local_calendar import LocalCalendarService

router = Router()

# Константы для callback
CALENDAR_PREFIX = "cal"
MONTH_NAV = "month_nav"
DAY_SELECT = "day_select"


def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    """Генерирует инлайн-календарь на месяц."""
    # Название месяца и год
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"

    buttons = []

    # Навигация: <  Июнь 2026  >
    nav_row = [
        InlineKeyboardButton(text="◀️", callback_data=f"{CALENDAR_PREFIX}:{MONTH_NAV}:prev:{year}:{month}"),
        InlineKeyboardButton(text=header, callback_data="ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"{CALENDAR_PREFIX}:{MONTH_NAV}:next:{year}:{month}"),
    ]
    buttons.append(nav_row)

    # Дни недели
    days_row = [InlineKeyboardButton(text=day, callback_data="ignore") for day in
                ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]]
    buttons.append(days_row)

    # Числа
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        week_buttons = []
        for day_num in week:
            if day_num == 0:
                week_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                selected_date = date(year, month, day_num)
                week_buttons.append(
                    InlineKeyboardButton(
                        text=str(day_num),
                        callback_data=f"{CALENDAR_PREFIX}:{DAY_SELECT}:{selected_date.isoformat()}"
                    )
                )
        buttons.append(week_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("calendar"))
async def cmd_calendar(message: Message):
    today = date.today()
    keyboard = generate_calendar(today.year, today.month)
    await message.answer("📅 Выберите дату:", reply_markup=keyboard)


@router.callback_query(F.data.startswith(CALENDAR_PREFIX))
async def process_calendar(callback: CallbackQuery, calendar_service: LocalCalendarService):
    parts = callback.data.split(":")
    action = parts[1]

    if action == MONTH_NAV:
        # Навигация по месяцам
        direction = parts[2]
        year = int(parts[3])
        month = int(parts[4])

        if direction == "prev":
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
        elif direction == "next":
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

        keyboard = generate_calendar(year, month)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

    elif action == DAY_SELECT:
        # Выбор конкретной даты
        date_str = parts[2]
        selected_date = date.fromisoformat(date_str)
        user_id = str(callback.from_user.id)

        tasks = await calendar_service.get_tasks(user_id, selected_date)

        if tasks:
            lines = [f"📋 <b>Задачи на {selected_date.strftime('%d.%m.%Y')}:</b>\n"]
            for task in tasks:
                title = task.get("title", "Без названия")
                time_str = task.get("event_time", "")
                time_part = f" в {time_str}" if time_str else ""
                is_all_day = task.get("is_all_day", 0)
                if is_all_day:
                    time_part = " (весь день)"
                lines.append(f"• {title}{time_part}")
            await callback.message.answer("\n".join(lines), parse_mode="HTML")
        else:
            await callback.message.answer(
                f"📭 На {selected_date.strftime('%d.%m.%Y')} задач нет.",
                parse_mode="HTML"
            )

    await callback.answer()