"""
Repository для работы с автомобилями
"""
from typing import List, Optional, Dict, Any
from bot.database.db_pool import db_pool
from bot.utils.cache import cache
import logging

logger = logging.getLogger(__name__)


class CarRepository:
    """Repository для работы с автомобилями"""
    
    async def get_all(self, available_only: bool = False) -> List[Dict[str, Any]]:
        """Получает все автомобили"""
        try:
            cache_key = f"cars:all:{available_only}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            query = "SELECT * FROM cars"
            params = ()
            if available_only:
                query += " WHERE available = 1"
            query += " ORDER BY created_at DESC"
            
            result = await db_pool.execute_fetchall(query, params)
            # Кэшируем на 60 секунд
            cache.set(cache_key, result, ttl=60)
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении автомобилей: {e}")
            return []
    
    async def get_by_id(self, car_id: int) -> Optional[Dict[str, Any]]:
        """Получает автомобиль по ID"""
        try:
            cache_key = f"car:{car_id}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await db_pool.execute_fetchone("SELECT * FROM cars WHERE id = ?", (car_id,))
            if result:
                # Кэшируем на 120 секунд
                cache.set(cache_key, result, ttl=120)
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении автомобиля: {e}")
            return None
    
    async def create(
        self,
        name: str,
        description: Optional[str],
        daily_price: int,
        available: bool = True,
        image_1: Optional[str] = None,
        image_2: Optional[str] = None,
        image_3: Optional[str] = None
    ) -> Optional[int]:
        """Создает новый автомобиль"""
        try:
            cursor = await db_pool.execute(
                """INSERT INTO cars (name, description, daily_price, available, image_1, image_2, image_3) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, description, daily_price, available, image_1, image_2, image_3)
            )
            await db_pool.commit()
            
            # Очищаем кэш
            cache.delete("cars:all:True")
            cache.delete("cars:all:False")
            
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании автомобиля: {e}")
            return None
    
    async def update(
        self,
        car_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        daily_price: Optional[int] = None,
        available: Optional[bool] = None,
        image_1: Optional[str] = None,
        image_2: Optional[str] = None,
        image_3: Optional[str] = None
    ) -> bool:
        """Обновляет информацию об автомобиле"""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if daily_price is not None:
                updates.append("daily_price = ?")
                params.append(daily_price)
            if available is not None:
                updates.append("available = ?")
                params.append(available)
            if image_1 is not None:
                updates.append("image_1 = ?")
                params.append(image_1)
            if image_2 is not None:
                updates.append("image_2 = ?")
                params.append(image_2)
            if image_3 is not None:
                updates.append("image_3 = ?")
                params.append(image_3)
            
            if not updates:
                return True
            
            params.append(car_id)
            query = f"UPDATE cars SET {', '.join(updates)} WHERE id = ?"
            
            await db_pool.execute(query, tuple(params))
            await db_pool.commit()
            
            # Очищаем кэш
            cache.delete(f"car:{car_id}")
            cache.delete("cars:all:True")
            cache.delete("cars:all:False")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении автомобиля: {e}")
            return False
    
    async def delete(self, car_id: int) -> bool:
        """Удаляет автомобиль"""
        try:
            # Проверяем, существует ли автомобиль
            car = await self.get_by_id(car_id)
            if not car:
                logger.warning(f"Попытка удалить несуществующий автомобиль с ID: {car_id}")
                return False
            
            # Проверяем, есть ли активные аренды
            active_rentals = await db_pool.execute_fetchall(
                "SELECT id FROM rentals WHERE car_id = ? AND is_active = 1",
                (car_id,)
            )
            
            if active_rentals:
                logger.warning(f"Нельзя удалить автомобиль с ID {car_id}: есть {len(active_rentals)} активных аренд")
                return False
            
            # Удаляем все аренды этого автомобиля
            rentals_to_delete = await db_pool.execute_fetchall(
                "SELECT id, user_id FROM rentals WHERE car_id = ?",
                (car_id,)
            )
            
            if rentals_to_delete:
                # Очищаем кэш для пользователей
                for rental in rentals_to_delete:
                    cache.delete(f"rental:user:{rental['user_id']}")
                
                await db_pool.execute("DELETE FROM rentals WHERE car_id = ?", (car_id,))
                logger.info(f"Удалено {len(rentals_to_delete)} аренд для автомобиля с ID {car_id}")
            
            # Удаляем автомобиль
            cursor = await db_pool.execute("DELETE FROM cars WHERE id = ?", (car_id,))
            await db_pool.commit()
            
            if cursor.rowcount == 0:
                logger.warning(f"Автомобиль с ID {car_id} не был удален")
                return False
            
            # Очищаем кэш
            cache.delete(f"car:{car_id}")
            cache.delete("cars:all:True")
            cache.delete("cars:all:False")
            cache.delete("rentals:active")
            
            logger.info(f"Автомобиль с ID {car_id} успешно удален")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении автомобиля: {e}")
            return False






