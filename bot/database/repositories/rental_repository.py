"""
Repository для работы с арендой
"""
from typing import List, Optional, Dict, Any
from bot.database.db_pool import db_pool
from bot.utils.cache import cache
import logging

logger = logging.getLogger(__name__)


class RentalRepository:
    """Repository для работы с арендой"""
    
    async def create(
        self,
        user_id: int,
        car_id: int,
        daily_price: int,
        reminder_time: str = "12:00",
        reminder_type: str = "daily"
    ) -> Optional[int]:
        """Создает новую аренду"""
        try:
            # Проверяем, нет ли уже активной аренды
            existing = await self.get_active_by_user(user_id)
            if existing:
                return None
            
            cursor = await db_pool.execute(
                """INSERT INTO rentals (user_id, car_id, daily_price, reminder_time, reminder_type) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, car_id, daily_price, reminder_time, reminder_type)
            )
            await db_pool.commit()
            
            # Очищаем кэш
            cache.delete(f"rental:user:{user_id}")
            cache.delete("rentals:active")
            
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании аренды: {e}")
            return None
    
    async def get_active_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает активную аренду пользователя"""
        try:
            cache_key = f"rental:user:{user_id}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await db_pool.execute_fetchone(
                """SELECT r.*, c.name as car_name, c.description as car_description, 
                          c.image_1, c.image_2, c.image_3
                   FROM rentals r
                   JOIN cars c ON r.car_id = c.id
                   WHERE r.user_id = ? AND r.is_active = 1
                   ORDER BY r.created_at DESC
                   LIMIT 1""",
                (user_id,)
            )
            
            if result:
                cache.set(cache_key, result, ttl=300)
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении аренды пользователя: {e}")
            return None
    
    async def get_all_active(self) -> List[Dict[str, Any]]:
        """Получает все активные аренды"""
        try:
            cache_key = "rentals:active"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await db_pool.execute_fetchall(
                """SELECT r.*, c.name as car_name, u.first_name, u.username
                   FROM rentals r
                   JOIN cars c ON r.car_id = c.id
                   JOIN users u ON r.user_id = u.telegram_id
                   WHERE r.is_active = 1
                   ORDER BY r.created_at DESC"""
            )
            
            cache.set(cache_key, result, ttl=60)
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении активных аренд: {e}")
            return []
    
    async def get_by_id(self, rental_id: int) -> Optional[Dict[str, Any]]:
        """Получает аренду по ID"""
        try:
            return await db_pool.execute_fetchone(
                """SELECT r.*, c.name as car_name, u.first_name, u.username
                   FROM rentals r
                   JOIN cars c ON r.car_id = c.id
                   JOIN users u ON r.user_id = u.telegram_id
                   WHERE r.id = ?""",
                (rental_id,)
            )
        except Exception as e:
            logger.error(f"Ошибка при получении аренды: {e}")
            return None
    
    async def end(self, rental_id: int) -> bool:
        """Завершает аренду"""
        try:
            await db_pool.execute(
                "UPDATE rentals SET is_active = 0 WHERE id = ?",
                (rental_id,)
            )
            await db_pool.commit()
            
            # Очищаем кэш
            cache.delete("rentals:active")
            rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
            if rental:
                cache.delete(f"rental:user:{rental['user_id']}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при завершении аренды: {e}")
            return False
    
    async def update_reminder_time(self, rental_id: int, reminder_time: str) -> bool:
        """Обновляет время напоминания"""
        try:
            await db_pool.execute(
                "UPDATE rentals SET reminder_time = ? WHERE id = ?",
                (reminder_time, rental_id)
            )
            await db_pool.commit()
            
            # Очищаем кэш
            rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
            if rental:
                cache.delete(f"rental:user:{rental['user_id']}")
            cache.delete("rentals:active")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени напоминания: {e}")
            return False
    
    async def update_reminder_type(self, rental_id: int, reminder_type: str) -> bool:
        """Обновляет тип напоминания"""
        try:
            await db_pool.execute(
                "UPDATE rentals SET reminder_type = ?, last_reminder_date = NULL WHERE id = ?",
                (reminder_type, rental_id)
            )
            await db_pool.commit()
            
            # Очищаем кэш
            rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
            if rental:
                cache.delete(f"rental:user:{rental['user_id']}")
            cache.delete("rentals:active")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении типа напоминания: {e}")
            return False






