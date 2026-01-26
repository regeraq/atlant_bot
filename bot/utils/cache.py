"""
Система кэширования для оптимизации производительности
"""
from typing import Optional, Dict, Any, Tuple
import time
from functools import wraps
from bot.utils.constants import DEFAULT_CACHE_TTL

class SimpleCache:
    """Простой in-memory кэш с TTL"""
    
    def __init__(self, default_ttl: int = DEFAULT_CACHE_TTL):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        
        if time.time() > expiry:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Установить значение в кэш"""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """Удалить значение из кэша"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """Очистить весь кэш"""
        self._cache.clear()
    
    def get_or_set(self, key: str, func, ttl: Optional[int] = None):
        """Получить из кэша или выполнить функцию и сохранить результат"""
        value = self.get(key)
        if value is not None:
            return value
        
        value = func()
        self.set(key, value, ttl)
        return value

# Глобальный экземпляр кэша
cache = SimpleCache(default_ttl=DEFAULT_CACHE_TTL)

def cached(ttl: int = DEFAULT_CACHE_TTL):
    """Декоратор для кэширования результатов функций"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кэша на основе аргументов
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Пытаемся получить из кэша
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

