"""
Unit тесты для модуля helpers.py
"""
import pytest
from unittest.mock import AsyncMock, Mock
from aiogram.exceptions import TelegramBadRequest
from bot.utils.helpers import safe_callback_answer


class TestSafeCallbackAnswer:
    """Тесты для функции safe_callback_answer"""
    
    @pytest.mark.asyncio
    async def test_successful_answer(self, mock_callback_query):
        """Тест успешного ответа на callback"""
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once_with(
            text=None,
            show_alert=False
        )
    
    @pytest.mark.asyncio
    async def test_answer_with_text(self, mock_callback_query):
        """Тест ответа с текстом"""
        await safe_callback_answer(mock_callback_query, text="Test message")
        
        mock_callback_query.answer.assert_called_once_with(
            text="Test message",
            show_alert=False
        )
    
    @pytest.mark.asyncio
    async def test_answer_with_alert(self, mock_callback_query):
        """Тест ответа с alert"""
        await safe_callback_answer(mock_callback_query, show_alert=True)
        
        mock_callback_query.answer.assert_called_once_with(
            text=None,
            show_alert=True
        )
    
    @pytest.mark.asyncio
    async def test_answer_with_text_and_alert(self, mock_callback_query):
        """Тест ответа с текстом и alert"""
        await safe_callback_answer(
            mock_callback_query,
            text="Alert message",
            show_alert=True
        )
        
        mock_callback_query.answer.assert_called_once_with(
            text="Alert message",
            show_alert=True
        )
    
    @pytest.mark.asyncio
    async def test_handle_too_old_query_error(self, mock_callback_query):
        """Тест обработки ошибки 'query is too old'"""
        error = TelegramBadRequest("query is too old")
        mock_callback_query.answer.side_effect = error
        
        # Не должно вызывать исключение
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_timeout_error(self, mock_callback_query):
        """Тест обработки ошибки timeout"""
        error = TelegramBadRequest("timeout")
        mock_callback_query.answer.side_effect = error
        
        # Не должно вызывать исключение
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_invalid_query_id_error(self, mock_callback_query):
        """Тест обработки ошибки 'query id is invalid'"""
        error = TelegramBadRequest("query id is invalid")
        mock_callback_query.answer.side_effect = error
        
        # Не должно вызывать исключение
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_other_telegram_bad_request(self, mock_callback_query):
        """Тест обработки других TelegramBadRequest ошибок"""
        error = TelegramBadRequest("Some other error")
        mock_callback_query.answer.side_effect = error
        
        # Не должно вызывать исключение, но должно логировать предупреждение
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_unexpected_exception(self, mock_callback_query):
        """Тест обработки неожиданных исключений"""
        mock_callback_query.answer.side_effect = Exception("Unexpected error")
        
        # Не должно вызывать исключение
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_case_insensitive_error_matching(self, mock_callback_query):
        """Тест регистронезависимого сопоставления ошибок"""
        error = TelegramBadRequest("QUERY IS TOO OLD")
        mock_callback_query.answer.side_effect = error
        
        # Не должно вызывать исключение
        await safe_callback_answer(mock_callback_query)
        
        mock_callback_query.answer.assert_called_once()






