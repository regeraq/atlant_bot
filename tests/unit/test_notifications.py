"""
Unit тесты для модуля notifications.py
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from bot.utils.notifications import BroadcastManager, format_broadcast_stats


class TestBroadcastManager:
    """Тесты для класса BroadcastManager"""
    
    @pytest.fixture
    def mock_bot(self):
        """Создает мок бота"""
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.send_photo = AsyncMock()
        bot.send_video = AsyncMock()
        bot.send_document = AsyncMock()
        bot.send_animation = AsyncMock()
        return bot
    
    @pytest.fixture
    def broadcast_manager(self, mock_bot):
        """Создает экземпляр BroadcastManager"""
        return BroadcastManager(mock_bot)
    
    @pytest.fixture
    def sample_users(self):
        """Тестовые пользователи"""
        return [
            {'telegram_id': 111111111},
            {'telegram_id': 222222222},
            {'telegram_id': 333333333},
        ]
    
    @pytest.mark.asyncio
    async def test_send_broadcast_text_preview_only(self, broadcast_manager, mock_bot):
        """Тест предварительного просмотра текстовой рассылки"""
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock):
            result = await broadcast_manager.send_broadcast(
                content_type='text',
                text="Test message",
                admin_id=123456789,
                preview_only=True
            )
            
            assert result['preview'] is True
            assert result['success'] is True
            mock_bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_broadcast_text_no_users(self, broadcast_manager):
        """Тест рассылки при отсутствии пользователей"""
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users:
            mock_get_users.return_value = []
            
            result = await broadcast_manager.send_broadcast(
                content_type='text',
                text="Test message"
            )
            
            assert result['total'] == 0
            assert result['sent'] == 0
    
    @pytest.mark.asyncio
    async def test_send_broadcast_text_success(self, broadcast_manager, sample_users):
        """Тест успешной текстовой рассылки"""
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock):
            mock_get_users.return_value = sample_users
            
            result = await broadcast_manager.send_broadcast(
                content_type='text',
                text="Test message",
                admin_id=123456789
            )
            
            assert result['total'] == 3
            assert result['sent'] == 3
            assert result['failed'] == 0
            assert result['blocked'] == 0
    
    @pytest.mark.asyncio
    async def test_send_broadcast_with_blocked_users(self, broadcast_manager, sample_users):
        """Тест рассылки с заблокированными пользователями"""
        from aiogram.exceptions import TelegramForbiddenError
        
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock):
            mock_get_users.return_value = sample_users
            
            # Первый пользователь заблокировал бота
            async def mock_send_message(*args, **kwargs):
                if kwargs.get('chat_id') == 111111111:
                    raise TelegramForbiddenError("Forbidden")
                return Mock()
            
            broadcast_manager.bot.send_message = mock_send_message
            
            result = await broadcast_manager.send_broadcast(
                content_type='text',
                text="Test message",
                admin_id=123456789
            )
            
            assert result['total'] == 3
            assert result['blocked'] == 1
            assert result['sent'] == 2
    
    @pytest.mark.asyncio
    async def test_send_broadcast_photo(self, broadcast_manager, sample_users):
        """Тест рассылки с фото"""
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock):
            mock_get_users.return_value = sample_users
            
            result = await broadcast_manager.send_broadcast(
                content_type='photo',
                text="Photo caption",
                file_id="photo_file_id",
                admin_id=123456789
            )
            
            assert result['sent'] == 3
            broadcast_manager.bot.send_photo.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_broadcast_video(self, broadcast_manager, sample_users):
        """Тест рассылки с видео"""
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock):
            mock_get_users.return_value = sample_users
            
            result = await broadcast_manager.send_broadcast(
                content_type='video',
                text="Video caption",
                file_id="video_file_id",
                admin_id=123456789
            )
            
            assert result['sent'] == 3
            broadcast_manager.bot.send_video.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_broadcast_document(self, broadcast_manager, sample_users):
        """Тест рассылки с документом"""
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock):
            mock_get_users.return_value = sample_users
            
            result = await broadcast_manager.send_broadcast(
                content_type='document',
                text="Document caption",
                file_id="doc_file_id",
                admin_id=123456789
            )
            
            assert result['sent'] == 3
            broadcast_manager.bot.send_document.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_broadcast_large_batch(self, broadcast_manager):
        """Тест рассылки большому количеству пользователей"""
        # Создаем 150 пользователей для тестирования батчинга
        large_user_list = [{'telegram_id': i} for i in range(150)]
        
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock), \
             patch('asyncio.sleep', new_callable=AsyncMock):  # Мокаем sleep для скорости
            mock_get_users.return_value = large_user_list
            
            result = await broadcast_manager.send_broadcast(
                content_type='text',
                text="Test message",
                admin_id=123456789
            )
            
            assert result['total'] == 150
            # Проверяем, что все пользователи получили сообщения
            assert broadcast_manager.bot.send_message.call_count == 150
    
    @pytest.mark.asyncio
    async def test_send_broadcast_with_errors(self, broadcast_manager, sample_users):
        """Тест рассылки с ошибками"""
        error_count = [0]
        
        async def mock_send_with_errors(*args, **kwargs):
            error_count[0] += 1
            if error_count[0] == 1:
                raise Exception("Network error")
            return Mock()
        
        with patch('bot.utils.notifications.get_all_users', new_callable=AsyncMock) as mock_get_users, \
             patch('bot.utils.notifications.add_broadcast_log', new_callable=AsyncMock):
            mock_get_users.return_value = sample_users
            broadcast_manager.bot.send_message = mock_send_with_errors
            
            result = await broadcast_manager.send_broadcast(
                content_type='text',
                text="Test message",
                admin_id=123456789
            )
            
            assert result['failed'] == 1
            assert result['sent'] == 2


class TestFormatBroadcastStats:
    """Тесты для функции format_broadcast_stats"""
    
    def test_format_preview_success(self):
        """Тест форматирования успешного предпросмотра"""
        stats = {'preview': True, 'success': True}
        result = format_broadcast_stats(stats)
        
        assert 'Предварительный просмотр успешен' in result
    
    def test_format_preview_error(self):
        """Тест форматирования ошибки предпросмотра"""
        stats = {'preview': True, 'success': False, 'error': 'Test error'}
        result = format_broadcast_stats(stats)
        
        assert 'Ошибка предварительного просмотра' in result
        assert 'Test error' in result
    
    def test_format_stats_success(self):
        """Тест форматирования успешной статистики"""
        stats = {
            'total': 100,
            'sent': 95,
            'failed': 3,
            'blocked': 2
        }
        result = format_broadcast_stats(stats)
        
        assert '100' in result
        assert '95' in result
        assert '95.0%' in result  # Процент успешных
        assert '3' in result
        assert '2' in result
    
    def test_format_stats_with_errors(self):
        """Тест форматирования статистики с ошибками"""
        stats = {
            'total': 10,
            'sent': 7,
            'failed': 3,
            'blocked': 0,
            'errors': ['Error 1', 'Error 2', 'Error 3', 'Error 4']
        }
        result = format_broadcast_stats(stats)
        
        assert 'Примеры ошибок' in result
        # Должны показаться первые 3 ошибки
        assert 'Error 1' in result
        assert 'Error 2' in result
        assert 'Error 3' in result
    
    def test_format_stats_zero_total(self):
        """Тест форматирования статистики с нулевым общим количеством"""
        stats = {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'blocked': 0
        }
        result = format_broadcast_stats(stats)
        
        assert '0' in result
        assert '0.0%' in result






