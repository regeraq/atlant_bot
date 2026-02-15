from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict, Any

def get_admin_main_menu():
    """Создает главное меню для администраторов"""
    keyboard = [
        [KeyboardButton(text="🔧 Админ панель")],
        [KeyboardButton(text="🚗 Каталог автомобилей"), KeyboardButton(text="ℹ️ Помощь")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие"
    )

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Создает главную админ панель с цветными кнопками (Bot API 9.4)"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить автомобиль", callback_data="admin_add_car", style="primary")],
        [InlineKeyboardButton(text="📋 Управление автомобилями", callback_data="admin_manage_cars")],
        [InlineKeyboardButton(text="🚗 Управление арендой", callback_data="admin_manage_rentals")],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📞 Контакты", callback_data="admin_manage_contacts"),
            InlineKeyboardButton(text="👥 Админы", callback_data="admin_manage_admins")
        ],
        [InlineKeyboardButton(text="💾 Экспорт БД", callback_data="admin_export_db")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_cars_management_keyboard(cars: List[Dict[str, Any]], page: int = 0, cars_per_page: int = 5, callback_prefix: str = "admin_edit_car") -> InlineKeyboardMarkup:
    """Создает клавиатуру управления автомобилями для админов
    
    Args:
        cars: Список автомобилей
        page: Номер страницы
        cars_per_page: Количество автомобилей на странице
        callback_prefix: Префикс для callback_data (по умолчанию "admin_edit_car", для аренды "rental_car_select")
    """
    keyboard = []
    
    # Рассчитываем границы страницы
    start_idx = page * cars_per_page
    end_idx = min(start_idx + cars_per_page, len(cars))
    
    # Добавляем кнопки автомобилей
    for i in range(start_idx, end_idx):
        car = cars[i]
        car_name = car['name']
        price_text = f"{car['daily_price']:,}₽"
        status = "✅" if car['available'] else "❌"
        
        # Улучшенный формат кнопки
        # Формат кнопки для админов с минимальными эмодзи
        status_emoji = "✅" if car['available'] else "❌"
        button_text = f"{status_emoji} {car_name}\n💰 {price_text}/день"
        callback_data = f"{callback_prefix}:{car['id']}"
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        )])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    
    # Определяем callback для пагинации в зависимости от префикса
    if callback_prefix == "rental_car_select":
        page_callback_prefix = "rental_cars_page"
    else:
        page_callback_prefix = "admin_cars_page"
    
    # Кнопка "Предыдущая страница"
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="← Назад",
            callback_data=f"{page_callback_prefix}:{page - 1}"
        ))
    
    # Информация о странице
    total_pages = (len(cars) - 1) // cars_per_page + 1 if cars else 1
    nav_buttons.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="admin_page_info"
    ))
    
    # Кнопка "Следующая страница"
    if end_idx < len(cars):
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед →",
            callback_data=f"{page_callback_prefix}:{page + 1}"
        ))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки действий (только для управления автомобилями, не для выбора при аренде)
    if callback_prefix != "rental_car_select":
        keyboard.append([
            InlineKeyboardButton(text="➕ Добавить автомобиль", callback_data="admin_add_car", style="primary"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh_cars")
        ])
        keyboard.append([InlineKeyboardButton(
            text="🔙 Назад в админ панель",
            callback_data="back_to_admin_panel"
        )])
    else:
        # Для выбора автомобиля при аренде - только кнопка отмены
        keyboard.append([InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_action",
            style="danger"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_car_edit_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру редактирования автомобиля"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_car_name:{car_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_car_desc:{car_id}")],
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"edit_car_price:{car_id}")],
        [InlineKeyboardButton(text="🖼️ Управление фотографиями", callback_data=f"edit_car_images:{car_id}")],
        [InlineKeyboardButton(text="📊 Изменить статус", callback_data=f"edit_car_status:{car_id}")],
        [InlineKeyboardButton(text="🛠️ Журнал обслуживания", callback_data=f"car_maintenance:{car_id}")],  # Модуль 5
        [InlineKeyboardButton(text="🗑️ Удалить автомобиль", callback_data=f"delete_car:{car_id}", style="danger")],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin_manage_cars"),
            InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_car_delete_confirm_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения удаления автомобиля с цветными кнопками (Bot API 9.4)"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_car:{car_id}", style="danger"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_edit_car:{car_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_edit_car:{car_id}")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру статистики"""
    keyboard = [
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="admin_refresh_stats")],
        [InlineKeyboardButton(text="🏆 Реферальная система", callback_data="admin_referral_system")],  # Модуль 6
        [InlineKeyboardButton(text="🔙 Назад в админ панель", callback_data="back_to_admin_panel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_management_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру управления администраторами"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin")],
        [InlineKeyboardButton(text="📋 Список админов", callback_data="admin_list_admins")],
        [InlineKeyboardButton(text="🗑️ Удалить админа", callback_data="admin_delete_admin", style="danger")],
        [InlineKeyboardButton(text="🔙 Назад в админ панель", callback_data="back_to_admin_panel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_list_keyboard(admins: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком админов для удаления"""
    keyboard = []
    
    for admin in admins:
        admin_id = admin['telegram_id']
        keyboard.append([InlineKeyboardButton(
            text=f"🗑️ Удалить ID: {admin_id}",
            callback_data=f"admin_confirm_delete_admin:{admin_id}",
            style="danger"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад к управлению", callback_data="admin_manage_admins"),
        InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_delete_confirm_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления админа с цветными кнопками (Bot API 9.4)"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_confirm_delete_admin_final:{admin_id}", style="danger"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_admins")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_admins")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру отмены действия с цветными кнопками (Bot API 9.4)"""
    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action", style="danger")],
        [InlineKeyboardButton(text="🔙 Назад в админ панель", callback_data="back_to_admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_car_images_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру управления изображениями автомобиля"""
    keyboard = [
        [InlineKeyboardButton(text="📷 Загрузить изображение 1", callback_data=f"upload_image_1:{car_id}")],
        [InlineKeyboardButton(text="📷 Загрузить изображение 2", callback_data=f"upload_image_2:{car_id}")],
        [InlineKeyboardButton(text="📷 Загрузить изображение 3", callback_data=f"upload_image_3:{car_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить изображение 1", callback_data=f"delete_image_1:{car_id}", style="danger")],
        [InlineKeyboardButton(text="🗑️ Удалить изображение 2", callback_data=f"delete_image_2:{car_id}", style="danger")],
        [InlineKeyboardButton(text="🗑️ Удалить изображение 3", callback_data=f"delete_image_3:{car_id}", style="danger")],
        [
            InlineKeyboardButton(text="🔙 Назад к редактированию", callback_data=f"admin_edit_car:{car_id}"),
            InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# === КЛАВИАТУРЫ ДЛЯ РАССЫЛКИ ===

def get_broadcast_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню рассылки"""
    keyboard = [
        [InlineKeyboardButton(text="📝 Текстовое сообщение", callback_data="broadcast_text")],
        [InlineKeyboardButton(text="🖼️ С фото", callback_data="broadcast_photo")],
        [InlineKeyboardButton(text="🎥 С видео", callback_data="broadcast_video")],
        [InlineKeyboardButton(text="📎 С документом", callback_data="broadcast_document")],
        [InlineKeyboardButton(text="📊 История рассылок", callback_data="broadcast_history")],
        [InlineKeyboardButton(text="🔙 Назад в админ панель", callback_data="back_to_admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_content_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления содержимым рассылки с цветными кнопками (Bot API 9.4)"""
    keyboard = [
        [InlineKeyboardButton(text="👁️ Предварительный просмотр", callback_data="broadcast_preview")],
        [InlineKeyboardButton(text="📢 Отправить всем", callback_data="broadcast_send_all", style="primary")],
        [
            InlineKeyboardButton(text="🔄 Начать заново", callback_data="broadcast_reset"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast", style="danger")
        ],
        [InlineKeyboardButton(text="🔙 Назад в админ панель", callback_data="back_to_admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отправки рассылки с цветными кнопками (Bot API 9.4)"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, отправить", callback_data="broadcast_confirm_send", style="success"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_main", style="danger")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="broadcast_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_buttons_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления кнопками в рассылке (зарезервировано для будущей реализации)"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔙 Назад к рассылке", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_contacts_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления контактами"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="admin_contact_edit_name")],
        [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="admin_contact_edit_phone")],
        [InlineKeyboardButton(text="💬 Изменить Telegram", callback_data="admin_contact_edit_telegram")],
        [InlineKeyboardButton(text="🔙 Назад в админ панель", callback_data="back_to_admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)