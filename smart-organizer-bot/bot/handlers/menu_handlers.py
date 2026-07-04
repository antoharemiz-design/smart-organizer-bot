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

@router.message(F.text == "⚙️ Помощь")
async def menu_help(message: Message):
    """Обработчик кнопки 'Помощь'."""
    help_text = (
        "🤖 <b>Умный Органайзер</b>\n\n"
        "<b>Как создавать задачи:</b>\n"
        "• Текст: напишите «Позвонить врачу завтра в 10»\n"
        "• Голос: отправьте голосовое сообщение\n\n"
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
        "📤 Экспорт — выгрузка в файл\n"
        "⚙️ Помощь — это сообщение\n\n"
        "<i>Есть вопросы? Пишите моему создателю @Anton_Sergeevich_7!</i>"
    )

    @router.message(F.text == "🌐 Веб-интерфейс")
    async def menu_web(message: Message):
        """Обработчик кнопки 'Веб-интерфейс'."""
        await message.answer(
            "🌐 <b>Веб-интерфейс ваших задач:</b>\n\n"
            "https://smart-organizer-bot.onrender.com\n\n"
            "<i>Откройте в браузере для просмотра всех задач.</i>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    await message.answer(help_text, parse_mode="HTML")