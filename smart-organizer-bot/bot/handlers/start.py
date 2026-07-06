from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.keyboards.main_menu import get_main_keyboard
from common.channel_check import check_subscription

router = Router()

CHANNEL_URL = "https://t.me/architectkulees"
SHARE_URL = "https://t.me/share/url?url=https://t.me/UmniyOrganaizerBot&text=🤖%20Умный%20органайзер%20с%20AI%20—%20попробуй!"

WELCOME_IMAGE_URL = "https://img.freepik.com/free-vector/organizer-concept-illustration_114360-5229.jpg"


class Onboarding(StatesGroup):
    waiting_for_name = State()
    waiting_for_timezone = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие с проверкой подписки."""

    # Проверяем подписку
    is_subscribed = await check_subscription(message.bot, message.from_user.id)

    if not is_subscribed:
        # Просим подписаться
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
        ])

        await message.answer_photo(
            photo=URLInputFile(WELCOME_IMAGE_URL),
            caption=(
                f"👋 <b>Здравствуйте, {message.from_user.first_name}!</b>\n\n"
                f"Я — <b>Умный Органайзер</b> с искусственным интеллектом.\n\n"
                f"⚠️ <b>Для использования бота подпишитесь на канал:</b>\n"
                f"{CHANNEL_URL}\n\n"
                f"После подписки нажмите кнопку «Проверить подписку»"
            ),
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # Подписан — показываем приветствие
    await show_welcome(message, state)


@router.callback_query(lambda c: c.data == "check_sub")
async def check_sub(callback, state: FSMContext):
    """Повторная проверка подписки."""
    is_subscribed = await check_subscription(callback.bot, callback.from_user.id)

    if is_subscribed:
        await callback.message.delete()
        await show_welcome(callback.message, state)
    else:
        await callback.answer("❌ Вы ещё не подписались на канал!", show_alert=True)


async def show_welcome(message: Message, state: FSMContext):
    """Показывает приветствие и начинает онбординг."""
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
        f"Для точных напоминаний мне нужно знать ваш часовой пояс.\n\n"
        f"<b>Выберите и введите свой город:</b>\n"
        f"• Калининград — <code>Europe/Kaliningrad</code>\n"
        f"• Москва, Краснодар, Казань — <code>Europe/Moscow</code>\n"
        f"• Самара, Ижевск — <code>Europe/Samara</code>\n"
        f"• Екатеринбург, Челябинск — <code>Asia/Yekaterinburg</code>\n"
        f"• Омск — <code>Asia/Omsk</code>\n"
        f"• Красноярск — <code>Asia/Krasnoyarsk</code>\n"
        f"• Иркутск — <code>Asia/Irkutsk</code>\n"
        f"• Владивосток, Хабаровск — <code>Asia/Vladivostok</code>\n\n"
        f"<i>Просто напишите код в ответ (например: Europe/Moscow)</i>",
        parse_mode="HTML"
    )
    await state.set_state(Onboarding.waiting_for_timezone)


@router.message(Onboarding.waiting_for_timezone)
async def process_timezone(message: Message, state: FSMContext, calendar_service, scheduler):
    timezone = message.text.strip()
    await state.update_data(timezone=timezone)
    user_data = await state.get_data()
    name = user_data['name']

    if scheduler:
        scheduler.set_user_timezone(str(message.from_user.id), timezone)

    # Кнопка «Поделиться»
    share_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Поделиться с друзьями", url=SHARE_URL)]
    ])

    final_text = (
        f"🎉 <b>Отлично, {name}! Всё готово!</b>\n\n"
        f"⏰ Часовой пояс: <b>{timezone}</b>\n\n"
        f"📝 <b>Как создавать задачи:</b>\n"
        f"• Текст: «Позвонить врачу завтра в 10»\n"
        f"• Текст: просто напишите что и когда\n\n"
        f"🔔 <b>Я буду:</b>\n"
        f"• Присылать план на день в 8:00\n"
        f"• Напоминать точно в указанное время\n"
        f"• Спрашивать о задачах вечером в 21:00\n\n"
        f"👇 Используйте кнопки меню или просто напишите задачу!"
    )

    await message.answer(
        final_text,
        parse_mode="HTML",
        reply_markup=share_keyboard
    )
    await state.clear()