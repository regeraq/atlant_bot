"""
Service для работы с автомобилями
Бизнес-логика для управления автомобилями
"""
from typing import List, Optional, Dict, Any
from bot.database.repositories.car_repository import CarRepository
from bot.models.car_models import CarCreate, CarUpdate, CarResponse
from bot.utils.errors import ValidationError, NotFoundError, DatabaseError
import logging

logger = logging.getLogger(__name__)


class CarService:
    """Service для работы с автомобилями"""
    
    def __init__(self, car_repository: CarRepository) -> None:
        """
        Инициализация сервиса
        
        Args:
            car_repository: Репозиторий для работы с автомобилями
        """
        self.car_repository = car_repository
    
    async def get_all_cars(self, available_only: bool = False) -> List[Dict[str, Any]]:
        """
        Получает все автомобили
        
        Args:
            available_only: Если True, возвращает только доступные автомобили
            
        Returns:
            Список словарей с информацией об автомобилях
        """
        try:
            return await self.car_repository.get_all(available_only=available_only)
        except Exception as e:
            logger.error(f"Ошибка при получении автомобилей: {e}")
            raise DatabaseError(f"Ошибка при получении автомобилей: {e}")
    
    async def get_car_by_id(self, car_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает автомобиль по ID
        
        Args:
            car_id: ID автомобиля
            
        Returns:
            Словарь с информацией об автомобиле или None, если не найден
        """
        if car_id <= 0:
            raise ValidationError("ID автомобиля должен быть положительным числом")
        
        try:
            car = await self.car_repository.get_by_id(car_id)
            return car
        except Exception as e:
            logger.error(f"Ошибка при получении автомобиля {car_id}: {e}")
            raise DatabaseError(f"Ошибка при получении автомобиля: {e}")
    
    async def create_car(self, car_data: CarCreate) -> Optional[int]:
        """
        Создает новый автомобиль с валидацией через Pydantic
        
        Args:
            car_data: Данные автомобиля для создания (валидируются через Pydantic)
            
        Returns:
            ID созданного автомобиля или None при ошибке
            
        Raises:
            ValidationError: При ошибках валидации данных
            DatabaseError: При ошибках работы с БД
        """
        try:
            # Валидация через Pydantic уже выполнена при создании CarCreate
            return await self.car_repository.create(
                name=car_data.name,
                description=car_data.description,
                daily_price=car_data.daily_price,
                available=car_data.available,
                image_1=car_data.image_1,
                image_2=car_data.image_2,
                image_3=car_data.image_3
            )
        except ValueError as e:
            logger.warning(f"Ошибка валидации при создании автомобиля: {e}")
            raise ValidationError(str(e))
        except Exception as e:
            logger.error(f"Ошибка при создании автомобиля: {e}")
            raise DatabaseError(f"Ошибка при создании автомобиля: {e}")
    
    async def update_car(self, car_id: int, car_data: CarUpdate) -> bool:
        """
        Обновляет информацию об автомобиле с валидацией через Pydantic
        
        Args:
            car_id: ID автомобиля для обновления
            car_data: Данные для обновления (валидируются через Pydantic)
            
        Returns:
            True если обновление успешно, False иначе
            
        Raises:
            ValidationError: При ошибках валидации данных
            NotFoundError: Если автомобиль не найден
            DatabaseError: При ошибках работы с БД
        """
        if car_id <= 0:
            raise ValidationError("ID автомобиля должен быть положительным числом")
        
        # Проверяем существование автомобиля
        existing_car = await self.get_car_by_id(car_id)
        if not existing_car:
            raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
        
        try:
            # Подготавливаем данные для обновления (только не None значения)
            update_data = {}
            if car_data.name is not None:
                update_data['name'] = car_data.name
            if car_data.description is not None:
                update_data['description'] = car_data.description
            if car_data.daily_price is not None:
                update_data['daily_price'] = car_data.daily_price
            if car_data.available is not None:
                update_data['available'] = car_data.available
            if car_data.image_1 is not None:
                update_data['image_1'] = car_data.image_1
            if car_data.image_2 is not None:
                update_data['image_2'] = car_data.image_2
            if car_data.image_3 is not None:
                update_data['image_3'] = car_data.image_3
            
            if not update_data:
                return True  # Нет изменений
            
            return await self.car_repository.update(car_id=car_id, **update_data)
        except ValueError as e:
            logger.warning(f"Ошибка валидации при обновлении автомобиля: {e}")
            raise ValidationError(str(e))
        except Exception as e:
            logger.error(f"Ошибка при обновлении автомобиля {car_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении автомобиля: {e}")
    
    async def delete_car(self, car_id: int) -> bool:
        """
        Удаляет автомобиль
        
        Args:
            car_id: ID автомобиля для удаления
            
        Returns:
            True если удаление успешно, False иначе
            
        Raises:
            ValidationError: При невалидном ID
            NotFoundError: Если автомобиль не найден
            DatabaseError: При ошибках работы с БД
        """
        if car_id <= 0:
            raise ValidationError("ID автомобиля должен быть положительным числом")
        
        # Проверяем существование автомобиля
        existing_car = await self.get_car_by_id(car_id)
        if not existing_car:
            raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
        
        try:
            return await self.car_repository.delete(car_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении автомобиля {car_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении автомобиля: {e}")

