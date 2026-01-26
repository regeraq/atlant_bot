import aiosqlite
from bot.config import DB_PATH, ADMIN_IDS
from bot.database.models import ALL_TABLES
from bot.database.db_pool import db_pool
from bot.utils.cache import cache
from bot.utils.constants import (
    CACHE_TTL_CARS_LIST, CACHE_TTL_CAR_DETAILS,
    CACHE_TTL_RENTAL_USER, CACHE_TTL_RENTALS_ACTIVE,
    CACHE_TTL_ADMIN_CHECK
)
from typing import Optional, List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализация базы данных и создание всех таблиц"""
    # Инициализируем пул соединений
    await db_pool.initialize()
    db = await db_pool.get_connection()
    
    try:
        # Создаем все таблицы
        for table_sql in ALL_TABLES:
            await db.execute(table_sql)
        
        # Создаем индексы для оптимизации
        await _create_indexes(db)
        
        # Выполняем миграции для существующих таблиц
        await _migrate_cars_table_for_images(db)
        await _migrate_rentals_table_for_reminder_type(db)
        await _migrate_rentals_table_for_deposits(db)
        await _migrate_users_table_for_referrals(db)
        await _migrate_users_table_for_source(db)
        
        await db.commit()
        logger.info("✅ База данных инициализирована успешно")
        
        # Инициализируем администраторов из конфигурации
        await init_admins_from_config()
        
        # Инициализируем контакты
        await init_contacts()
        
        # Добавляем таблицу для логирования рассылок
        await _create_broadcast_logs_table(db)
        
        # Инициализируем настройки реферальной системы по умолчанию
        await _init_referral_settings(db)
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise

async def _create_indexes(db):
    """Создание индексов для оптимизации запросов"""
    try:
        # Индекс для быстрого поиска пользователей
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)
        """)
        # Индекс для быстрого поиска админов
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_admins_telegram_id ON admins(telegram_id)
        """)
        # Индекс для фильтрации доступных автомобилей
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_cars_available ON cars(available)
        """)
        # Индекс для сортировки по дате создания
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_cars_created_at ON cars(created_at DESC)
        """)
        # Индексы для аренды
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rentals_user_id ON rentals(user_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rentals_car_id ON rentals(car_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rentals_is_active ON rentals(is_active)
        """)
        logger.info("✅ Индексы созданы")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка создания индексов: {e}")

async def _migrate_cars_table_for_images(db):
    """Миграция таблицы cars для добавления полей изображений"""
    try:
        # Проверяем существующие колонки в таблице cars
        cursor = await db.execute("PRAGMA table_info(cars)")
        columns = await cursor.fetchall()
        existing_columns = {col[1] for col in columns}  # col[1] - имя колонки
        
        # Добавляем отсутствующие колонки для изображений
        image_columns = ['image_1', 'image_2', 'image_3']
        for img_col in image_columns:
            if img_col not in existing_columns:
                await db.execute(f"ALTER TABLE cars ADD COLUMN {img_col} TEXT")
                logger.info(f"✅ Добавлена колонка {img_col} в таблицу cars")
        
        # Проверяем, нужна ли миграция
        added_cols = [col for col in image_columns if col not in existing_columns]
        if added_cols:
            logger.info(f"🔄 Миграция завершена: добавлено {len(added_cols)} колонок для изображений")
        
    except Exception as e:
        logger.warning(f"⚠️  Ошибка при миграции таблицы cars: {e}")
        # Не останавливаем работу, так как для новых БД колонки уже будут созданы

async def _migrate_rentals_table_for_reminder_type(db):
    """Миграция таблицы rentals для добавления полей reminder_type и last_reminder_date"""
    try:
        # Проверяем существующие колонки в таблице rentals
        cursor = await db.execute("PRAGMA table_info(rentals)")
        columns = await cursor.fetchall()
        existing_columns = {col[1] for col in columns}  # col[1] - имя колонки
        
        # Добавляем отсутствующие колонки
        if 'reminder_type' not in existing_columns:
            await db.execute("ALTER TABLE rentals ADD COLUMN reminder_type TEXT DEFAULT 'daily'")
            logger.info("✅ Добавлена колонка reminder_type в таблицу rentals")
        
        if 'last_reminder_date' not in existing_columns:
            await db.execute("ALTER TABLE rentals ADD COLUMN last_reminder_date DATE")
            logger.info("✅ Добавлена колонка last_reminder_date в таблицу rentals")
        
        # Обновляем существующие записи, если нужно
        if 'reminder_type' not in existing_columns:
            await db.execute("UPDATE rentals SET reminder_type = 'daily' WHERE reminder_type IS NULL")
        
    except Exception as e:
        logger.warning(f"⚠️  Ошибка при миграции таблицы rentals: {e}")

async def _migrate_rentals_table_for_deposits(db):
    """Миграция таблицы rentals для добавления полей deposit_amount и deposit_status (Модуль 4)"""
    try:
        cursor = await db.execute("PRAGMA table_info(rentals)")
        columns = await cursor.fetchall()
        existing_columns = {col[1] for col in columns}
        
        if 'deposit_amount' not in existing_columns:
            await db.execute("ALTER TABLE rentals ADD COLUMN deposit_amount DECIMAL(10, 2) DEFAULT 0")
            logger.info("✅ Добавлена колонка deposit_amount в таблицу rentals")
        
        if 'deposit_status' not in existing_columns:
            await db.execute("ALTER TABLE rentals ADD COLUMN deposit_status TEXT DEFAULT 'pending'")
            # Обновляем существующие записи
            await db.execute("UPDATE rentals SET deposit_status = 'pending' WHERE deposit_status IS NULL")
            logger.info("✅ Добавлена колонка deposit_status в таблицу rentals")
        
        # Добавляем поле end_date для определения даты окончания аренды
        if 'end_date' not in existing_columns:
            await db.execute("ALTER TABLE rentals ADD COLUMN end_date DATE")
            logger.info("✅ Добавлена колонка end_date в таблицу rentals")
        
        # Добавляем поле referral_discount_percentage для хранения примененного реферального бонуса (Модуль 6)
        if 'referral_discount_percentage' not in existing_columns:
            await db.execute("ALTER TABLE rentals ADD COLUMN referral_discount_percentage INTEGER DEFAULT 0")
            logger.info("✅ Добавлена колонка referral_discount_percentage в таблицу rentals")
        
    except Exception as e:
        logger.warning(f"⚠️  Ошибка при миграции таблицы rentals для депозитов: {e}")

async def _migrate_users_table_for_referrals(db):
    """Миграция таблицы users для добавления полей referral_code и referrer_id (Модуль 6)"""
    try:
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        existing_columns = {col[1] for col in columns}
        
        if 'referral_code' not in existing_columns:
            # SQLite не поддерживает добавление UNIQUE колонки напрямую
            # Сначала добавляем колонку без ограничения
            await db.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
            # Затем создаем уникальный индекс
            await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)")
            logger.info("✅ Добавлена колонка referral_code в таблицу users")
        
        if 'referrer_id' not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
            logger.info("✅ Добавлена колонка referrer_id в таблицу users")
        
    except Exception as e:
        logger.warning(f"⚠️  Ошибка при миграции таблицы users для реферальной системы: {e}")

async def _migrate_users_table_for_source(db):
    """Миграция таблицы users для добавления поля source (Модуль 7)"""
    try:
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        existing_columns = {col[1] for col in columns}
        
        if 'source' not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN source TEXT")
            logger.info("✅ Добавлена колонка source в таблицу users")
        
    except Exception as e:
        logger.warning(f"⚠️  Ошибка при миграции таблицы users для UTM-меток: {e}")

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ===

async def add_user(telegram_id: int, username: Optional[str], first_name: Optional[str], 
                  referral_code: Optional[str] = None, source: Optional[str] = None) -> bool:
    """Добавляет нового пользователя в базу данных (Модули 6, 7: поддержка рефералов и источников)"""
    try:
        # Проверяем, существует ли уже пользователь
        existing = await get_user_by_id(telegram_id)
        if existing:
            # Пользователь уже существует, обновляем source, если он еще не установлен (Модуль 7)
            if source and not existing.get('source'):
                await update_user_source(telegram_id, source)
            return False
        
        await db_pool.execute(
            "INSERT INTO users (telegram_id, username, first_name, referral_code, source) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, referral_code, source)
        )
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        return False

async def get_all_users() -> List[Dict[str, Any]]:
    """Получает всех пользователей из базы данных"""
    try:
        return await db_pool.execute_fetchall("SELECT * FROM users ORDER BY created_at DESC")
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {e}")
        return []

async def get_users_chunked(chunk_size: int = None):
    """
    Async генератор для получения пользователей порциями (для оптимизации памяти)
    Используется в рассылках для обработки больших объемов данных
    
    Args:
        chunk_size: Размер порции (если None, используется DB_CHUNK_SIZE из констант)
    
    Yields:
        List[Dict[str, Any]]: Список пользователей порциями
    """
    from bot.utils.constants import DB_CHUNK_SIZE
    
    if chunk_size is None:
        chunk_size = DB_CHUNK_SIZE
    
    offset = 0
    while True:
        try:
            users = await db_pool.execute_fetchall(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (chunk_size, offset)
            )
            if not users:
                break
            yield users
            offset += chunk_size
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей порциями: {e}")
            break

# === ФУНКЦИИ ДЛЯ РАБОТЫ С АВТОМОБИЛЯМИ ===

async def add_car(name: str, description: Optional[str], daily_price: int, available: bool = True, 
                 image_1: Optional[str] = None, image_2: Optional[str] = None, image_3: Optional[str] = None) -> Optional[int]:
    """Добавляет новый автомобиль в базу данных и очищает кэш"""
    try:
        cursor = await db_pool.execute(
            "INSERT INTO cars (name, description, daily_price, available, image_1, image_2, image_3) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, description, daily_price, available, image_1, image_2, image_3)
        )
        await db_pool.commit()
        
        # Очищаем кэш списка автомобилей
        cache.delete("cars:all:True")
        cache.delete("cars:all:False")
        
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении автомобиля: {e}")
        return None

async def get_all_cars(available_only: bool = False) -> List[Dict[str, Any]]:
    """Получает все автомобили из базы данных с кэшированием"""
    try:
        cache_key = f"cars:all:{available_only}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        query = "SELECT * FROM cars"
        params = ()
        if available_only:
            query += " WHERE available = 1"
        query += " ORDER BY created_at DESC"
        
        result = await db_pool.execute_fetchall(query, params)
        # Используем константу для TTL кэша
        cache.set(cache_key, result, ttl=CACHE_TTL_CARS_LIST)
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении автомобилей: {e}")
        return []

async def get_car_by_id(car_id: int) -> Optional[Dict[str, Any]]:
    """Получает автомобиль по ID с кэшированием"""
    try:
        cache_key = f"car:{car_id}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = await db_pool.execute_fetchone("SELECT * FROM cars WHERE id = ?", (car_id,))
        if result:
            # Используем константу для TTL кэша
            cache.set(cache_key, result, ttl=CACHE_TTL_CAR_DETAILS)
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении автомобиля: {e}")
        return None

async def update_car(car_id: int, name: Optional[str] = None, description: Optional[str] = None, 
                    daily_price: Optional[int] = None, available: Optional[bool] = None,
                    image_1: Optional[str] = None, image_2: Optional[str] = None, image_3: Optional[str] = None) -> bool:
    """Обновляет информацию об автомобиле и очищает кэш"""
    try:
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if daily_price is not None:
            updates.append("daily_price = ?")
            params.append(daily_price)
        if available is not None:
            updates.append("available = ?")
            params.append(available)
        if image_1 is not None:
            updates.append("image_1 = ?")
            params.append(image_1)
        if image_2 is not None:
            updates.append("image_2 = ?")
            params.append(image_2)
        if image_3 is not None:
            updates.append("image_3 = ?")
            params.append(image_3)
        
        if not updates:
            return True
        
        params.append(car_id)
        query = f"UPDATE cars SET {', '.join(updates)} WHERE id = ?"
        
        await db_pool.execute(query, tuple(params))
        await db_pool.commit()
        
        # Очищаем кэш для этого автомобиля и списка автомобилей
        cache.delete(f"car:{car_id}")
        cache.delete("cars:all:True")
        cache.delete("cars:all:False")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении автомобиля: {e}")
        return False

async def delete_car(car_id: int) -> bool:
    """Удаляет автомобиль из базы данных и очищает кэш"""
    try:
        # Проверяем, существует ли автомобиль
        car = await get_car_by_id(car_id)
        if not car:
            logger.warning(f"Попытка удалить несуществующий автомобиль с ID: {car_id}")
            return False
        
        # Проверяем, есть ли активные аренды для этого автомобиля
        active_rentals = await db_pool.execute_fetchall(
            "SELECT id FROM rentals WHERE car_id = ? AND is_active = 1",
            (car_id,)
        )
        
        if active_rentals:
            logger.warning(f"Нельзя удалить автомобиль с ID {car_id}: есть {len(active_rentals)} активных аренд")
            return False
        
        # Удаляем все аренды (активные и неактивные), связанные с этим автомобилем
        # Это необходимо для избежания ошибки FOREIGN KEY constraint
        rentals_to_delete = await db_pool.execute_fetchall(
            "SELECT id, user_id FROM rentals WHERE car_id = ?",
            (car_id,)
        )
        
        if rentals_to_delete:
            # Очищаем кэш для пользователей, у которых были аренды этого автомобиля
            for rental in rentals_to_delete:
                cache.delete(f"rental:user:{rental['user_id']}")
            
            # Удаляем все аренды этого автомобиля
            await db_pool.execute(
                "DELETE FROM rentals WHERE car_id = ?",
                (car_id,)
            )
            logger.info(f"Удалено {len(rentals_to_delete)} аренд для автомобиля с ID {car_id}")
        
        # Удаляем автомобиль
        cursor = await db_pool.execute("DELETE FROM cars WHERE id = ?", (car_id,))
        await db_pool.commit()
        
        # Проверяем, было ли удаление успешным
        if cursor.rowcount == 0:
            logger.warning(f"Автомобиль с ID {car_id} не был удален (возможно, не существует)")
            return False
        
        # Очищаем кэш
        cache.delete(f"car:{car_id}")
        cache.delete("cars:all:True")
        cache.delete("cars:all:False")
        cache.delete("rentals:active")
        
        logger.info(f"Автомобиль с ID {car_id} успешно удален")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении автомобиля: {e}")
        return False

# === ФУНКЦИИ ДЛЯ РАБОТЫ С АДМИНИСТРАТОРАМИ ===

async def add_admin(telegram_id: int) -> bool:
    """Добавляет администратора в базу данных"""
    try:
        # Сначала проверяем, существует ли уже администратор
        existing = await db_pool.execute_fetchone(
            "SELECT id FROM admins WHERE telegram_id = ?",
            (telegram_id,)
        )
        if existing:
            logger.warning(f"Администратор с ID {telegram_id} уже существует")
            return False
        
        # Добавляем администратора
        await db_pool.execute(
            "INSERT INTO admins (telegram_id) VALUES (?)",
            (telegram_id,)
        )
        await db_pool.commit()
        
        # Очищаем кэш для этого администратора
        cache.delete(f"admin:{telegram_id}")
        
        logger.info(f"Администратор с ID {telegram_id} успешно добавлен")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}")
        return False

async def is_admin(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь администратором с кэшированием"""
    try:
        cache_key = f"admin:{telegram_id}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = await db_pool.execute_fetchone("SELECT id FROM admins WHERE telegram_id = ?", (telegram_id,))
        is_admin_result = result is not None
        # Используем константу для TTL кэша
        cache.set(cache_key, is_admin_result, ttl=CACHE_TTL_ADMIN_CHECK)
        return is_admin_result
    except Exception as e:
        logger.error(f"Ошибка при проверке администратора: {e}")
        return False

async def get_all_admins() -> List[Dict[str, Any]]:
    """Получает всех администраторов"""
    try:
        return await db_pool.execute_fetchall("SELECT * FROM admins ORDER BY added_at DESC")
    except Exception as e:
        logger.error(f"Ошибка при получении администраторов: {e}")
        return []

async def delete_admin(telegram_id: int) -> bool:
    """Удаляет администратора из базы данных"""
    try:
        cursor = await db_pool.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
        await db_pool.commit()
        # Проверяем, было ли удаление успешным
        success = cursor.rowcount > 0
        if success:
            # Очищаем кэш для удаленного администратора
            cache.delete(f"admin:{telegram_id}")
        return success
    except Exception as e:
        logger.error(f"Ошибка при удалении администратора: {e}")
        return False

# === ФУНКЦИЯ ДЛЯ ДОБАВЛЕНИЯ ТЕСТОВЫХ ДАННЫХ ===

async def add_sample_cars():
    """Добавляет несколько тестовых автомобилей"""
    # Проверяем, есть ли уже машины в базе
    existing_cars = await get_all_cars()
    if existing_cars:
        print("Тестовые автомобили уже добавлены")
        return
    
    sample_cars = [
        {
            "name": "BMW X5 2021",
            "description": "Премиальный внедорожник с полным приводом. Комфортная кожаная салон, автоматическая коробка передач, система навигации.",
            "daily_price": 8500
        },
        {
            "name": "Mercedes-Benz C-Class 2020",
            "description": "Элегантный седан бизнес-класса. Экономичный двигатель, стильный дизайн, современные системы безопасности.",
            "daily_price": 7200
        },
        {
            "name": "Toyota Camry 2022",
            "description": "Надежный и комфортный седан. Отличная топливная экономичность, просторный салон, высокая надежность.",
            "daily_price": 5800
        },
        {
            "name": "Honda CR-V 2021",
            "description": "Популярный кроссовер для семьи. Высокий клиренс, вместительный багажник, отличная видимость.",
            "daily_price": 6500
        }
    ]
    
    for car in sample_cars:
        await add_car(**car)
    
    print(f"Добавлено {len(sample_cars)} тестовых автомобилей")

async def init_admins_from_config():
    """Инициализация администраторов из конфигурации (оптимизировано для параллельного добавления)"""
    if not ADMIN_IDS:
        return
    
    try:
        import asyncio
        
        # Проверяем, сколько админов уже есть в системе
        existing_admins = await get_all_admins()
        existing_ids = {admin['telegram_id'] for admin in existing_admins}
        
        # Фильтруем только новых администраторов
        new_admin_ids = [admin_id for admin_id in ADMIN_IDS if admin_id not in existing_ids]
        
        if not new_admin_ids:
            if existing_admins:
                print(f"ℹ️  Все администраторы из конфигурации уже существуют (всего: {len(existing_admins)})")
            return
        
        # Добавляем новых администраторов параллельно
        async def add_single_admin(admin_id: int) -> bool:
            """Добавляет одного администратора"""
            return await add_admin(admin_id)
        
        # Параллельное добавление через asyncio.gather
        results = await asyncio.gather(*[add_single_admin(admin_id) for admin_id in new_admin_ids], return_exceptions=True)
        added_count = sum(1 for result in results if result is True)
        
        if added_count > 0:
            print(f"✅ Добавлено {added_count} новых администратор(ов) из конфигурации")
        
    except Exception as e:
        print(f"⚠️  Ошибка при инициализации администраторов из конфигурации: {e}")

async def _create_broadcast_logs_table(db):
    """Создает таблицу для логирования рассылок"""
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                text TEXT,
                total_users INTEGER NOT NULL,
                sent_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                blocked_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Индекс для быстрого поиска по дате
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_broadcast_logs_created_at 
            ON broadcast_logs(created_at DESC)
        """)
        logger.info("✅ Таблица логирования рассылок готова")
    except Exception as e:
        logger.warning(f"⚠️  Ошибка создания таблицы рассылок: {e}")

# === ФУНКЦИИ ДЛЯ РАССЫЛКИ ===

async def add_broadcast_log(admin_id: int, content_type: str, text: Optional[str], 
                          total_users: int, sent_count: int, failed_count: int, blocked_count: int) -> bool:
    """Добавляет запись о рассылке в логи"""
    try:
        await db_pool.execute(
            """INSERT INTO broadcast_logs 
               (admin_id, content_type, text, total_users, sent_count, failed_count, blocked_count) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (admin_id, content_type, text, total_users, sent_count, failed_count, blocked_count)
        )
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении лога рассылки: {e}")
        return False

async def get_broadcast_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Получает историю рассылок"""
    try:
        return await db_pool.execute_fetchall(
            "SELECT * FROM broadcast_logs ORDER BY created_at DESC LIMIT ?", 
            (limit,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении истории рассылок: {e}")
        return []

# === ФУНКЦИИ ДЛЯ РАБОТЫ С АРЕНДОЙ ===

async def add_rental(user_id: int, car_id: int, daily_price: int, reminder_time: str = "12:00", 
                    reminder_type: str = "daily", deposit_amount: float = 0.0, deposit_status: str = "pending",
                    end_date: Optional[str] = None, referral_discount_percentage: int = 0) -> Optional[int]:
    """Добавляет аренду автомобиля пользователю (Модули 4, 6: добавлена поддержка залогов и реферальных скидок)"""
    try:
        # Проверяем, нет ли уже активной аренды у пользователя
        existing = await get_active_rental_by_user(user_id)
        if existing:
            return None  # У пользователя уже есть активная аренда
        
        # Применяем реферальную скидку к цене, если есть (Модуль 6)
        final_price = daily_price
        if referral_discount_percentage > 0:
            discount = (daily_price * referral_discount_percentage) // 100
            final_price = daily_price - discount
        
        cursor = await db_pool.execute(
            """INSERT INTO rentals (user_id, car_id, daily_price, reminder_time, reminder_type, 
               deposit_amount, deposit_status, end_date, referral_discount_percentage) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, car_id, final_price, reminder_time, reminder_type, deposit_amount, deposit_status, 
             end_date, referral_discount_percentage)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        cache.delete(f"rental:user:{user_id}")
        cache.delete("rentals:active")
        
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении аренды: {e}")
        return None

async def get_active_rental_by_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получает активную аренду пользователя"""
    try:
        cache_key = f"rental:user:{user_id}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = await db_pool.execute_fetchone(
            """SELECT r.*, c.name as car_name, c.description as car_description, 
                      c.image_1, c.image_2, c.image_3
               FROM rentals r
               JOIN cars c ON r.car_id = c.id
               WHERE r.user_id = ? AND r.is_active = 1
               ORDER BY r.created_at DESC
               LIMIT 1""",
            (user_id,)
        )
        
        if result:
            cache.set(cache_key, result, ttl=CACHE_TTL_RENTAL_USER)
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении аренды пользователя: {e}")
        return None

async def get_all_active_rentals() -> List[Dict[str, Any]]:
    """Получает все активные аренды"""
    try:
        cache_key = "rentals:active"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = await db_pool.execute_fetchall(
            """SELECT r.*, c.name as car_name, u.first_name, u.username
               FROM rentals r
               JOIN cars c ON r.car_id = c.id
               JOIN users u ON r.user_id = u.telegram_id
               WHERE r.is_active = 1
               ORDER BY r.created_at DESC"""
        )
        
        cache.set(cache_key, result, ttl=CACHE_TTL_RENTALS_ACTIVE)
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении активных аренд: {e}")
        return []

async def get_rentals_by_reminder_time(reminder_time: str) -> List[Dict[str, Any]]:
    """
    Получает активные аренды с указанным временем напоминания (Fix based on audit)
    Оптимизация для PaymentReminderScheduler - фильтрация на уровне БД вместо загрузки всех аренд
    
    Args:
        reminder_time: Время напоминания в формате "HH:MM"
    
    Returns:
        Список аренд с указанным временем напоминания
    """
    try:
        result = await db_pool.execute_fetchall(
            """SELECT r.*, c.name as car_name, u.first_name, u.username
               FROM rentals r
               JOIN cars c ON r.car_id = c.id
               JOIN users u ON r.user_id = u.telegram_id
               WHERE r.is_active = 1 AND r.reminder_time = ?
               ORDER BY r.created_at DESC""",
            (reminder_time,)
        )
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении аренд по времени напоминания: {e}")
        return []

async def end_rental(rental_id: int) -> bool:
    """Завершает аренду"""
    try:
        await db_pool.execute(
            "UPDATE rentals SET is_active = 0 WHERE id = ?",
            (rental_id,)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        cache.delete("rentals:active")
        # Очищаем кэш пользователя (нужно получить user_id из rental_id)
        rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
        if rental:
            cache.delete(f"rental:user:{rental['user_id']}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при завершении аренды: {e}")
        return False

async def update_rental_reminder_time(rental_id: int, reminder_time: str) -> bool:
    """Обновляет время напоминания для аренды"""
    try:
        await db_pool.execute(
            "UPDATE rentals SET reminder_time = ? WHERE id = ?",
            (reminder_time, rental_id)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
        if rental:
            cache.delete(f"rental:user:{rental['user_id']}")
        cache.delete("rentals:active")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени напоминания: {e}")
        return False

async def update_rental_reminder_type(rental_id: int, reminder_type: str) -> bool:
    """Обновляет тип напоминания для аренды"""
    try:
        await db_pool.execute(
            "UPDATE rentals SET reminder_type = ?, last_reminder_date = NULL WHERE id = ?",
            (reminder_type, rental_id)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
        if rental:
            cache.delete(f"rental:user:{rental['user_id']}")
        cache.delete("rentals:active")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении типа напоминания: {e}")
        return False

async def update_rental_last_reminder(rental_id: int, reminder_date: str) -> bool:
    """Обновляет дату последнего напоминания"""
    try:
        await db_pool.execute(
            "UPDATE rentals SET last_reminder_date = ? WHERE id = ?",
            (reminder_date, rental_id)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
        if rental:
            cache.delete(f"rental:user:{rental['user_id']}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении даты напоминания: {e}")
        return False

async def get_rental_by_id(rental_id: int) -> Optional[Dict[str, Any]]:
    """Получает аренду по ID"""
    try:
        return await db_pool.execute_fetchone(
            """SELECT r.*, c.name as car_name, u.first_name, u.username
               FROM rentals r
               JOIN cars c ON r.car_id = c.id
               JOIN users u ON r.user_id = u.telegram_id
               WHERE r.id = ?""",
            (rental_id,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении аренды: {e}")
        return None

async def update_rental_deposit_status(rental_id: int, deposit_status: str) -> bool:
    """Обновляет статус залога аренды (Модуль 4)"""
    try:
        await db_pool.execute(
            "UPDATE rentals SET deposit_status = ? WHERE id = ?",
            (deposit_status, rental_id)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
        if rental:
            cache.delete(f"rental:user:{rental['user_id']}")
        cache.delete("rentals:active")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса залога: {e}")
        return False

async def update_rental_end_date(rental_id: int, end_date: str) -> bool:
    """Обновляет дату окончания аренды"""
    try:
        await db_pool.execute(
            "UPDATE rentals SET end_date = ? WHERE id = ?",
            (end_date, rental_id)
        )
        await db_pool.commit()
        
        # Очищаем кэш
        rental = await db_pool.execute_fetchone("SELECT user_id FROM rentals WHERE id = ?", (rental_id,))
        if rental:
            cache.delete(f"rental:user:{rental['user_id']}")
        cache.delete("rentals:active")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении даты окончания аренды: {e}")
        return False

# === ФУНКЦИЯ ДЛЯ ВЫГРУЗКИ БАЗЫ ДАННЫХ ===

async def export_database() -> Optional[bytes]:
    """Экспортирует базу данных в бинарный формат для скачивания"""
    try:
        # Используем асинхронную файловую операцию вместо блокирующей
        import aiofiles
        
        if os.path.exists(DB_PATH):
            async with aiofiles.open(DB_PATH, 'rb') as f:
                db_data = await f.read()
            return db_data
        return None
    except ImportError:
        # Fallback на синхронную операцию, если aiofiles не установлен
        logger.warning("aiofiles не установлен, используется синхронная операция")
        try:
            if os.path.exists(DB_PATH):
                with open(DB_PATH, 'rb') as f:
                    db_data = f.read()
                return db_data
            return None
        except Exception as e:
            logger.error(f"Ошибка при экспорте БД: {e}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при экспорте БД: {e}")
        return None

# === ФУНКЦИИ ДЛЯ РАБОТЫ С КОНТАКТАМИ ===

async def init_contacts():
    """Инициализация контактов по умолчанию"""
    try:
        # Проверяем, есть ли уже контакты
        existing = await db_pool.execute_fetchone("SELECT id FROM contacts WHERE contact_type = 'booking'")
        if existing:
            return
        
        # Создаем контакт по умолчанию
        await db_pool.execute(
            """INSERT OR IGNORE INTO contacts (contact_type, name, phone, telegram_username) 
               VALUES (?, ?, ?, ?)""",
            ('booking', 'Денис', '+7 919 634-90-91', 'olimp_auto')
        )
        await db_pool.commit()
    except Exception as e:
        logger.warning(f"Ошибка при инициализации контактов: {e}")

async def get_contact(contact_type: str = 'booking') -> Optional[Dict[str, Any]]:
    """Получает контакт по типу"""
    try:
        return await db_pool.execute_fetchone(
            "SELECT * FROM contacts WHERE contact_type = ?",
            (contact_type,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении контакта: {e}")
        return None

async def update_contact(contact_type: str, name: Optional[str] = None, 
                        phone: Optional[str] = None, telegram_username: Optional[str] = None,
                        telegram_id: Optional[int] = None) -> bool:
    """Обновляет контакт"""
    try:
        # Проверяем, существует ли контакт
        existing = await get_contact(contact_type)
        
        if existing:
            # Обновляем существующий
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if phone is not None:
                updates.append("phone = ?")
                params.append(phone)
            if telegram_username is not None:
                updates.append("telegram_username = ?")
                params.append(telegram_username)
            if telegram_id is not None:
                updates.append("telegram_id = ?")
                params.append(telegram_id)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(contact_type)
                
                query = f"UPDATE contacts SET {', '.join(updates)} WHERE contact_type = ?"
                await db_pool.execute(query, tuple(params))
        else:
            # Создаем новый
            await db_pool.execute(
                """INSERT INTO contacts (contact_type, name, phone, telegram_username, telegram_id) 
                   VALUES (?, ?, ?, ?, ?)""",
                (contact_type, name, phone, telegram_username, telegram_id)
            )
        
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении контакта: {e}")
        return False

# === МОДУЛЬ 2: ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАМЕТКАМИ О ПОЛЬЗОВАТЕЛЯХ ===

async def add_user_note(user_id: int, admin_id: int, note_text: str) -> Optional[int]:
    """Добавляет заметку о пользователе (Модуль 2)"""
    try:
        cursor = await db_pool.execute(
            "INSERT INTO user_notes (user_id, admin_id, note_text) VALUES (?, ?, ?)",
            (user_id, admin_id, note_text)
        )
        await db_pool.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении заметки о пользователе: {e}")
        return None

async def get_user_notes(user_id: int) -> List[Dict[str, Any]]:
    """Получает все заметки о пользователе (Модуль 2)"""
    try:
        return await db_pool.execute_fetchall(
            """SELECT un.*, a.telegram_id as admin_telegram_id
               FROM user_notes un
               JOIN admins a ON un.admin_id = a.telegram_id
               WHERE un.user_id = ?
               ORDER BY un.created_at DESC""",
            (user_id,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении заметок о пользователе: {e}")
        return []

async def delete_user_note(note_id: int) -> bool:
    """Удаляет заметку о пользователе (Модуль 2)"""
    try:
        cursor = await db_pool.execute("DELETE FROM user_notes WHERE id = ?", (note_id,))
        await db_pool.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при удалении заметки: {e}")
        return False

async def get_user_by_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает пользователя по Telegram ID"""
    try:
        return await db_pool.execute_fetchone(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        return None

# === МОДУЛЬ 3: ФУНКЦИИ ДЛЯ РАБОТЫ С ИНЦИДЕНТАМИ ===

async def add_rental_incident(rental_id: int, incident_type: str, description: str, 
                              amount: float = 0.0, photo_file_id: Optional[str] = None) -> Optional[int]:
    """Добавляет инцидент к аренде (Модуль 3)"""
    try:
        cursor = await db_pool.execute(
            """INSERT INTO rental_incidents (rental_id, incident_type, description, amount, photo_file_id) 
               VALUES (?, ?, ?, ?, ?)""",
            (rental_id, incident_type, description, amount, photo_file_id)
        )
        await db_pool.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении инцидента: {e}")
        return None

async def get_rental_incidents(rental_id: int) -> List[Dict[str, Any]]:
    """Получает все инциденты по аренде (Модуль 3)"""
    try:
        return await db_pool.execute_fetchall(
            """SELECT * FROM rental_incidents 
               WHERE rental_id = ?
               ORDER BY created_at DESC""",
            (rental_id,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении инцидентов: {e}")
        return []

async def delete_rental_incident(incident_id: int) -> bool:
    """Удаляет инцидент (Модуль 3)"""
    try:
        cursor = await db_pool.execute("DELETE FROM rental_incidents WHERE id = ?", (incident_id,))
        await db_pool.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при удалении инцидента: {e}")
        return False

# === МОДУЛЬ 5: ФУНКЦИИ ДЛЯ РАБОТЫ С ЖУРНАЛОМ ОБСЛУЖИВАНИЯ ===

async def add_car_maintenance(car_id: int, entry_type: str, description: str, 
                              mileage: Optional[int] = None, event_date: str = None, 
                              reminder_date: Optional[str] = None) -> Optional[int]:
    """Добавляет запись в журнал обслуживания (Модуль 5)"""
    try:
        # Если дата события не указана, используем текущую дату
        if event_date is None:
            from datetime import date
            event_date = date.today().isoformat()
        
        cursor = await db_pool.execute(
            """INSERT INTO car_maintenance (car_id, entry_type, description, mileage, event_date, reminder_date) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (car_id, entry_type, description, mileage, event_date, reminder_date)
        )
        await db_pool.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении записи обслуживания: {e}")
        return None

async def get_car_maintenance_entries(car_id: int) -> List[Dict[str, Any]]:
    """Получает все записи обслуживания автомобиля (Модуль 5)"""
    try:
        return await db_pool.execute_fetchall(
            """SELECT * FROM car_maintenance 
               WHERE car_id = ?
               ORDER BY event_date DESC, created_at DESC""",
            (car_id,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении записей обслуживания: {e}")
        return []

async def get_maintenance_reminders_for_today() -> List[Dict[str, Any]]:
    """Получает записи обслуживания, для которых сегодня дата напоминания (Модуль 5)"""
    try:
        from datetime import date
        today = date.today().isoformat()
        
        return await db_pool.execute_fetchall(
            """SELECT cm.*, c.name as car_name
               FROM car_maintenance cm
               JOIN cars c ON cm.car_id = c.id
               WHERE cm.reminder_date = ?""",
            (today,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении напоминаний обслуживания: {e}")
        return []

async def remove_maintenance_reminder(entry_id: int) -> bool:
    """Удаляет напоминание из записи обслуживания (Модуль 5)"""
    try:
        await db_pool.execute(
            "UPDATE car_maintenance SET reminder_date = NULL WHERE id = ?",
            (entry_id,)
        )
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении напоминания: {e}")
        return False

# === МОДУЛЬ 6: ФУНКЦИИ ДЛЯ РАБОТЫ С РЕФЕРАЛЬНОЙ СИСТЕМОЙ ===

async def get_setting(setting_key: str) -> Optional[str]:
    """Получает значение настройки (Модуль 6)"""
    try:
        result = await db_pool.execute_fetchone(
            "SELECT setting_value FROM settings WHERE setting_key = ?",
            (setting_key,)
        )
        return result['setting_value'] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении настройки: {e}")
        return None

async def set_setting(setting_key: str, setting_value: str) -> bool:
    """Устанавливает значение настройки (Модуль 6)"""
    try:
        await db_pool.execute(
            """INSERT OR REPLACE INTO settings (setting_key, setting_value, updated_at) 
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (setting_key, setting_value)
        )
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке настройки: {e}")
        return False

async def generate_referral_code(telegram_id: int) -> str:
    """Генерирует уникальный реферальный код для пользователя (Модуль 6)"""
    import random
    import string
    
    # Формируем код: user_id + случайная строка из 6 символов
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    code = f"{telegram_id}{random_part}"
    
    # Проверяем уникальность
    try:
        existing = await db_pool.execute_fetchone(
            "SELECT id FROM users WHERE referral_code = ?",
            (code,)
        )
        if existing:
            # Если код уже существует, генерируем новый
            return await generate_referral_code(telegram_id)
    except:
        pass
    
    return code

async def ensure_user_referral_code(telegram_id: int) -> str:
    """Гарантирует, что у пользователя есть реферальный код (Модуль 6)"""
    try:
        user = await get_user_by_id(telegram_id)
        if not user:
            return None
        
        referral_code = user.get('referral_code')
        if referral_code:
            return referral_code
        
        # Генерируем новый код
        new_code = await generate_referral_code(telegram_id)
        await db_pool.execute(
            "UPDATE users SET referral_code = ? WHERE telegram_id = ?",
            (new_code, telegram_id)
        )
        await db_pool.commit()
        return new_code
    except Exception as e:
        logger.error(f"Ошибка при генерации реферального кода: {e}")
        return None

async def get_user_by_referral_code(referral_code: str) -> Optional[Dict[str, Any]]:
    """Получает пользователя по реферальному коду (Модуль 6)"""
    try:
        return await db_pool.execute_fetchone(
            "SELECT * FROM users WHERE referral_code = ?",
            (referral_code,)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя по реферальному коду: {e}")
        return None

async def set_user_referrer(user_id: int, referrer_id: int) -> bool:
    """Устанавливает реферера для пользователя (Модуль 6)"""
    try:
        await db_pool.execute(
            "UPDATE users SET referrer_id = ? WHERE telegram_id = ? AND referrer_id IS NULL",
            (referrer_id, user_id)
        )
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке реферера: {e}")
        return False

async def get_referral_stats() -> Dict[str, Any]:
    """Получает статистику реферальной системы (Модуль 6)"""
    try:
        # Количество пользователей с реферерами
        result = await db_pool.execute_fetchone(
            "SELECT COUNT(*) as count FROM users WHERE referrer_id IS NOT NULL"
        )
        referred_count = result['count'] if result else 0
        
        # Всего пользователей
        all_users = await get_all_users()
        total_count = len(all_users)
        
        return {
            'referred_count': referred_count,
            'total_count': total_count
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики рефералов: {e}")
        return {'referred_count': 0, 'total_count': 0}

async def update_user_source(telegram_id: int, source: str) -> bool:
    """Обновляет источник пользователя (Модуль 7) - только если еще не установлен"""
    try:
        # Проверяем, есть ли уже источник
        user = await get_user_by_id(telegram_id)
        if user and user.get('source'):
            # Источник уже установлен, не перезаписываем
            return False
        
        await db_pool.execute(
            "UPDATE users SET source = ? WHERE telegram_id = ?",
            (source, telegram_id)
        )
        await db_pool.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении источника пользователя: {e}")
        return False

async def get_users_by_source() -> Dict[str, int]:
    """Получает статистику пользователей по источникам (Модуль 7)"""
    try:
        result = await db_pool.execute_fetchall(
            "SELECT source, COUNT(*) as count FROM users WHERE source IS NOT NULL GROUP BY source"
        )
        
        stats = {}
        for row in result:
            stats[row['source']] = row['count']
        
        # Добавляем прямые переходы (пользователи без источника)
        total_with_source = sum(stats.values())
        all_users = await get_all_users()
        total_users = len(all_users)
        stats['Прямой переход'] = total_users - total_with_source
        
        return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики по источникам: {e}")
        return {}

async def check_user_referral_bonus_eligibility(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Проверяет, имеет ли пользователь право на реферальный бонус (Модуль 6)
    Бонус может быть использован только один раз (для первой аренды)
    
    Returns:
        Dict с информацией о бонусе или None, если бонус недоступен
        {'percentage': int, 'days_remaining': int}
    """
    try:
        # Проверяем, включена ли реферальная система
        referral_enabled = await get_setting('referral_system_enabled')
        if referral_enabled != 'true':
            return None
        
        # Получаем пользователя
        user = await get_user_by_id(user_id)
        if not user:
            return None
        
        # Проверяем, есть ли реферер
        referrer_id = user.get('referrer_id')
        if not referrer_id:
            return None
        
        # Проверяем, использовал ли пользователь уже бонус (если есть аренды с примененной скидкой)
        existing_rentals_with_discount = await db_pool.execute_fetchall(
            "SELECT id FROM rentals WHERE user_id = ? AND referral_discount_percentage > 0 LIMIT 1",
            (user_id,)
        )
        
        # Если пользователь уже использовал бонус, больше не может использовать
        if existing_rentals_with_discount:
            return None
        
        # Проверяем срок действия бонуса
        bonus_duration_days = int(await get_setting('referral_bonus_duration_days') or '30')
        user_created_at_str = user.get('created_at')
        
        if not user_created_at_str:
            return None
        
        try:
            from datetime import datetime as dt, date
            if isinstance(user_created_at_str, str):
                user_created_at = dt.fromisoformat(user_created_at_str.replace('Z', '+00:00'))
            else:
                user_created_at = user_created_at_str
            
            days_since_registration = (date.today() - user_created_at.date()).days
            days_remaining = bonus_duration_days - days_since_registration
            
            # Если срок действия бонуса не истек
            if days_remaining > 0:
                bonus_percentage = int(await get_setting('referral_bonus_percentage') or '10')
                return {
                    'percentage': bonus_percentage,
                    'days_remaining': days_remaining
                }
        except Exception as e:
            logger.error(f"Ошибка при проверке реферального бонуса: {e}")
        
        return None
    except Exception as e:
        logger.error(f"Ошибка при проверке права на реферальный бонус: {e}")
        return None

async def get_referral_statistics() -> Dict[str, Any]:
    """Получает расширенную статистику реферальной системы (Модуль 6)"""
    try:
        # Общая статистика
        stats = await get_referral_stats()
        
        # Количество пользователей, которые использовали бонус
        rentals_with_bonus = await db_pool.execute_fetchall(
            "SELECT COUNT(DISTINCT user_id) as count FROM rentals WHERE referral_discount_percentage > 0"
        )
        used_bonus_count = rentals_with_bonus[0]['count'] if rentals_with_bonus else 0
        
        # Общая сумма скидок (приблизительно)
        rentals_with_bonus_details = await db_pool.execute_fetchall(
            """SELECT referral_discount_percentage, daily_price 
               FROM rentals 
               WHERE referral_discount_percentage > 0"""
        )
        
        total_discount_amount = 0
        for rental in rentals_with_bonus_details:
            discount_percent = rental.get('referral_discount_percentage', 0)
            daily_price = rental.get('daily_price', 0)
            # Приблизительная сумма скидки (7 дней аренды по умолчанию)
            discount = (daily_price * discount_percent * 7) // 100
            total_discount_amount += discount
        
        return {
            'referred_count': stats.get('referred_count', 0),
            'total_count': stats.get('total_count', 0),
            'used_bonus_count': used_bonus_count,
            'total_discount_amount': total_discount_amount
        }
    except Exception as e:
        logger.error(f"Ошибка при получении расширенной статистики рефералов: {e}")
        return {'referred_count': 0, 'total_count': 0, 'used_bonus_count': 0, 'total_discount_amount': 0}

async def _init_referral_settings(db):
    """Инициализация настроек реферальной системы по умолчанию"""
    try:
        # Проверяем, есть ли уже настройки
        cursor = await db.execute("SELECT setting_key FROM settings WHERE setting_key IN (?, ?, ?)",
                                 ('referral_system_enabled', 'referral_bonus_percentage', 'referral_bonus_duration_days'))
        existing_keys = {row[0] for row in await cursor.fetchall()}
        
        # Добавляем недостающие настройки по умолчанию
        default_settings = [
            ('referral_system_enabled', 'false'),
            ('referral_bonus_percentage', '10'),
            ('referral_bonus_duration_days', '30')
        ]
        
        for key, value in default_settings:
            if key not in existing_keys:
                await db.execute("INSERT INTO settings (setting_key, setting_value) VALUES (?, ?)",
                               (key, value))
                logger.info(f"✅ Добавлена настройка реферальной системы: {key} = {value}")
    except Exception as e:
        logger.warning(f"⚠️  Ошибка при инициализации настроек реферальной системы: {e}")