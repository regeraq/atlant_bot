"""
Integration тесты для CarRepository
"""
import pytest
import aiosqlite
from bot.database.repositories.car_repository import CarRepository
from bot.database.db_pool import DatabasePool
from bot.database.models import CREATE_CARS_TABLE
from bot.utils.cache import SimpleCache


class TestCarRepositoryIntegration:
    """Integration тесты для CarRepository с реальной БД"""
    
    @pytest.fixture
    async def test_db(self, tmp_path, monkeypatch):
        """Создает тестовую БД"""
        db_path = tmp_path / "test_cars.db"
        
        # Мокаем DB_PATH в config
        monkeypatch.setattr("bot.config.DB_PATH", str(db_path))
        
        # Создаем пул и инициализируем БД
        pool = DatabasePool()
        await pool.initialize()
        
        # Создаем таблицу cars
        await pool.execute(CREATE_CARS_TABLE)
        await pool.commit()
        
        yield pool, db_path
        
        await pool.close()
        if db_path.exists():
            db_path.unlink()
    
    @pytest.fixture
    def car_repository(self, test_db):
        """Создает экземпляр CarRepository"""
        pool, _ = test_db
        repo = CarRepository()
        # Заменяем db_pool на тестовый
        import bot.database.repositories.car_repository
        original_pool = bot.database.repositories.car_repository.db_pool
        bot.database.repositories.car_repository.db_pool = pool
        
        yield repo
        
        bot.database.repositories.car_repository.db_pool = original_pool
    
    @pytest.fixture
    def clean_cache(self):
        """Очищает кэш перед каждым тестом"""
        from bot.utils.cache import cache
        cache.clear()
        yield
        cache.clear()
    
    @pytest.mark.asyncio
    async def test_create_car(self, car_repository, clean_cache):
        """Тест создания автомобиля"""
        car_id = await car_repository.create(
            name="Test Car",
            description="Test description",
            daily_price=5000
        )
        
        assert car_id is not None
        assert car_id > 0
    
    @pytest.mark.asyncio
    async def test_get_car_by_id(self, car_repository, clean_cache):
        """Тест получения автомобиля по ID"""
        # Создаем автомобиль
        car_id = await car_repository.create(
            name="Test Car",
            description="Test description",
            daily_price=5000
        )
        
        # Получаем автомобиль
        car = await car_repository.get_by_id(car_id)
        
        assert car is not None
        assert car['id'] == car_id
        assert car['name'] == "Test Car"
        assert car['daily_price'] == 5000
    
    @pytest.mark.asyncio
    async def test_get_all_cars(self, car_repository, clean_cache):
        """Тест получения всех автомобилей"""
        # Создаем несколько автомобилей
        await car_repository.create("Car 1", "Desc 1", 5000, True)
        await car_repository.create("Car 2", "Desc 2", 6000, True)
        await car_repository.create("Car 3", "Desc 3", 7000, False)
        
        # Получаем все автомобили
        all_cars = await car_repository.get_all()
        assert len(all_cars) == 3
        
        # Получаем только доступные
        available_cars = await car_repository.get_all(available_only=True)
        assert len(available_cars) == 2
    
    @pytest.mark.asyncio
    async def test_update_car(self, car_repository, clean_cache):
        """Тест обновления автомобиля"""
        # Создаем автомобиль
        car_id = await car_repository.create(
            name="Old Name",
            description="Old description",
            daily_price=5000
        )
        
        # Обновляем
        success = await car_repository.update(
            car_id,
            name="New Name",
            daily_price=6000
        )
        
        assert success is True
        
        # Проверяем обновление
        car = await car_repository.get_by_id(car_id)
        assert car['name'] == "New Name"
        assert car['daily_price'] == 6000
        assert car['description'] == "Old description"  # Не изменено
    
    @pytest.mark.asyncio
    async def test_delete_car(self, car_repository, clean_cache):
        """Тест удаления автомобиля"""
        # Создаем автомобиль
        car_id = await car_repository.create(
            name="To Delete",
            description="Will be deleted",
            daily_price=5000
        )
        
        # Удаляем
        success = await car_repository.delete(car_id)
        
        assert success is True
        
        # Проверяем, что автомобиль удален
        car = await car_repository.get_by_id(car_id)
        assert car is None
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, car_repository, clean_cache):
        """Тест работы кэширования"""
        from bot.utils.cache import cache
        
        # Создаем автомобиль
        car_id = await car_repository.create(
            name="Cached Car",
            description="Test",
            daily_price=5000
        )
        
        # Первый запрос - должен идти в БД
        car1 = await car_repository.get_by_id(car_id)
        
        # Второй запрос - должен быть из кэша
        car2 = await car_repository.get_by_id(car_id)
        
        assert car1 == car2
        
        # Проверяем, что значение в кэше
        cached_value = cache.get(f"car:{car_id}")
        assert cached_value is not None
        assert cached_value['name'] == "Cached Car"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, car_repository, clean_cache):
        """Тест инвалидации кэша при обновлении"""
        from bot.utils.cache import cache
        
        # Создаем автомобиль
        car_id = await car_repository.create(
            name="Original Name",
            description="Test",
            daily_price=5000
        )
        
        # Получаем (кэшируется)
        await car_repository.get_by_id(car_id)
        
        # Обновляем
        await car_repository.update(car_id, name="Updated Name")
        
        # Кэш должен быть очищен
        cached_value = cache.get(f"car:{car_id}")
        assert cached_value is None
        
        # Новый запрос должен получить обновленные данные
        car = await car_repository.get_by_id(car_id)
        assert car['name'] == "Updated Name"






