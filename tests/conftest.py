"""
Конфигурация pytest и общие фикстуры
"""
import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator, AsyncGenerator

# Настройка asyncio для pytest
@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Создает временный путь для тестовой БД"""
    return tmp_path / "test_bot_database.db"


@pytest.fixture
def mock_bot():
    """Создает мок объект Bot"""
    bot = Mock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_video = AsyncMock()
    bot.send_document = AsyncMock()
    bot.send_animation = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Создает мок объект Message"""
    message = Mock()
    message.message_id = 1
    message.chat = Mock()
    message.chat.id = 123456789
    message.from_user = Mock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.text = "test message"
    message.answer = AsyncMock()
    message.delete = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query():
    """Создает мок объект CallbackQuery"""
    callback = Mock()
    callback.data = "test_callback"
    callback.message = Mock()
    callback.message.message_id = 1
    callback.message.chat = Mock()
    callback.message.chat.id = 123456789
    callback.message.edit_text = AsyncMock()
    callback.message.delete = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.from_user = Mock()
    callback.from_user.id = 123456789
    callback.from_user.username = "test_user"
    callback.from_user.first_name = "Test"
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def sample_car_data():
    """Тестовые данные автомобиля"""
    return {
        'id': 1,
        'name': 'Test Car',
        'description': 'Test description',
        'daily_price': 5000,
        'available': True,
        'image_1': None,
        'image_2': None,
        'image_3': None,
        'created_at': '2024-01-01 00:00:00'
    }


@pytest.fixture
def sample_user_data():
    """Тестовые данные пользователя"""
    return {
        'id': 1,
        'telegram_id': 123456789,
        'username': 'test_user',
        'first_name': 'Test',
        'created_at': '2024-01-01 00:00:00'
    }


@pytest.fixture
def sample_rental_data():
    """Тестовые данные аренды"""
    return {
        'id': 1,
        'user_id': 123456789,
        'car_id': 1,
        'start_date': '2024-01-01 00:00:00',
        'daily_price': 5000,
        'reminder_time': '12:00',
        'reminder_type': 'daily',
        'last_reminder_date': None,
        'is_active': True,
        'created_at': '2024-01-01 00:00:00'
    }


@pytest.fixture
def mock_db_pool():
    """Создает мок для db_pool"""
    pool = Mock()
    pool.execute = AsyncMock()
    pool.execute_fetchone = AsyncMock()
    pool.execute_fetchall = AsyncMock()
    pool.commit = AsyncMock()
    pool.get_connection = AsyncMock()
    return pool


@pytest.fixture
def mock_cache():
    """Создает мок для cache"""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    cache.delete = Mock()
    cache.clear = Mock()
    return cache


@pytest.fixture(autouse=True)
def reset_env_vars(monkeypatch):
    """Сбрасывает переменные окружения перед каждым тестом"""
    # Сохраняем оригинальные значения
    original_env = {}
    for key in ['BOT_TOKEN', 'DB_PATH', 'ADMIN_IDS', 'BOOKING_CONTACT_ID', 'LOG_LEVEL']:
        original_env[key] = os.environ.get(key)
        monkeypatch.delenv(key, raising=False)
    
    yield
    
    # Восстанавливаем оригинальные значения
    for key, value in original_env.items():
        if value is not None:
            monkeypatch.setenv(key, value)
        else:
            monkeypatch.delenv(key, raising=False)






