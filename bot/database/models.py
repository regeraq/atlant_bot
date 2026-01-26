# Database models

# SQL схемы для создания таблиц базы данных

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ADMINS_TABLE = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CARS_TABLE = """
CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    daily_price INTEGER NOT NULL,
    available BOOLEAN DEFAULT 1,
    image_1 TEXT,
    image_2 TEXT,
    image_3 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_RENTALS_TABLE = """
CREATE TABLE IF NOT EXISTS rentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    car_id INTEGER NOT NULL,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date DATE,
    daily_price INTEGER NOT NULL,
    reminder_time TEXT DEFAULT '12:00',
    reminder_type TEXT DEFAULT 'daily',
    last_reminder_date DATE,
    is_active BOOLEAN DEFAULT 1,
    referral_discount_percentage INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (car_id) REFERENCES cars(id)
);
"""

CREATE_CONTACTS_TABLE = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_type TEXT NOT NULL UNIQUE,
    name TEXT,
    phone TEXT,
    telegram_username TEXT,
    telegram_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Модуль 2: Заметки о пользователях (Мини-CRM)
CREATE_USER_NOTES_TABLE = """
CREATE TABLE IF NOT EXISTS user_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    admin_id INTEGER NOT NULL,
    note_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (admin_id) REFERENCES admins(telegram_id)
);
"""

# Модуль 3: Учет инцидентов (Штрафы и повреждения)
CREATE_RENTAL_INCIDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS rental_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rental_id INTEGER NOT NULL,
    incident_type TEXT NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(10, 2) DEFAULT 0,
    photo_file_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rental_id) REFERENCES rentals(id)
);
"""

# Модуль 5: Журнал обслуживания автомобилей
CREATE_CAR_MAINTENANCE_TABLE = """
CREATE TABLE IF NOT EXISTS car_maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER NOT NULL,
    entry_type TEXT NOT NULL,
    description TEXT NOT NULL,
    mileage INTEGER,
    event_date DATE NOT NULL,
    reminder_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (car_id) REFERENCES cars(id)
);
"""

# Модуль 6: Настройки реферальной системы
CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Список всех таблиц для создания
ALL_TABLES = [
    CREATE_USERS_TABLE,
    CREATE_ADMINS_TABLE,
    CREATE_CARS_TABLE,
    CREATE_RENTALS_TABLE,
    CREATE_CONTACTS_TABLE,
    CREATE_USER_NOTES_TABLE,
    CREATE_RENTAL_INCIDENTS_TABLE,
    CREATE_CAR_MAINTENANCE_TABLE,
    CREATE_SETTINGS_TABLE
]