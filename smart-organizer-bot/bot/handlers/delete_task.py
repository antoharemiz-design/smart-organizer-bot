from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, timedelta

router = Router()


class DeleteTask(StatesGroup):
    waiting_for_confirmation = State()


@router.message(F.text == "❌ Удалить задачу")
async def menu_delete_task(message: Message, calendar_service, state: FSMContext):
    """Показывает список задач для удаления."""
    user_id = str(message.from_user.id)
    today = date.today()
    week_end = today + timedelta(days=7)

    # Получаем задачи на ближайшую неделю
    tasks = []
    current_date = today
    while current_date <= week_end:
        day_tasks = await calendar_service.get_tasks(user_id, current_date)
        for task in day_tasks:
            task["_date"] = current_date.isoformat()
        tasks.extend(day_tasks)
        current_date += timedelta(days=1)

    if not tasks:
        await message.answer("📭 Нет задач для удаления.")
        return

    # Показываем список с кнопками удаления
    lines = ["🗑 <b>Выберите задачу для удаления:</b>\n"]
    keyboard_buttons = []

    for i, task in enumerate(tasks[:10], 1):  # Максимум 10 задач
        title = task.get("title", "Без названия")
        date_str = task.get("_date", "")
        time_str = task.get("event_time", "")

        line = f"{i}. {title}"
        if date_str:
            line += f" ({date_str})"
        if time_str:
            line += f" в {time_str}"
        lines.append(line)

        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"❌ {i}. {title[:30]}",
                callback_data=f"task_delete:{task['id']}"
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Отмена", callback_data="task_delete:cancel")
    ])

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("task_delete:"))
async def process_delete(callback: CallbackQuery, calendar_service):
    task_id = callback.data.split(":")[1]

    if task_id == "cancel":
        await callback.message.delete()
        await callback.answer("Удаление отменено")
        return

    try:
        await calendar_service.delete_task(int(task_id))
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>Задача удалена!</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.answer("Ошибка при удалении задачи")
    finally:
        await callback.answer()