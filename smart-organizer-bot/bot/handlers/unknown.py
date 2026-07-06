from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message()
async def handle_unknown(message: Message):
    """Обработка неизвестных сообщений."""
    await message.answer(
        "🤔 <b>Я вас не понял.</b>\n\n"
        "Попробуйте:\n"
        "• Написать задачу: «Купить хлеб завтра»\n"
        "• Использовать кнопки меню\n"
        "• Написать задачу текстом\n\n"
        "<i>Нужна помощь? Нажмите ⚙️ Помощь</i>",
        parse_mode="HTML"
    )