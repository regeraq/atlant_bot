"""
Улучшенная конфигурация с валидацией
"""
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Класс конфигурации с валидацией"""
    
    def __init__(self):
        self.BOT_TOKEN = self._get_bot_token()
        self.DB_PATH = os.getenv('DB_PATH', 'bot_database.db')
        self.ADMIN_IDS = self._get_admin_ids()
        self.BOOKING_CONTACT_ID = self._get_booking_contact_id()
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    def _get_bot_token(self) -> str:
        """Получает токен бота с валидацией"""
        token = os.getenv('BOT_TOKEN')
        if not token:
            raise ValueError(
                "BOT_TOKEN не установлен! "
                "Установите переменную окружения BOT_TOKEN или создайте файл .env "
                "на основе .env.example"
            )
        return token
    
    def _get_admin_ids(self) -> List[int]:
        """Получает список ID администраторов"""
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        if not admin_ids_str:
            return []
        
        try:
            admin_ids = [
                int(admin_id.strip())
                for admin_id in admin_ids_str.split(',')
                if admin_id.strip()
            ]
            return admin_ids
        except ValueError as e:
            print(f"❌ Ошибка при парсинге ADMIN_IDS: {e}")
            return []
    
    def _get_booking_contact_id(self) -> Optional[int]:
        """Получает ID контакта для бронирования"""
        contact_id_str = os.getenv('BOOKING_CONTACT_ID')
        if not contact_id_str:
            return None
        
        try:
            return int(contact_id_str)
        except ValueError:
            print("❌ BOOKING_CONTACT_ID должен быть числом")
            return None


# Глобальный экземпляр конфигурации
config = Config()

# Экспортируем для обратной совместимости
BOT_TOKEN = config.BOT_TOKEN
DB_PATH = config.DB_PATH
ADMIN_IDS = config.ADMIN_IDS
BOOKING_CONTACT_ID = config.BOOKING_CONTACT_ID






