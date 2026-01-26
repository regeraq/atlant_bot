"""
Repository для работы с пользователями
"""
from typing import List, Optional, Dict, Any
from bot.database.db_pool import db_pool
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository для работы с пользователями"""
    
    async def create(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str]
    ) -> bool:
        """Создает нового пользователя"""
        try:
            await db_pool.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                (telegram_id, username, first_name)
            )
            await db_pool.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            return False
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """Получает всех пользователей"""
        try:
            return await db_pool.execute_fetchall("SELECT * FROM users ORDER BY created_at DESC")
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return []
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по Telegram ID"""
        try:
            return await db_pool.execute_fetchone(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None






