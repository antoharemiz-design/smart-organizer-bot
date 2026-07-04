"""
Проверка подписки на Telegram-канал.
"""
import logging
from aiogram import Bot
from aiogram.types import ChatMemberMember, ChatMemberAdministrator, ChatMemberOwner

logger = logging.getLogger(__name__)

CHANNEL_ID = "@architectkulees"
CHANNEL_URL = "https://t.me/architectkulees"


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал."""
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return isinstance(member, (ChatMemberMember, ChatMemberAdministrator, ChatMemberOwner))
    except Exception as e:
        logger.error(f"Failed to check subscription: {e}")
        return False


async def get_subscription_text(bot: Bot, user_id: int) -> str:
    """Возвращает текст с просьбой подписаться, если пользователь не подписан."""
    is_subscribed = await check_subscription(bot, user_id)
    if not is_subscribed:
        return (
            f"⚠️ <b>Для использования бота подпишитесь на канал:</b>\n"
            f"{CHANNEL_URL}\n\n"
            f"После подписки нажмите /start"
        )
    return ""