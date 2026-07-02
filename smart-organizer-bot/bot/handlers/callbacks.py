import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from calendar_core.local_calendar import LocalCalendarService

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("task_done:"))
async def handle_task_done(callback: CallbackQuery, calendar_service: LocalCalendarService):
    task_id = int(callback.data.split(":")[1])
    try:
        await calendar_service.mark_completed(task_id)
        await callback.message.edit_text(f"{callback.message.text}\n\n✅ <b>Задача выполнена!</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to mark task {task_id} as done: {e}")
        await callback.answer("Ошибка при отметке задачи")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("task_move:"))
async def handle_task_move(callback: CallbackQuery, calendar_service: LocalCalendarService):
    task_id = int(callback.data.split(":")[1])
    try:
        # Получаем задачу и переносим на завтра
        user_id = str(callback.from_user.id)
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Получаем текущую задачу
        tasks = await calendar_service.get_tasks(user_id, today)
        task_data = next((t for t in tasks if t.get("id") == task_id), None)

        if task_data:
            # Создаём копию на завтра
            from common.schemas import TaskDraft
            from datetime import time as dt_time

            task = TaskDraft(
                title=task_data.get("title"),
                due_date=tomorrow,
                event_time=dt_time.fromisoformat(task_data["event_time"]) if task_data.get("event_time") else None,
                is_all_day=bool(task_data.get("is_all_day", 0)),
                notes=task_data.get("notes")
            )
            await calendar_service.add_task(user_id, task)
            # Отмечаем старую как выполненную
            await calendar_service.mark_completed(task_id)

            await callback.message.edit_text(
                f"{callback.message.text}\n\n🔄 <b>Задача перенесена на завтра ({tomorrow.strftime('%d.%m.%Y')})</b>",
                parse_mode="HTML"
            )
        else:
            await callback.answer("Задача не найдена")
    except Exception as e:
        logger.error(f"Failed to move task {task_id}: {e}")
        await callback.answer("Ошибка при переносе задачи")
    finally:
        await callback.answer()

@router.callback_query(F.data.startswith("task_delete:"))
async def handle_task_delete(callback: CallbackQuery, calendar_service: LocalCalendarService):
    task_id = int(callback.data.split(":")[1])
    try:
        await calendar_service.delete_task(task_id)
        await callback.message.edit_text(
            f"{callback.message.text}\n\n🗑 <b>Задача удалена!</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        await callback.answer("Ошибка при удалении задачи")
    finally:
        await callback.answer()