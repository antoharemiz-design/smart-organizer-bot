"""
Модуль контекстной адаптации.
Анализирует привычки пользователя и предлагает оптимальное время для задач.
"""
import logging
from datetime import datetime, time
from typing import Optional
import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "data/organizer.db"


class HabitTracker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Создаёт таблицу для хранения привычек."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    task_keyword TEXT NOT NULL,
                    preferred_time TEXT,
                    preferred_day TEXT,
                    frequency INTEGER DEFAULT 0,
                    last_used TEXT
                )
            """)
            await db.commit()
        logger.info("Habit tracker initialized")

    async def track_task(self, user_id: str, task_title: str, task_time: Optional[time], task_date: Optional[datetime]):
        """Записывает задачу в историю для анализа привычек."""
        if not task_title:
            return

        # Извлекаем ключевые слова из названия задачи
        keywords = task_title.lower().split()
        main_keyword = keywords[0] if keywords else task_title.lower()

        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, есть ли уже такая привычка
            cursor = await db.execute(
                "SELECT id, frequency FROM user_habits WHERE user_id = ? AND task_keyword = ?",
                (user_id, main_keyword)
            )
            row = await cursor.fetchone()

            if row:
                # Обновляем частоту
                await db.execute(
                    "UPDATE user_habits SET frequency = frequency + 1, last_used = ? WHERE id = ?",
                    (datetime.now().isoformat(), row[0])
                )
            else:
                # Создаём новую запись
                day_name = task_date.strftime("%A") if task_date else None
                await db.execute(
                    """INSERT INTO user_habits 
                    (user_id, task_keyword, preferred_time, preferred_day, frequency, last_used)
                    VALUES (?, ?, ?, ?, 1, ?)""",
                    (
                        user_id,
                        main_keyword,
                        task_time.strftime("%H:%M") if task_time else None,
                        day_name,
                        datetime.now().isoformat()
                    )
                )
            await db.commit()

    async def get_suggestion(self, user_id: str, task_title: str) -> Optional[str]:
        """Предлагает оптимальное время на основе прошлых задач."""
        if not task_title:
            return None

        keywords = task_title.lower().split()
        main_keyword = keywords[0] if keywords else task_title.lower()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT preferred_time, preferred_day, frequency 
                FROM user_habits 
                WHERE user_id = ? AND task_keyword = ? AND frequency >= 2
                ORDER BY frequency DESC LIMIT 1""",
                (user_id, main_keyword)
            )
            row = await cursor.fetchone()

            if row:
                time_str = row[0]
                day_str = row[1]
                freq = row[2]

                suggestion = f"Вы часто создаёте эту задачу"
                if time_str:
                    suggestion += f" на {time_str}"
                if day_str:
                    suggestion += f" в {day_str}"
                return suggestion
            return None