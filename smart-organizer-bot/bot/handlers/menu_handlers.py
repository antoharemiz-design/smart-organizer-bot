from aiogram import Router, F
from aiogram.types import Message
from datetime import date

router = Router()


@router.message(F.text == "📋 Мои задачи")
async def menu_tasks_today(message: Message, calendar_service):
    """Обработчик кнопки 'Мои задачи'."""
    user_id = str(message.from_user.id)
    today = date.today()

    tasks = await calendar_service.get_tasks(user_id, date_filter=today)

    if not tasks:
        await message.answer(
            "📭 <b>На сегодня задач нет.</b>\n\n"
            "Хотите создать новую? Просто напишите мне задачу!",
            parse_mode="HTML"
        )
        return

    lines = [f"📋 <b>Задачи на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"]
    for i, task in enumerate(tasks, 1):
        title = task.get("title", "Без названия")
        time_str = task.get("event_time", "")
        time_part = f" ⏰ {time_str}" if time_str else ""
        is_all_day = task.get("is_all_day", 0)
        if is_all_day:
            time_part = " 📆 (весь день)"
        lines.append(f"{i}. {title}{time_part}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "📅 Календарь")
async def menu_calendar(message: Message):
    """Обработчик кнопки 'Календарь'."""
    from bot.handlers.calendar_view import generate_calendar
    today = date.today()
    keyboard = generate_calendar(today.year, today.month)
    await message.answer("📅 <b>Выберите дату для просмотра задач:</b>", reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📤 Экспорт")
async def menu_export(message: Message, calendar_service):
    """Обработчик кнопки 'Экспорт'."""
    from bot.handlers.export_calendar import generate_ics
    import tempfile
    import os
    from aiogram.types import FSInputFile

    user_id = str(message.from_user.id)
    tasks = await calendar_service.get_tasks(user_id)

    if not tasks:
        await message.answer(
            "📭 <b>Нет задач для экспорта.</b>\n\n"
            "Создайте хотя бы одну задачу!",
            parse_mode="HTML"
        )
        return

    ics_content = generate_ics(tasks)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ics", delete=False, encoding="utf-8") as f:
        f.write(ics_content)
        temp_path = f.name

    await message.answer_document(
        FSInputFile(temp_path, filename="tasks.ics"),
        caption="📅 <b>Ваши задачи в формате iCalendar.</b>\nМожно импортировать в Google Calendar, Apple Calendar и другие.",
        parse_mode="HTML"
    )
    os.remove(temp_path)


@router.message(F.text == "📊 Статистика")
async def menu_stats(message: Message, calendar_service):
    """Обработчик кнопки 'Статистика'."""
    from bot.handlers.stats import cmd_stats
    await cmd_stats(message, calendar_service)


@router.message(F.text == "❌ Удалить задачу")
async def menu_delete_task(message: Message, calendar_service, state):
    """Обработчик кнопки 'Удалить задачу'."""
    from bot.handlers.delete_task import menu_delete_task as del_task
    await del_task(message, calendar_service, state)


@router.message(F.text == "🌐 Веб-интерфейс")
async def menu_web(message: Message):
    """Обработчик кнопки 'Веб-интерфейс'."""
    await message.answer(
        "🌐 <b>Веб-интерфейс ваших задач:</b>\n\n"
        "https://smart-organizer-bot-5s7c.onrender.com\n\n"
        "<i>Откройте в браузере для просмотра всех задач.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@router.message(F.text == "🕐 Время")
async def menu_time(message: Message, scheduler):
    from datetime import datetime
    import pytz

    # Берём часовой пояс пользователя
    user_id = str(message.from_user.id)
    timezone_str = scheduler.user_timezones.get(user_id, "Europe/Moscow")
    user_tz = pytz.timezone(timezone_str)
    now = datetime.now(user_tz)

    await message.answer(
        f"🕐 Текущее время: {now.strftime('%H:%M:%S')}\n"
        f"📅 Дата: {now.strftime('%d.%m.%Y')}\n"
        f"🌍 Часовой пояс: {timezone_str}"
    )


@router.message(F.text == "⚙️ Настройки")
async def menu_settings(message: Message, calendar_service):
    """Обработчик кнопки 'Настройки'."""
    from bot.handlers.settings_handler import cmd_settings
    await cmd_settings(message, calendar_service)


@router.message(F.text == "⚙️ Помощь")
async def menu_help(message: Message):
    """Обработчик кнопки 'Помощь'."""
    help_text = (
        "🤖 <b>Умный Органайзер</b>\n\n"
        "<b>Как создавать задачи:</b>\n"
        "• Текст: напишите «Позвонить врачу завтра в 10»\n"
        "• Текст: напишите задачу в чат\n\n"
        "<b>Примеры:</b>\n"
        "• Купить молоко завтра в 18\n"
        "• Встреча с клиентом в пятницу в 15:00\n"
        "• Позвонить маме каждый вторник в 19\n\n"
        "<b>Автоматические уведомления:</b>\n"
        "🌅 8:00 — план на день\n"
        "🔔 Точно в указанное время — напоминание\n"
        "🌙 21:00 — вечерняя проверка\n\n"
        "<b>Кнопки меню:</b>\n"
        "📋 Мои задачи — задачи на сегодня\n"
        "📅 Календарь — просмотр по датам\n"
        "📊 Статистика — продуктивность\n"
        "📤 Экспорт — выгрузка в файл\n"
        "🌐 Веб-интерфейс — просмотр в браузере\n"
        "❌ Удалить задачу — удаление\n"
        "⚙️ Настройки — время утра/вечера\n"
        "⚙️ Помощь — это сообщение\n\n"
        "<i>Есть вопросы? Пишите моему создателю @Anton_Sergeevich_7!</i>"
    )
    await message.answer(help_text, parse_mode="HTML")