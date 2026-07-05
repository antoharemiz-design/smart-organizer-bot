from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Мои задачи"),
                KeyboardButton(text="📅 Календарь")
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="📤 Экспорт")
            ],
            [
                KeyboardButton(text="🌐 Веб-интерфейс"),
                KeyboardButton(text="❌ Удалить задачу")
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="⚙️ Помощь")
            ],
            [
                KeyboardButton(text="🕐 Время")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите задачу или выберите действие ✍️"
    )


def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"task_done:{task_id}"),
            InlineKeyboardButton(text="🔄 Перенести", callback_data=f"task_move:{task_id}")
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task_delete:{task_id}")
        ]
    ])