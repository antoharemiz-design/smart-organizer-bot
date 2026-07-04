"""
Веб-интерфейс для просмотра задач.
"""
from flask import Flask, render_template_string
import aiosqlite
import asyncio
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_PATH = "data/organizer.db"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Умный Органайзер</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .task { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .task-title { font-size: 18px; font-weight: bold; color: #333; }
        .task-time { color: #666; font-size: 14px; }
        .completed { text-decoration: line-through; opacity: 0.5; }
        .footer { text-align: center; margin-top: 30px; color: #999; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Умный Органайзер</h1>
        <p>Ваши задачи</p>
    </div>
    {% if tasks %}
        {% for task in tasks %}
        <div class="task {% if task.completed %}completed{% endif %}">
            <div class="task-title">{{ task.title }}</div>
            <div class="task-time">
                📅 {{ task.due_date }}
                {% if task.event_time %}⏰ {{ task.event_time }}{% endif %}
                {% if task.completed %}✅ Выполнено{% endif %}
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="task" style="text-align:center;">
            <p>📭 Нет задач</p>
        </div>
    {% endif %}
    <div class="footer">
        <p>Бот в Telegram: <a href="https://t.me/UmniyOrganaizerBot">@UmniyOrganaizerBot</a></p>
    </div>
</body>
</html>
"""


async def get_tasks():
    """Получает все задачи из БД."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks ORDER BY due_date, event_time"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@app.route("/")
def index():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = loop.run_until_complete(get_tasks())
    return render_template_string(HTML_TEMPLATE, tasks=tasks)


def run_web_server():
    app.run(host="0.0.0.0", port=8080)