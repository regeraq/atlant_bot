"""
Инициализация бота и диспетчера
"""
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import BOT_TOKEN

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Создает экземпляр бота"""
    return Bot(token=BOT_TOKEN)


def create_dispatcher() -> Dispatcher:
    """Создает диспетчер с хранилищем состояний"""
    storage = MemoryStorage()
    return Dispatcher(storage=storage)






