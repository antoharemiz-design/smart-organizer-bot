from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, URLInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.keyboards.main_menu import get_main_keyboard

router = Router()


class Onboarding(StatesGroup):
    waiting_for_name = State()
    waiting_for_timezone = State()


# URL красивой картинки для приветствия
WELCOME_IMAGE_URL = "https://img.freepik.com/free-vector/organizer-concept-illustration_114360-5229.jpg"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие с красивой картинкой и описанием."""

    welcome_text = (
        f"👋 <b>Здравствуйте, {message.from_user.first_name}!</b>\n\n"
        f"Я — <b>Умный Органайзер</b> с искусственным интеллектом.\n"
        f"Помогу вам управлять задачами и ничего не забыть.\n\n"
        f"✨ <b>Что я умею:</b>\n"
        f"• Понимать свободный текст и голос\n"
        f"• Создавать задачи с датой и временем\n"
        f"• Присылать утренние планы и напоминания\n"
        f"• Вечером спрашивать о результате\n"
        f"• Экспортировать задачи в календарь\n\n"
        f"🚀 <b>Как начать:</b>\n"
        f"Просто напишите задачу как другу:\n"
        f"«Позвонить врачу завтра в 10»\n\n"
        f"<i>Давайте познакомимся! Как вас зовут?</i>"
    )

    # Отправляем картинку по URL
    await message.answer_photo(
        photo=URLInputFile(WELCOME_IMAGE_URL),
        caption=welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

    await state.set_state(Onboarding.waiting_for_name)


@router.message(Onboarding.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)

    await message.answer(
        f"✨ <b>Приятно познакомиться, {name}!</b>\n\n"
        f"Для точных напоминаний мне нужно знать ваш часовой пояс.\n"
        f"<i>Например: Europe/Moscow, Asia/Yekaterinburg, Europe/Kaliningrad</i>",
        parse_mode="HTML"
    )
    await state.set_state(Onboarding.waiting_for_timezone)


@router.message(Onboarding.waiting_for_timezone)
async def process_timezone(message: Message, state: FSMContext, calendar_service, scheduler):
    timezone = message.text.strip()
    await state.update_data(timezone=timezone)
    user_data = await state.get_data()
    name = user_data['name']

    # Сохраняем timezone в планировщик
    if scheduler:
        scheduler.set_user_timezone(str(message.from_user.id), timezone)

    final_text = (
        f"🎉 <b>Отлично, {name}! Всё готово!</b>\n\n"
        f"⏰ Часовой пояс: <b>{timezone}</b>\n\n"
        f"📝 <b>Как создавать задачи:</b>\n"
        f"• Текст: «Позвонить врачу завтра в 10»\n"
        f"• Голос: просто скажите что и когда\n\n"
        f"🔔 <b>Я буду:</b>\n"
        f"• Присылать план на день в 8:00\n"
        f"• Напоминать точно в указанное время\n"
        f"• Спрашивать о задачах вечером в 21:00\n\n"
        f"👇 Используйте кнопки меню или просто напишите задачу!"
    )

    await message.answer(
        final_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await state.clear()