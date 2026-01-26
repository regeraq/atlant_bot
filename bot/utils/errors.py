"""
Централизованная обработка ошибок
"""
import logging
from typing import Optional, Callable, Any
from functools import wraps
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError, TelegramForbiddenError
from bot.utils.helpers import safe_callback_answer

logger = logging.getLogger(__name__)


class BotError(Exception):
    """Базовое исключение для ошибок бота"""
    def __init__(self, message: str, user_message: Optional[str] = None):
        self.message = message
        self.user_message = user_message or message
        super().__init__(self.message)


class ValidationError(BotError):
    """Ошибка валидации данных"""
    pass


class DatabaseError(BotError):
    """Ошибка работы с базой данных"""
    pass


class NotFoundError(BotError):
    """Ошибка - объект не найден"""
    pass


def error_handler(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в handlers
    
    Usage:
        @error_handler
        async def my_handler(message: Message):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            # Определяем тип первого аргумента
            if args and isinstance(args[0], (Message, CallbackQuery)):
                obj = args[0]
                if isinstance(obj, CallbackQuery):
                    await safe_callback_answer(obj, e.user_message, show_alert=True)
                else:
                    await obj.answer(f"❌ {e.user_message}")
            return None
        except NotFoundError as e:
            logger.warning(f"Not found error in {func.__name__}: {e.message}")
            if args and isinstance(args[0], (Message, CallbackQuery)):
                obj = args[0]
                if isinstance(obj, CallbackQuery):
                    await safe_callback_answer(obj, e.user_message, show_alert=True)
                else:
                    await obj.answer(f"❌ {e.user_message}")
            return None
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e.message}")
            if args and isinstance(args[0], (Message, CallbackQuery)):
                obj = args[0]
                if isinstance(obj, CallbackQuery):
                    await safe_callback_answer(
                        obj,
                        "❌ Ошибка работы с базой данных. Попробуйте позже.",
                        show_alert=True
                    )
                else:
                    await obj.answer("❌ Ошибка работы с базой данных. Попробуйте позже.")
            return None
        except TelegramBadRequest as e:
            logger.warning(f"Telegram API error in {func.__name__}: {e}")
            # Игнорируем некоторые ошибки Telegram API
            return None
        except TelegramForbiddenError as e:
            logger.warning(f"User blocked bot in {func.__name__}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            if args and isinstance(args[0], (Message, CallbackQuery)):
                obj = args[0]
                if isinstance(obj, CallbackQuery):
                    await safe_callback_answer(
                        obj,
                        "❌ Произошла ошибка. Попробуйте позже.",
                        show_alert=True
                    )
                else:
                    await obj.answer("❌ Произошла ошибка. Попробуйте позже.")
            return None
    
    return wrapper






