"""
Unit тесты для модуля car_service.py
"""
import pytest
from unittest.mock import AsyncMock, Mock
from bot.services.car_service import CarService
from bot.database.repositories.car_repository import CarRepository


class TestCarService:
    """Тесты для класса CarService"""
    
    @pytest.fixture
    def mock_repository(self):
        """Создает мок репозитория"""
        repo = Mock(spec=CarRepository)
        repo.get_all = AsyncMock(return_value=[])
        repo.get_by_id = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=1)
        repo.update = AsyncMock(return_value=True)
        repo.delete = AsyncMock(return_value=True)
        return repo
    
    @pytest.fixture
    def car_service(self, mock_repository):
        """Создает экземпляр CarService с мок репозиторием"""
        return CarService(mock_repository)
    
    @pytest.mark.asyncio
    async def test_get_all_cars(self, car_service, mock_repository):
        """Тест получения всех автомобилей"""
        expected_cars = [{'id': 1, 'name': 'Car 1'}]
        mock_repository.get_all.return_value = expected_cars
        
        result = await car_service.get_all_cars()
        
        assert result == expected_cars
        mock_repository.get_all.assert_called_once_with(available_only=False)
    
    @pytest.mark.asyncio
    async def test_get_all_cars_available_only(self, car_service, mock_repository):
        """Тест получения только доступных автомобилей"""
        await car_service.get_all_cars(available_only=True)
        
        mock_repository.get_all.assert_called_once_with(available_only=True)
    
    @pytest.mark.asyncio
    async def test_get_car_by_id(self, car_service, mock_repository):
        """Тест получения автомобиля по ID"""
        expected_car = {'id': 1, 'name': 'Test Car'}
        mock_repository.get_by_id.return_value = expected_car
        
        result = await car_service.get_car_by_id(1)
        
        assert result == expected_car
        mock_repository.get_by_id.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_car_by_id_not_found(self, car_service, mock_repository):
        """Тест получения несуществующего автомобиля"""
        mock_repository.get_by_id.return_value = None
        
        result = await car_service.get_car_by_id(999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_car_valid(self, car_service, mock_repository):
        """Тест создания валидного автомобиля"""
        car_id = await car_service.create_car(
            name="Test Car",
            description="Test description",
            daily_price=5000
        )
        
        assert car_id == 1
        mock_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_car_name_too_short(self, car_service):
        """Тест создания автомобиля с слишком коротким названием"""
        with pytest.raises(ValueError, match="минимум 3 символа"):
            await car_service.create_car(
                name="AB",  # Слишком короткое
                description="Test",
                daily_price=5000
            )
    
    @pytest.mark.asyncio
    async def test_create_car_name_only_spaces(self, car_service):
        """Тест создания автомобиля с названием только из пробелов"""
        with pytest.raises(ValueError, match="минимум 3 символа"):
            await car_service.create_car(
                name="   ",  # Только пробелы
                description="Test",
                daily_price=5000
            )
    
    @pytest.mark.asyncio
    async def test_create_car_negative_price(self, car_service):
        """Тест создания автомобиля с отрицательной ценой"""
        with pytest.raises(ValueError, match="положительной"):
            await car_service.create_car(
                name="Test Car",
                description="Test",
                daily_price=-100
            )
    
    @pytest.mark.asyncio
    async def test_create_car_zero_price(self, car_service):
        """Тест создания автомобиля с нулевой ценой"""
        with pytest.raises(ValueError, match="положительной"):
            await car_service.create_car(
                name="Test Car",
                description="Test",
                daily_price=0
            )
    
    @pytest.mark.asyncio
    async def test_create_car_price_too_high(self, car_service):
        """Тест создания автомобиля со слишком высокой ценой"""
        with pytest.raises(ValueError, match="слишком большая"):
            await car_service.create_car(
                name="Test Car",
                description="Test",
                daily_price=2000000  # Превышает лимит
            )
    
    @pytest.mark.asyncio
    async def test_create_car_with_images(self, car_service, mock_repository):
        """Тест создания автомобиля с изображениями"""
        car_id = await car_service.create_car(
            name="Test Car",
            description="Test",
            daily_price=5000,
            image_1="image1.jpg",
            image_2="image2.jpg",
            image_3="image3.jpg"
        )
        
        assert car_id == 1
        call_args = mock_repository.create.call_args
        assert call_args[1]['image_1'] == "image1.jpg"
        assert call_args[1]['image_2'] == "image2.jpg"
        assert call_args[1]['image_3'] == "image3.jpg"
    
    @pytest.mark.asyncio
    async def test_update_car_valid(self, car_service, mock_repository):
        """Тест обновления автомобиля с валидными данными"""
        result = await car_service.update_car(
            car_id=1,
            name="Updated Car",
            daily_price=6000
        )
        
        assert result is True
        mock_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_car_name_too_short(self, car_service):
        """Тест обновления с слишком коротким названием"""
        with pytest.raises(ValueError, match="минимум 3 символа"):
            await car_service.update_car(
                car_id=1,
                name="AB"  # Слишком короткое
            )
    
    @pytest.mark.asyncio
    async def test_update_car_negative_price(self, car_service):
        """Тест обновления с отрицательной ценой"""
        with pytest.raises(ValueError, match="положительной"):
            await car_service.update_car(
                car_id=1,
                daily_price=-100
            )
    
    @pytest.mark.asyncio
    async def test_update_car_price_too_high(self, car_service):
        """Тест обновления со слишком высокой ценой"""
        with pytest.raises(ValueError, match="слишком большая"):
            await car_service.update_car(
                car_id=1,
                daily_price=2000000
            )
    
    @pytest.mark.asyncio
    async def test_update_car_no_changes(self, car_service, mock_repository):
        """Тест обновления без изменений"""
        result = await car_service.update_car(car_id=1)
        
        assert result is True
        mock_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_car(self, car_service, mock_repository):
        """Тест удаления автомобиля"""
        result = await car_service.delete_car(1)
        
        assert result is True
        mock_repository.delete.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_delete_car_not_found(self, car_service, mock_repository):
        """Тест удаления несуществующего автомобиля"""
        mock_repository.delete.return_value = False
        
        result = await car_service.delete_car(999)
        
        assert result is False






