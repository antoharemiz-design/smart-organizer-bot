"""
Локальное календарное ядро на SQLite.
Хранит задачи с датами, временем, рекурренцией, напоминаниями.
"""
import logging
import aiosqlite
from datetime import date, datetime, time, timedelta
from typing import Optional, List, Dict

from common.schemas import TaskDraft

logger = logging.getLogger(__name__)

DB_PATH = "data/organizer.db"


class LocalCalendarService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Создание таблиц при первом запуске."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    due_date TEXT,
                    event_time TEXT,
                    is_all_day INTEGER DEFAULT 0,
                    recurrence TEXT,
                    reminder_minutes_before INTEGER,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    completed INTEGER DEFAULT 0
                )
            """)
            await db.commit()
        logger.info("Local calendar database initialized")

    async def add_task(self, user_id: str, task: TaskDraft) -> int:
        """Добавляет задачу в БД, если такой ещё нет. Возвращает ID."""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем дубликат: та же дата + время + название
            cursor = await db.execute(
                """SELECT id FROM tasks 
                WHERE user_id = ? 
                AND title = ? 
                AND due_date = ? 
                AND event_time = ? 
                AND completed = 0""",
                (
                    user_id,
                    task.title,
                    task.due_date.isoformat() if task.due_date else None,
                    task.event_time.strftime("%H:%M") if task.event_time else None,
                )
            )
            existing = await cursor.fetchone()

            if existing:
                logger.info(f"Duplicate task skipped: {task.title} for user {user_id}")
                return existing[0]  # Возвращаем ID существующей задачи

            cursor = await db.execute(
                """INSERT INTO tasks 
                (user_id, title, due_date, event_time, is_all_day, recurrence, reminder_minutes_before, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    task.title,
                    task.due_date.isoformat() if task.due_date else None,
                    task.event_time.strftime("%H:%M") if task.event_time else None,
                    1 if task.is_all_day else 0,
                    task.recurrence,
                    task.reminder_minutes_before,
                    task.notes,
                )
            )
            await db.commit()
            task_id = cursor.lastrowid
            logger.info(f"Task added for user {user_id}: {task.title} (ID: {task_id})")
            return task_id

    async def reset_user_tasks(self, user_id: str):
        """Удаляет все задачи пользователя (сброс статистики)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
            await db.commit()
        logger.info(f"All tasks reset for user {user_id}")

    async def initialize(self):
        """Создание таблиц при старте."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    due_date TEXT,
                    event_time TEXT,
                    is_all_day INTEGER DEFAULT 0,
                    recurrence TEXT,
                    reminder_minutes_before INTEGER,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    completed INTEGER DEFAULT 0
                )
            """)
            # Таблица настроек пользователя
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    morning_time TEXT DEFAULT '08:00',
                    evening_time TEXT DEFAULT '21:00',
                    timezone TEXT DEFAULT 'Europe/Moscow'
                )
            """)
            await db.commit()
        logger.info("Local calendar database initialized")

    async def get_user_settings(self, user_id: str) -> dict:
        """Получает настройки пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            # Настройки по умолчанию
            return {"morning_time": "08:00", "evening_time": "21:00", "timezone": "Europe/Moscow"}

    async def save_user_settings(self, user_id: str, morning_time: str = None, evening_time: str = None,
                                 timezone: str = None):
        """Сохраняет настройки пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем текущие настройки
            current = await self.get_user_settings(user_id)

            # Обновляем только переданные значения
            morning = morning_time or current.get("morning_time", "08:00")
            evening = evening_time or current.get("evening_time", "21:00")
            tz = timezone or current.get("timezone", "Europe/Moscow")

            await db.execute(
                """INSERT INTO user_settings (user_id, morning_time, evening_time, timezone) 
                VALUES (?, ?, ?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET 
                morning_time = excluded.morning_time,
                evening_time = excluded.evening_time,
                timezone = excluded.timezone""",
                (user_id, morning, evening, tz)
            )
            await db.commit()
        logger.info(f"Settings saved for user {user_id}: morning={morning}, evening={evening}")

    async def get_tasks(self, user_id: str, date_filter: Optional[date] = None) -> List[Dict]:
        """Возвращает задачи пользователя, опционально на конкретную дату."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if date_filter:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE user_id = ? AND due_date = ? AND completed = 0",
                    (user_id, date_filter.isoformat())
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY due_date",
                    (user_id,)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_completed(self, task_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
            await db.commit()

    async def delete_task(self, task_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()