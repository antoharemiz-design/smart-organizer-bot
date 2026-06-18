import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TELEGRAM_BOT_TOKEN
from handlers.recipe import router
from database.db import init_db

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())