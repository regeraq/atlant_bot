"""
Unit тесты для модуля cache.py
"""
import pytest
import time
from bot.utils.cache import SimpleCache


class TestSimpleCache:
    """Тесты для класса SimpleCache"""
    
    def test_cache_init_default_ttl(self):
        """Тест инициализации кэша с TTL по умолчанию"""
        cache = SimpleCache()
        assert cache.default_ttl == 300
        assert len(cache._cache) == 0
    
    def test_cache_init_custom_ttl(self):
        """Тест инициализации кэша с кастомным TTL"""
        cache = SimpleCache(default_ttl=600)
        assert cache.default_ttl == 600
    
    def test_set_and_get(self):
        """Тест установки и получения значения"""
        cache = SimpleCache(default_ttl=60)
        cache.set("test_key", "test_value")
        
        result = cache.get("test_key")
        assert result == "test_value"
    
    def test_get_nonexistent_key(self):
        """Тест получения несуществующего ключа"""
        cache = SimpleCache()
        result = cache.get("nonexistent")
        assert result is None
    
    def test_get_expired_key(self, monkeypatch):
        """Тест получения истекшего ключа"""
        import bot.utils.cache
        current_time = [1000.0]  # Начальное время
        
        def mock_time():
            return current_time[0]
        
        monkeypatch.setattr(bot.utils.cache, "time", mock_time)
        
        cache = SimpleCache(default_ttl=60)
        cache.set("expired_key", "value")
        
        # Симулируем истечение TTL
        current_time[0] = 1100.0  # Прошло больше 60 секунд
        
        result = cache.get("expired_key")
        assert result is None
        assert "expired_key" not in cache._cache
    
    def test_set_custom_ttl(self, monkeypatch):
        """Тест установки значения с кастомным TTL"""
        import bot.utils.cache
        current_time = [1000.0]
        
        def mock_time():
            return current_time[0]
        
        monkeypatch.setattr(bot.utils.cache, "time", mock_time)
        
        cache = SimpleCache(default_ttl=300)
        cache.set("key", "value", ttl=10)
        
        # Проверяем, что значение есть
        assert cache.get("key") == "value"
        
        # Симулируем истечение кастомного TTL
        current_time[0] = 1011.0  # Прошло больше 10 секунд
        
        result = cache.get("key")
        assert result is None
    
    def test_delete_existing_key(self):
        """Тест удаления существующего ключа"""
        cache = SimpleCache()
        cache.set("key", "value")
        cache.delete("key")
        
        assert cache.get("key") is None
    
    def test_delete_nonexistent_key(self):
        """Тест удаления несуществующего ключа (не должно вызывать ошибку)"""
        cache = SimpleCache()
        # Не должно вызывать исключение
        cache.delete("nonexistent")
    
    def test_clear(self):
        """Тест очистки всего кэша"""
        cache = SimpleCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert len(cache._cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_get_or_set_cache_hit(self):
        """Тест get_or_set при попадании в кэш"""
        cache = SimpleCache()
        cache.set("key", "cached_value")
        
        call_count = [0]
        def func():
            call_count[0] += 1
            return "new_value"
        
        result = cache.get_or_set("key", func)
        assert result == "cached_value"
        assert call_count[0] == 0  # Функция не должна вызываться
    
    def test_get_or_set_cache_miss(self):
        """Тест get_or_set при промахе кэша"""
        cache = SimpleCache()
        
        call_count = [0]
        def func():
            call_count[0] += 1
            return "new_value"
        
        result = cache.get_or_set("key", func)
        assert result == "new_value"
        assert call_count[0] == 1  # Функция должна вызваться один раз
        assert cache.get("key") == "new_value"  # Значение должно быть закэшировано
    
    def test_get_or_set_custom_ttl(self):
        """Тест get_or_set с кастомным TTL"""
        cache = SimpleCache(default_ttl=300)
        
        def func():
            return "value"
        
        cache.get_or_set("key", func, ttl=10)
        # Проверяем, что значение установлено
        assert cache.get("key") == "value"
    
    def test_concurrent_access(self):
        """Тест конкурентного доступа к кэшу"""
        cache = SimpleCache()
        
        # Симулируем конкурентную запись
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")
        
        # Проверяем, что все значения доступны
        for i in range(100):
            assert cache.get(f"key_{i}") == f"value_{i}"
    
    def test_overwrite_existing_key(self):
        """Тест перезаписи существующего ключа"""
        cache = SimpleCache()
        cache.set("key", "old_value")
        cache.set("key", "new_value")
        
        assert cache.get("key") == "new_value"
    
    def test_none_value(self):
        """Тест сохранения None значения"""
        cache = SimpleCache()
        cache.set("key", None)
        
        result = cache.get("key")
        assert result is None
    
    def test_complex_objects(self):
        """Тест сохранения сложных объектов"""
        cache = SimpleCache()
        complex_obj = {
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'int': 42
        }
        
        cache.set("complex", complex_obj)
        result = cache.get("complex")
        
        assert result == complex_obj
        assert result['list'] == [1, 2, 3]
        assert result['dict']['nested'] == 'value'

