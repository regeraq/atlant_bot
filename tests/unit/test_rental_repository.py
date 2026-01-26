"""
Unit тесты для RentalRepository
"""
import pytest
from unittest.mock import AsyncMock, Mock
from bot.database.repositories.rental_repository import RentalRepository


class TestRentalRepository:
    """Тесты для класса RentalRepository"""
    
    @pytest.fixture
    def mock_db_pool(self):
        """Создает мок db_pool"""
        pool = Mock()
        pool.execute = AsyncMock()
        pool.execute_fetchone = AsyncMock()
        pool.execute_fetchall = AsyncMock()
        pool.commit = AsyncMock()
        
        # Мокаем cursor для create
        mock_cursor = Mock()
        mock_cursor.lastrowid = 1
        pool.execute.return_value = mock_cursor
        
        return pool
    
    @pytest.fixture
    def rental_repository(self, mock_db_pool, monkeypatch):
        """Создает экземпляр RentalRepository с мок db_pool"""
        import bot.database.repositories.rental_repository
        monkeypatch.setattr(
            bot.database.repositories.rental_repository,
            'db_pool',
            mock_db_pool
        )
        return RentalRepository()
    
    @pytest.fixture
    def clean_cache(self, monkeypatch):
        """Очищает кэш"""
        from bot.utils.cache import cache
        cache.clear()
        yield
        cache.clear()
    
    @pytest.mark.asyncio
    async def test_create_rental_success(self, rental_repository, mock_db_pool, clean_cache):
        """Тест успешного создания аренды"""
        mock_db_pool.execute_fetchone.return_value = None  # Нет активной аренды
        
        rental_id = await rental_repository.create(
            user_id=123456789,
            car_id=1,
            daily_price=5000
        )
        
        assert rental_id == 1
        mock_db_pool.execute.assert_called()
        mock_db_pool.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_rental_existing_active(self, rental_repository, mock_db_pool, clean_cache):
        """Тест создания аренды при существующей активной"""
        # Возвращаем существующую активную аренду
        mock_db_pool.execute_fetchone.return_value = {'id': 1, 'user_id': 123456789}
        
        rental_id = await rental_repository.create(
            user_id=123456789,
            car_id=1,
            daily_price=5000
        )
        
        assert rental_id is None
    
    @pytest.mark.asyncio
    async def test_get_active_by_user_found(self, rental_repository, mock_db_pool, clean_cache):
        """Тест получения активной аренды пользователя (найдена)"""
        expected_rental = {
            'id': 1,
            'user_id': 123456789,
            'car_id': 1,
            'car_name': 'Test Car',
            'daily_price': 5000
        }
        mock_db_pool.execute_fetchone.return_value = expected_rental
        
        result = await rental_repository.get_active_by_user(123456789)
        
        assert result == expected_rental
    
    @pytest.mark.asyncio
    async def test_get_active_by_user_not_found(self, rental_repository, mock_db_pool, clean_cache):
        """Тест получения активной аренды пользователя (не найдена)"""
        mock_db_pool.execute_fetchone.return_value = None
        
        result = await rental_repository.get_active_by_user(123456789)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_active(self, rental_repository, mock_db_pool, clean_cache):
        """Тест получения всех активных аренд"""
        expected_rentals = [
            {'id': 1, 'user_id': 111, 'car_name': 'Car 1'},
            {'id': 2, 'user_id': 222, 'car_name': 'Car 2'},
        ]
        mock_db_pool.execute_fetchall.return_value = expected_rentals
        
        result = await rental_repository.get_all_active()
        
        assert result == expected_rentals
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, rental_repository, mock_db_pool):
        """Тест получения аренды по ID"""
        expected_rental = {
            'id': 1,
            'user_id': 123456789,
            'car_id': 1,
            'car_name': 'Test Car'
        }
        mock_db_pool.execute_fetchone.return_value = expected_rental
        
        result = await rental_repository.get_by_id(1)
        
        assert result == expected_rental
    
    @pytest.mark.asyncio
    async def test_end_rental(self, rental_repository, mock_db_pool, clean_cache):
        """Тест завершения аренды"""
        mock_db_pool.execute_fetchone.return_value = {'user_id': 123456789}
        
        result = await rental_repository.end(1)
        
        assert result is True
        mock_db_pool.execute.assert_called()
        mock_db_pool.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_reminder_time(self, rental_repository, mock_db_pool, clean_cache):
        """Тест обновления времени напоминания"""
        mock_db_pool.execute_fetchone.return_value = {'user_id': 123456789}
        
        result = await rental_repository.update_reminder_time(1, "14:00")
        
        assert result is True
        mock_db_pool.execute.assert_called()
        mock_db_pool.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_reminder_type(self, rental_repository, mock_db_pool, clean_cache):
        """Тест обновления типа напоминания"""
        mock_db_pool.execute_fetchone.return_value = {'user_id': 123456789}
        
        result = await rental_repository.update_reminder_type(1, "weekly")
        
        assert result is True
        mock_db_pool.execute.assert_called()
        mock_db_pool.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_with_custom_reminder_time(self, rental_repository, mock_db_pool, clean_cache):
        """Тест создания аренды с кастомным временем напоминания"""
        mock_db_pool.execute_fetchone.return_value = None
        
        rental_id = await rental_repository.create(
            user_id=123456789,
            car_id=1,
            daily_price=5000,
            reminder_time="15:30",
            reminder_type="weekly"
        )
        
        assert rental_id == 1
        # Проверяем, что правильные параметры переданы
        call_args = mock_db_pool.execute.call_args
        assert "15:30" in str(call_args)
        assert "weekly" in str(call_args)






