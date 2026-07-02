from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from calendar_core.local_calendar import LocalCalendarService
from datetime import date, timedelta
import aiosqlite

router = Router()

DB_PATH = "data/organizer.db"


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message, calendar_service: LocalCalendarService):
    """Показывает статистику пользователя с кнопкой сброса."""
    user_id = str(message.from_user.id)

    async with aiosqlite.connect(DB_PATH) as db:
        # Всего задач
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
            (user_id,)
        )
        total_tasks = (await cursor.fetchone())[0]

        # Выполнено
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1",
            (user_id,)
        )
        completed = (await cursor.fetchone())[0]

        # За сегодня
        today = date.today()
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date = ?",
            (user_id, today.isoformat())
        )
        today_tasks = (await cursor.fetchone())[0]

        # За неделю
        week_start = today - timedelta(days=today.weekday())
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date >= ? AND due_date <= ?",
            (user_id, week_start.isoformat(), today.isoformat())
        )
        week_tasks = (await cursor.fetchone())[0]

        # Процент выполнения
        completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0

    stats_text = (
            f"📊 <b>Ваша статистика:</b>\n\n"
            f"📝 Всего задач: <b>{total_tasks}</b>\n"
            f"✅ Выполнено: <b>{completed}</b> ({completion_rate:.1f}%)\n"
            f"📅 За сегодня: <b>{today_tasks}</b>\n"
            f"📆 За неделю: <b>{week_tasks}</b>\n\n"
            f"🔥 <b>Продуктивность:</b> "
            + ("Отлично! Так держать!" if completion_rate > 70
               else "Хорошо! Есть куда расти." if completion_rate > 40
    else "Пора браться за дела!")
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Сбросить статистику", callback_data="reset_stats")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_stats")]
    ])

    await message.answer(stats_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "reset_stats")
async def process_reset_stats(callback: CallbackQuery, calendar_service: LocalCalendarService):
    user_id = str(callback.from_user.id)
    await calendar_service.reset_user_tasks(user_id)
    await callback.message.edit_text(
        "✅ <b>Статистика сброшена!</b>\nВсе задачи удалены.",
        parse_mode="HTML"
    )
    await callback.answer("Статистика сброшена")


@router.callback_query(F.data == "cancel_stats")
async def process_cancel_stats(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Отменено")