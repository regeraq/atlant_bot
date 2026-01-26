"""
Конфигурация бота.

Модуль загружает и валидирует конфигурационные параметры из переменных окружения
и .env файла. Обеспечивает безопасную работу с чувствительными данными.

Использование:
    from bot.config import BOT_TOKEN, DB_PATH, ADMIN_IDS
    
    # Или через объект конфигурации
    from bot.config import config
    token = config.BOT_TOKEN
"""
import os
import logging
from pathlib import Path
from typing import List, Optional, Final
from dotenv import load_dotenv

# Настройка логирования для модуля конфигурации
logger = logging.getLogger(__name__)

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Имена переменных окружения
ENV_BOT_TOKEN: Final[str] = 'BOT_TOKEN'
ENV_DB_PATH: Final[str] = 'DB_PATH'
ENV_ADMIN_IDS: Final[str] = 'ADMIN_IDS'
ENV_BOOKING_CONTACT_ID: Final[str] = 'BOOKING_CONTACT_ID'
ENV_LOG_LEVEL: Final[str] = 'LOG_LEVEL'

# Значения по умолчанию
DEFAULT_DB_PATH: Final[str] = 'bot_database.db'
DEFAULT_LOG_LEVEL: Final[str] = 'INFO'

# Минимальная длина токена бота (примерная валидация)
MIN_BOT_TOKEN_LENGTH: Final[int] = 20

# Разделитель для списка администраторов
ADMIN_IDS_SEPARATOR: Final[str] = ','

# ============================================================================
# ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ============================================================================

def _load_env_file() -> Path:
    """
    Загружает переменные окружения из .env файла.
    
    Returns:
        Path: Путь к файлу .env
        
    Note:
        Файл .env должен находиться в корне проекта (на уровень выше bot/).
    """
    env_path = Path(__file__).parent.parent / '.env'
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        logger.debug(f"Загружен .env файл: {env_path}")
    else:
        logger.warning(
            f"Файл .env не найден по пути: {env_path}. "
            "Используются только переменные окружения системы."
        )
    
    return env_path


# Загружаем .env файл при импорте модуля
_env_file_path = _load_env_file()

# ============================================================================
# ВАЛИДАЦИЯ И ПАРСИНГ
# ============================================================================

def _validate_bot_token(token: Optional[str]) -> str:
    """
    Валидирует токен бота.
    
    Args:
        token: Токен бота из переменной окружения
        
    Returns:
        str: Валидированный токен
        
    Raises:
        ValueError: Если токен отсутствует или невалиден
    """
    if not token:
        raise ValueError(
            f"{ENV_BOT_TOKEN} не установлен! "
            "Установите переменную окружения BOT_TOKEN или создайте файл .env "
            "на основе .env.example"
        )
    
    token = token.strip()
    
    if len(token) < MIN_BOT_TOKEN_LENGTH:
        raise ValueError(
            f"{ENV_BOT_TOKEN} слишком короткий. "
            f"Минимальная длина: {MIN_BOT_TOKEN_LENGTH} символов"
        )
    
    # Базовая проверка формата токена Telegram (обычно содержит двоеточие)
    if ':' not in token:
        logger.warning(
            f"{ENV_BOT_TOKEN} имеет необычный формат. "
            "Убедитесь, что токен корректен."
        )
    
    return token


def _parse_admin_ids(admin_ids_str: Optional[str]) -> List[int]:
    """
    Парсит строку с ID администраторов в список целых чисел.
    
    Args:
        admin_ids_str: Строка с ID администраторов, разделенными запятыми
        
    Returns:
        List[int]: Список ID администраторов
        
    Note:
        Пустые значения и некорректные ID игнорируются с предупреждением.
    """
    if not admin_ids_str:
        return []
    
    admin_ids: List[int] = []
    invalid_ids: List[str] = []
    
    for admin_id_str in admin_ids_str.split(ADMIN_IDS_SEPARATOR):
        admin_id_str = admin_id_str.strip()
        
        if not admin_id_str:
            continue
        
        try:
            admin_id = int(admin_id_str)
            if admin_id > 0:  # Telegram ID всегда положительное число
                admin_ids.append(admin_id)
            else:
                invalid_ids.append(admin_id_str)
        except ValueError:
            invalid_ids.append(admin_id_str)
    
    if invalid_ids:
        logger.warning(
            f"Обнаружены некорректные ID администраторов и они будут проигнорированы: {invalid_ids}"
        )
    
    return admin_ids


def _parse_booking_contact_id(contact_id_str: Optional[str]) -> Optional[int]:
    """
    Парсит ID контакта для бронирования.
    
    Args:
        contact_id_str: Строка с ID контакта
        
    Returns:
        Optional[int]: ID контакта или None, если не указан или невалиден
        
    Note:
        Некорректные значения логируются как предупреждение, но не вызывают ошибку.
    """
    if not contact_id_str:
        return None
    
    try:
        contact_id = int(contact_id_str.strip())
        if contact_id > 0:
            return contact_id
        else:
            logger.warning(
                f"{ENV_BOOKING_CONTACT_ID} должен быть положительным числом. "
                f"Получено: {contact_id}"
            )
            return None
    except ValueError:
        logger.warning(
            f"{ENV_BOOKING_CONTACT_ID} должен быть числом. "
            f"Получено: {contact_id_str}"
        )
        return None


def _validate_db_path(db_path: str) -> str:
    """
    Валидирует путь к базе данных.
    
    Args:
        db_path: Путь к файлу базы данных
        
    Returns:
        str: Валидированный путь
        
    Note:
        Проверяет, что путь не содержит опасных символов.
    """
    db_path = db_path.strip()
    
    # Базовая проверка на опасные пути
    if '..' in db_path or db_path.startswith('/'):
        logger.warning(
            f"Путь к БД содержит потенциально опасные символы: {db_path}. "
            "Рекомендуется использовать относительные пути."
        )
    
    return db_path


# ============================================================================
# ЗАГРУЗКА КОНФИГУРАЦИИ
# ============================================================================

def _load_configuration() -> tuple[str, str, List[int], Optional[int], str]:
    """
    Загружает и валидирует всю конфигурацию.
    
    Returns:
        tuple: (BOT_TOKEN, DB_PATH, ADMIN_IDS, BOOKING_CONTACT_ID, LOG_LEVEL)
        
    Raises:
        ValueError: Если критически важные параметры невалидны
    """
    # Токен бота (обязательный)
    bot_token = _validate_bot_token(os.getenv(ENV_BOT_TOKEN))
    
    # Путь к базе данных (с значением по умолчанию)
    db_path = _validate_db_path(
        os.getenv(ENV_DB_PATH, DEFAULT_DB_PATH)
    )
    
    # ID администраторов (опционально)
    admin_ids_str = os.getenv(ENV_ADMIN_IDS, '')
    admin_ids = _parse_admin_ids(admin_ids_str)
    
    if admin_ids:
        logger.info(f"Загружено {len(admin_ids)} ID администратор(ов) из переменной окружения")
    else:
        logger.warning(
            f"{ENV_ADMIN_IDS} не установлена или пуста. "
            "Для добавления администраторов установите переменную: "
            f"export {ENV_ADMIN_IDS}='123456789,987654321'"
        )
    
    # ID контакта для бронирования (опционально)
    booking_contact_id_str = os.getenv(ENV_BOOKING_CONTACT_ID)
    booking_contact_id = _parse_booking_contact_id(booking_contact_id_str)
    
    if booking_contact_id:
        logger.info(
            f"ID контакта для бронирования загружен из переменной окружения: {booking_contact_id}"
        )
    else:
        logger.debug(
            f"{ENV_BOOKING_CONTACT_ID} не установлен. "
            "Будет загружен из базы данных при старте (см. load_booking_contact_from_db() в main.py)"
        )
    
    # Уровень логирования (с значением по умолчанию)
    log_level = os.getenv(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).strip().upper()
    
    # Валидация уровня логирования
    valid_log_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
    if log_level not in valid_log_levels:
        logger.warning(
            f"Некорректный уровень логирования: {log_level}. "
            f"Используется значение по умолчанию: {DEFAULT_LOG_LEVEL}"
        )
        log_level = DEFAULT_LOG_LEVEL
    
    return bot_token, db_path, admin_ids, booking_contact_id, log_level


# Загружаем конфигурацию при импорте модуля
try:
    BOT_TOKEN, DB_PATH, ADMIN_IDS, BOOKING_CONTACT_ID, LOG_LEVEL = _load_configuration()
except ValueError as e:
    # Критическая ошибка - не можем продолжить без токена
    logger.critical(f"Критическая ошибка конфигурации: {e}")
    raise

# ============================================================================
# НАСТРОЙКИ УВЕДОМЛЕНИЙ АДМИНИСТРАТОРУ (Модуль 1)
# ============================================================================

# Время для ежедневных уведомлений о завершающихся арендах (формат: HH:MM)
NOTIFICATION_TIME: Final[str] = os.getenv('NOTIFICATION_TIME', '10:00')

# ============================================================================
# ЭКСПОРТ ПУБЛИЧНОГО API
# ============================================================================

__all__ = [
    'BOT_TOKEN',
    'DB_PATH',
    'ADMIN_IDS',
    'BOOKING_CONTACT_ID',
    'LOG_LEVEL',
    'NOTIFICATION_TIME',
]
