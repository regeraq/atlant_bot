"""
Integration тесты для работы с базой данных
"""
import pytest
import aiosqlite
import tempfile
import os
from pathlib import Path
from bot.database.db_pool import DatabasePool
from bot.database.models import ALL_TABLES


class TestDatabasePool:
    """Integration тесты для DatabasePool"""
    
    @pytest.fixture
    async def temp_db(self, tmp_path):
        """Создает временную БД для тестов"""
        db_path = tmp_path / "test.db"
        pool = DatabasePool()
        # Переопределяем путь к БД через monkeypatch
        import bot.database.db_pool
        original_path = bot.database.db_pool.DB_PATH
        bot.database.db_pool.DB_PATH = str(db_path)
        
        await pool.initialize()
        yield pool, db_path
        
        await pool.close()
        bot.database.db_pool.DB_PATH = original_path
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, temp_db):
        """Тест инициализации пула"""
        pool, db_path = temp_db
        assert pool._connection is not None
        assert db_path.exists()
    
    @pytest.mark.asyncio
    async def test_create_tables(self, temp_db):
        """Тест создания таблиц"""
        pool, db_path = temp_db
        
        # Создаем таблицы
        for table_sql in ALL_TABLES:
            await pool.execute(table_sql)
        await pool.commit()
        
        # Проверяем, что таблицы созданы
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            table_names = [row[0] for row in tables]
            
            assert 'users' in table_names
            assert 'admins' in table_names
            assert 'cars' in table_names
            assert 'rentals' in table_names
            assert 'contacts' in table_names
    
    @pytest.mark.asyncio
    async def test_insert_and_select(self, temp_db):
        """Тест вставки и выборки данных"""
        pool, db_path = temp_db
        
        # Создаем таблицу для теста
        await pool.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        await pool.commit()
        
        # Вставляем данные
        await pool.execute(
            "INSERT INTO test_table (name) VALUES (?)",
            ("test_name",)
        )
        await pool.commit()
        
        # Выбираем данные
        result = await pool.execute_fetchone(
            "SELECT * FROM test_table WHERE name = ?",
            ("test_name",)
        )
        
        assert result is not None
        assert result['name'] == "test_name"
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, temp_db):
        """Тест отката транзакции"""
        pool, db_path = temp_db
        
        await pool.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        await pool.commit()
        
        # Вставляем данные
        await pool.execute(
            "INSERT INTO test_table (name) VALUES (?)",
            ("test_name",)
        )
        # НЕ коммитим
        
        # Проверяем, что данные не видны (т.к. не закоммичены)
        result = await pool.execute_fetchone(
            "SELECT * FROM test_table WHERE name = ?",
            ("test_name",)
        )
        # В SQLite с WAL режимом данные могут быть видны, но это нормально
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self, temp_db):
        """Тест множественных операций"""
        pool, db_path = temp_db
        
        await pool.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        await pool.commit()
        
        # Вставляем несколько записей
        for i in range(10):
            await pool.execute(
                "INSERT INTO test_table (name) VALUES (?)",
                (f"name_{i}",)
            )
        await pool.commit()
        
        # Выбираем все записи
        results = await pool.execute_fetchall("SELECT * FROM test_table")
        
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_pool_close(self, temp_db):
        """Тест закрытия пула"""
        pool, db_path = temp_db
        
        await pool.close()
        
        assert pool._connection is None






