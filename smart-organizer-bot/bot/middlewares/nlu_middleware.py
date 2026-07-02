from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from nlu.service import parse_message


class NLUMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Применяем только к текстовым сообщениям
        if event.text:
            # Вызываем NLU
            nlu_result = await parse_message(event.text)
            data["nlu_result"] = nlu_result
        return await handler(event, data)