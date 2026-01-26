"""
Unit тесты для модуля config.py
"""
import pytest
import os
from unittest.mock import patch, mock_open
from bot.config import (
    _validate_bot_token,
    _parse_admin_ids,
    _parse_booking_contact_id,
    _validate_db_path,
    ENV_BOT_TOKEN,
    ENV_ADMIN_IDS,
    ENV_BOOKING_CONTACT_ID,
    MIN_BOT_TOKEN_LENGTH,
    ADMIN_IDS_SEPARATOR,
)


class TestValidateBotToken:
    """Тесты для функции _validate_bot_token"""
    
    def test_valid_token(self):
        """Тест валидного токена"""
        token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        result = _validate_bot_token(token)
        assert result == token
    
    def test_none_token(self):
        """Тест отсутствующего токена"""
        with pytest.raises(ValueError, match="BOT_TOKEN не установлен"):
            _validate_bot_token(None)
    
    def test_empty_token(self):
        """Тест пустого токена"""
        with pytest.raises(ValueError, match="BOT_TOKEN не установлен"):
            _validate_bot_token("")
    
    def test_whitespace_only_token(self):
        """Тест токена только с пробелами"""
        with pytest.raises(ValueError, match="BOT_TOKEN не установлен"):
            _validate_bot_token("   ")
    
    def test_too_short_token(self):
        """Тест слишком короткого токена"""
        short_token = "short"
        with pytest.raises(ValueError, match="слишком короткий"):
            _validate_bot_token(short_token)
    
    def test_token_without_colon(self):
        """Тест токена без двоеточия (должен предупредить, но не упасть)"""
        token = "a" * MIN_BOT_TOKEN_LENGTH
        # Не должно вызывать исключение, только предупреждение
        result = _validate_bot_token(token)
        assert result == token
    
    def test_token_stripping(self):
        """Тест обрезки пробелов в токене"""
        token_with_spaces = "  123456789:ABCdefGHIjklMNOpqrsTUVwxyz  "
        result = _validate_bot_token(token_with_spaces)
        assert result == token_with_spaces.strip()


class TestParseAdminIds:
    """Тесты для функции _parse_admin_ids"""
    
    def test_single_admin_id(self):
        """Тест парсинга одного ID"""
        result = _parse_admin_ids("123456789")
        assert result == [123456789]
    
    def test_multiple_admin_ids(self):
        """Тест парсинга нескольких ID"""
        result = _parse_admin_ids("123456789,987654321,555666777")
        assert result == [123456789, 987654321, 555666777]
    
    def test_empty_string(self):
        """Тест пустой строки"""
        result = _parse_admin_ids("")
        assert result == []
    
    def test_none_value(self):
        """Тест None значения"""
        result = _parse_admin_ids(None)
        assert result == []
    
    def test_with_spaces(self):
        """Тест ID с пробелами"""
        result = _parse_admin_ids("123456789 , 987654321 , 555666777")
        assert result == [123456789, 987654321, 555666777]
    
    def test_invalid_id_ignored(self):
        """Тест игнорирования некорректных ID"""
        result = _parse_admin_ids("123456789,invalid,987654321")
        assert result == [123456789, 987654321]
    
    def test_negative_id_ignored(self):
        """Тест игнорирования отрицательных ID"""
        result = _parse_admin_ids("123456789,-987654321,555666777")
        assert result == [123456789, 555666777]
    
    def test_zero_id_ignored(self):
        """Тест игнорирования нулевого ID"""
        result = _parse_admin_ids("123456789,0,555666777")
        assert result == [123456789, 555666777]
    
    def test_empty_values_ignored(self):
        """Тест игнорирования пустых значений"""
        result = _parse_admin_ids("123456789,,,987654321")
        assert result == [123456789, 987654321]
    
    def test_all_invalid_ids(self):
        """Тест случая, когда все ID некорректны"""
        result = _parse_admin_ids("invalid,not_a_number,abc")
        assert result == []


class TestParseBookingContactId:
    """Тесты для функции _parse_booking_contact_id"""
    
    def test_valid_contact_id(self):
        """Тест валидного ID контакта"""
        result = _parse_booking_contact_id("123456789")
        assert result == 123456789
    
    def test_none_value(self):
        """Тест None значения"""
        result = _parse_booking_contact_id(None)
        assert result is None
    
    def test_empty_string(self):
        """Тест пустой строки"""
        result = _parse_booking_contact_id("")
        assert result is None
    
    def test_with_spaces(self):
        """Тест ID с пробелами"""
        result = _parse_booking_contact_id("  123456789  ")
        assert result == 123456789
    
    def test_invalid_format(self):
        """Тест некорректного формата"""
        result = _parse_booking_contact_id("invalid")
        assert result is None
    
    def test_negative_id(self):
        """Тест отрицательного ID"""
        result = _parse_booking_contact_id("-123456789")
        assert result is None
    
    def test_zero_id(self):
        """Тест нулевого ID"""
        result = _parse_booking_contact_id("0")
        assert result is None


class TestValidateDbPath:
    """Тесты для функции _validate_db_path"""
    
    def test_valid_relative_path(self):
        """Тест валидного относительного пути"""
        result = _validate_db_path("test.db")
        assert result == "test.db"
    
    def test_path_with_spaces(self):
        """Тест пути с пробелами"""
        result = _validate_db_path("  test.db  ")
        assert result == "test.db"
    
    def test_path_with_parent_directory(self):
        """Тест пути с родительской директорией (должен предупредить)"""
        result = _validate_db_path("../test.db")
        # Не должно вызывать исключение, только предупреждение
        assert result == "../test.db"
    
    def test_absolute_path(self):
        """Тест абсолютного пути (должен предупредить)"""
        result = _validate_db_path("/tmp/test.db")
        # Не должно вызывать исключение, только предупреждение
        assert result == "/tmp/test.db"
    
    def test_path_with_special_chars(self):
        """Тест пути со специальными символами"""
        result = _validate_db_path("test-db_123.db")
        assert result == "test-db_123.db"






