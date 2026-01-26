"""
Вспомогательные функции для работы с ботом
"""
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)

async def safe_callback_answer(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """Безопасный ответ на callback query с обработкой ошибок"""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        error_str = str(e).lower()
        # Игнорируем ошибки "query is too old" и "query id is invalid" - это нормально для старых запросов
        if any(keyword in error_str for keyword in ["too old", "timeout", "invalid", "query id"]):
            logger.debug(f"Ignoring old/invalid callback query: {e}")
        else:
            logger.warning(f"Error answering callback: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error answering callback: {e}")

