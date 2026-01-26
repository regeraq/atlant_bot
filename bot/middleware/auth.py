"""
Middleware для проверки прав администратора
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.database.database import is_admin


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверка прав администратора может быть добавлена здесь
        # Пока оставляем декоратор admin_required в handlers
        return await handler(event, data)






