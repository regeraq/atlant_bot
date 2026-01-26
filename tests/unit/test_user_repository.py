"""
Unit тесты для UserRepository
"""
import pytest
from unittest.mock import AsyncMock, Mock
from bot.database.repositories.user_repository import UserRepository


class TestUserRepository:
    """Тесты для класса UserRepository"""
    
    @pytest.fixture
    def mock_db_pool(self):
        """Создает мок db_pool"""
        pool = Mock()
        pool.execute = AsyncMock()
        pool.execute_fetchone = AsyncMock()
        pool.execute_fetchall = AsyncMock()
        pool.commit = AsyncMock()
        return pool
    
    @pytest.fixture
    def user_repository(self, mock_db_pool, monkeypatch):
        """Создает экземпляр UserRepository с мок db_pool"""
        import bot.database.repositories.user_repository
        monkeypatch.setattr(
            bot.database.repositories.user_repository,
            'db_pool',
            mock_db_pool
        )
        return UserRepository()
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repository, mock_db_pool):
        """Тест успешного создания пользователя"""
        result = await user_repository.create(
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )
        
        assert result is True
        mock_db_pool.execute.assert_called_once()
        mock_db_pool.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_without_username(self, user_repository, mock_db_pool):
        """Тест создания пользователя без username"""
        result = await user_repository.create(
            telegram_id=123456789,
            username=None,
            first_name="Test"
        )
        
        assert result is True
        mock_db_pool.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_without_first_name(self, user_repository, mock_db_pool):
        """Тест создания пользователя без first_name"""
        result = await user_repository.create(
            telegram_id=123456789,
            username="test_user",
            first_name=None
        )
        
        assert result is True
        mock_db_pool.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate(self, user_repository, mock_db_pool):
        """Тест создания дубликата пользователя (INSERT OR IGNORE)"""
        # INSERT OR IGNORE не должен вызывать ошибку
        result = await user_repository.create(
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, user_repository, mock_db_pool):
        """Тест получения всех пользователей"""
        expected_users = [
            {'id': 1, 'telegram_id': 111, 'username': 'user1'},
            {'id': 2, 'telegram_id': 222, 'username': 'user2'},
        ]
        mock_db_pool.execute_fetchall.return_value = expected_users
        
        result = await user_repository.get_all()
        
        assert result == expected_users
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_users_empty(self, user_repository, mock_db_pool):
        """Тест получения всех пользователей (пустой список)"""
        mock_db_pool.execute_fetchall.return_value = []
        
        result = await user_repository.get_all()
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_found(self, user_repository, mock_db_pool):
        """Тест получения пользователя по Telegram ID (найден)"""
        expected_user = {
            'id': 1,
            'telegram_id': 123456789,
            'username': 'test_user',
            'first_name': 'Test'
        }
        mock_db_pool.execute_fetchone.return_value = expected_user
        
        result = await user_repository.get_by_telegram_id(123456789)
        
        assert result == expected_user
        mock_db_pool.execute_fetchone.assert_called_once_with(
            "SELECT * FROM users WHERE telegram_id = ?",
            (123456789,)
        )
    
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(self, user_repository, mock_db_pool):
        """Тест получения пользователя по Telegram ID (не найден)"""
        mock_db_pool.execute_fetchone.return_value = None
        
        result = await user_repository.get_by_telegram_id(999999999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_user_handles_exception(self, user_repository, mock_db_pool):
        """Тест обработки исключений при создании пользователя"""
        mock_db_pool.execute.side_effect = Exception("DB error")
        
        result = await user_repository.create(
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )
        
        assert result is False






