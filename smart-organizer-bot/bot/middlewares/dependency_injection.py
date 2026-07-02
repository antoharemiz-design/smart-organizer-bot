from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class DIMiddleware(BaseMiddleware):
    def __init__(self, calendar_service, scheduler=None):
        self.calendar_service = calendar_service
        self.scheduler = scheduler
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["calendar_service"] = self.calendar_service
        if self.scheduler:
            data["scheduler"] = self.scheduler
        return await handler(event, data)