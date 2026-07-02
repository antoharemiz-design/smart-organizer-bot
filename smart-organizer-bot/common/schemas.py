from datetime import date, datetime, time as datetime_time
from typing import Optional, Literal
from pydantic import BaseModel, field_validator


class TaskDraft(BaseModel):
    """Черновик задачи, извлечённый из NLU."""
    title: Optional[str] = None
    due_date: Optional[date] = None
    event_time: Optional[datetime_time] = None
    is_all_day: bool = False
    recurrence: Optional[Literal["daily", "weekly", "monthly", "yearly"]] = None
    reminder_minutes_before: Optional[int] = None
    notes: Optional[str] = None

    @field_validator('event_time', mode='before')
    @classmethod
    def parse_event_time(cls, value):
        """Позволяет передавать время как строку 'HH:MM' или как объект datetime.time."""
        if value is None:
            return None
        if isinstance(value, datetime_time):
            return value
        if isinstance(value, str):
            try:
                parts = value.strip().split(':')
                if len(parts) == 2:
                    return datetime_time(int(parts[0]), int(parts[1]))
            except ValueError:
                pass
        raise ValueError(f'Cannot parse event_time: {value}')


class IntentResult(BaseModel):
    intent: Literal["task", "question", "chitchat"]
    task_draft: Optional[TaskDraft] = None
    raw_response: Optional[str] = None