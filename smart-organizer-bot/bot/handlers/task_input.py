import logging
from datetime import datetime, date as date_type, timedelta
from aiogram import Router, F, Dispatcher
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from nlu.service import parse_message
from common.schemas import TaskDraft
from adaptation.habit_tracker import HabitTracker

router = Router()
logger = logging.getLogger(__name__)

habit_tracker = HabitTracker()


class TaskCreation(StatesGroup):
    waiting_for_date = State()


async def confirm_and_create(message: Message, state: FSMContext, task: TaskDraft, calendar_service):
    user_id = str(message.from_user.id)
    try:
        await calendar_service.add_task(user_id, task)
        await habit_tracker.track_task(user_id, task.title, task.event_time, task.due_date)
        time_str = task.event_time.strftime("%H:%M") if task.event_time else "не указано"
        response = (
                f"✅ <b>Задача сохранена:</b>\n"
                f"• {task.title}\n"
                f"• Дата: {task.due_date}\n"
                f"• Время: {time_str}\n"
                + ("• За весь день\n" if task.is_all_day else "")
        )

        # Проверяем привычки в фоне, но не показываем сразу
        suggestion = await habit_tracker.get_suggestion(user_id, task.title)
        if suggestion:
            response += f"\n<i>💡 {suggestion}</i>"

        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to add task: {e}")
        await message.answer("❌ Не удалось сохранить задачу. Попробуйте позже.")
    await state.clear()


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text_input(message: Message, state: FSMContext, calendar_service):
    nlu_result = await parse_message(message.text)

    if nlu_result is None:
        await message.answer("Не удалось обработать сообщение. Попробуйте ещё раз.")
        return

    if nlu_result.intent == "task" and nlu_result.task_draft:
        task = nlu_result.task_draft

        # Если заголовок не распознан — используем исходный текст
        if not task.title:
            task.title = message.text.strip()[:100]

        # Если дата не указана — спрашиваем
        if not task.due_date:
            await state.update_data(task_draft=task)
            await message.answer(
                "📅 На какую дату задачу?\n"
                "<i>Например: завтра, в пятницу, 05.07.2026</i>",
                parse_mode="HTML"
            )
            await state.set_state(TaskCreation.waiting_for_date)
            return

        # Всё есть — создаём
        await confirm_and_create(message, state, task, calendar_service)
        return
    elif nlu_result.intent == "question":
        await message.answer("Я пока не умею отвечать на вопросы, но скоро научусь!")
    else:
        await message.answer(
            "🤔 Я вас не понял. Попробуйте:\n"
            "• «Позвонить врачу завтра в 10»\n"
            "• «Купить продукты в пятницу»\n"
            "• «Пойти на работу к 7 вечера»"
        )


@router.message(TaskCreation.waiting_for_date)
async def process_date(message: Message, state: FSMContext, calendar_service):
    data = await state.get_data()
    task: TaskDraft = data["task_draft"]

    user_answer = message.text.strip()

    # Пробуем извлечь дату из ответа
    nlu_result = await parse_message(user_answer)

    if nlu_result and nlu_result.task_draft and nlu_result.task_draft.due_date:
        task.due_date = nlu_result.task_draft.due_date
        if nlu_result.task_draft.event_time and not task.event_time:
            task.event_time = nlu_result.task_draft.event_time
        await state.update_data(task_draft=task)
        await confirm_and_create(message, state, task, calendar_service)
        return

    # Простой парсинг даты
    today = date_type.today()
    answer_lower = user_answer.lower()

    if "завтра" in answer_lower:
        task.due_date = today + timedelta(days=1)
    elif "сегодня" in answer_lower:
        task.due_date = today
    elif "послезавтра" in answer_lower:
        task.due_date = today + timedelta(days=2)
    else:
        days = {
            "понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3,
            "пятница": 4, "суббота": 5, "воскресенье": 6
        }
        found = False
        for day_name, day_idx in days.items():
            if day_name in answer_lower:
                today_idx = today.weekday()
                diff = (day_idx - today_idx) % 7
                if diff == 0:
                    diff = 7
                task.due_date = today + timedelta(days=diff)
                found = True
                break

        if not found:
            await message.answer(
                "Не удалось понять дату. Попробуйте:\n"
                "• завтра\n"
                "• в пятницу\n"
                "• 05.07.2026"
            )
            return

    await state.update_data(task_draft=task)
    await confirm_and_create(message, state, task, calendar_service)