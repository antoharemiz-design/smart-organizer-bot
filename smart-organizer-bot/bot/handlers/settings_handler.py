from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from calendar_core.local_calendar import LocalCalendarService

router = Router()


class SettingsState(StatesGroup):
    waiting_for_morning = State()
    waiting_for_evening = State()


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, calendar_service: LocalCalendarService):
    """Показывает настройки пользователя."""
    user_id = str(message.from_user.id)
    settings = await calendar_service.get_user_settings(user_id)

    text = (
        f"⚙️ <b>Ваши настройки:</b>\n\n"
        f"🌅 Утреннее приветствие: <b>{settings['morning_time']}</b>\n"
        f"🌙 Вечерний опрос: <b>{settings['evening_time']}</b>\n"
        f"🕐 Часовой пояс: <b>{settings['timezone']}</b>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 Изменить утро", callback_data="set_morning"),
            InlineKeyboardButton(text="🌙 Изменить вечер", callback_data="set_evening"),
        ]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "set_morning")
async def set_morning(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🌅 Введите время утреннего приветствия (например, 07:00 или 09:00):"
    )
    await state.set_state(SettingsState.waiting_for_morning)
    await callback.answer()


@router.callback_query(F.data == "set_evening")
async def set_evening(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🌙 Введите время вечернего опроса (например, 20:00 или 22:00):"
    )
    await state.set_state(SettingsState.waiting_for_evening)
    await callback.answer()


@router.message(SettingsState.waiting_for_morning)
async def process_morning_time(message: Message, state: FSMContext, calendar_service: LocalCalendarService):
    time_str = message.text.strip()
    # Простая валидация
    if ":" in time_str and len(time_str) == 5:
        user_id = str(message.from_user.id)
        await calendar_service.save_user_settings(user_id, morning_time=time_str)
        await message.answer(f"✅ Утреннее приветствие установлено на <b>{time_str}</b>", parse_mode="HTML")
        await state.clear()
    else:
        await message.answer("❌ Неверный формат. Введите время в формате ЧЧ:ММ (например, 07:00):")


@router.message(SettingsState.waiting_for_evening)
async def process_evening_time(message: Message, state: FSMContext, calendar_service: LocalCalendarService):
    time_str = message.text.strip()
    if ":" in time_str and len(time_str) == 5:
        user_id = str(message.from_user.id)
        await calendar_service.save_user_settings(user_id, evening_time=time_str)
        await message.answer(f"✅ Вечерний опрос установлен на <b>{time_str}</b>", parse_mode="HTML")
        await state.clear()
    else:
        await message.answer("❌ Неверный формат. Введите время в формате ЧЧ:ММ (например, 22:00):")