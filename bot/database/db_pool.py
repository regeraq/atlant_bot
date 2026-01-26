"""
Connection pool для оптимизации работы с БД
"""
import aiosqlite
from typing import Optional
from bot.config import DB_PATH

class DatabasePool:
    """Пул соединений с базой данных для оптимизации производительности"""
    
    _instance: Optional['DatabasePool'] = None
    _connection: Optional[aiosqlite.Connection] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """Инициализация пула соединений"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(
                DB_PATH,
                check_same_thread=False
            )
            # Устанавливаем row_factory один раз при инициализации
            self._connection.row_factory = aiosqlite.Row
            # Оптимизация для производительности
            await self._connection.execute("PRAGMA journal_mode=WAL")
            await self._connection.execute("PRAGMA synchronous=NORMAL")
            await self._connection.execute("PRAGMA cache_size=10000")
            await self._connection.execute("PRAGMA foreign_keys=ON")
            await self._connection.commit()
            print("✅ Database pool initialized")
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Получить соединение из пула"""
        if self._connection is None:
            await self.initialize()
        return self._connection
    
    async def close(self):
        """Закрыть все соединения"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            print("✅ Database pool closed")
    
    async def execute(self, query: str, params: tuple = ()):
        """Выполнить запрос и вернуть cursor"""
        conn = await self.get_connection()
        cursor = await conn.execute(query, params)
        return cursor
    
    async def execute_fetchone(self, query: str, params: tuple = ()):
        """Выполнить запрос и получить одну строку"""
        conn = await self.get_connection()
        # row_factory уже установлен при инициализации
        cursor = await conn.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def execute_fetchall(self, query: str, params: tuple = ()):
        """Выполнить запрос и получить все строки"""
        conn = await self.get_connection()
        # row_factory уже установлен при инициализации
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def commit(self):
        """Закоммитить изменения"""
        if self._connection:
            await self._connection.commit()

# Глобальный экземпляр пула
db_pool = DatabasePool()

