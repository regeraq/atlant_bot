from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from typing import List, Dict, Any
from bot.config import BOOKING_CONTACT_ID

def get_main_menu(include_webapp: bool = True):
    """Создает главное меню для пользователей"""
    keyboard = []
    
    # Добавляем кнопку Web App, если включена
    if include_webapp:
        web_app_url = "https://regeraq.github.io/atlant_bot/"
        web_app_info = WebAppInfo(url=web_app_url)
        keyboard.append([KeyboardButton(text="🚗 Открыть гараж (Web App)", web_app=web_app_info)])
    
    keyboard.extend([
        [KeyboardButton(text="🚗 Каталог автомобилей")],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие"
    )

def get_cars_catalog_keyboard(cars: List[Dict[str, Any]], page: int = 0, cars_per_page: int = 5) -> InlineKeyboardMarkup:
    """Создает красивую клавиатуру каталога автомобилей с пагинацией (Bot API 9.4)"""
    keyboard = []
    
    # Рассчитываем границы страницы
    start_idx = page * cars_per_page
    end_idx = min(start_idx + cars_per_page, len(cars))
    
    # Добавляем кнопки автомобилей с улучшенным форматированием
    for i in range(start_idx, end_idx):
        car = cars[i]
        car_name = car['name']
        price_text = f"{car['daily_price']:,} ₽"
        
        # Улучшенный формат кнопки
        status_emoji = "🟢" if car['available'] else "🔴"
        button_text = f"{status_emoji} {car_name}\n💰 {price_text}/день"
        callback_data = f"car_details:{car['id']}"
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        )])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    
    # Кнопка "Предыдущая страница"
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="← Назад",
            callback_data=f"cars_page:{page - 1}"
        ))
    
    # Информация о странице
    total_pages = (len(cars) - 1) // cars_per_page + 1 if cars else 1
    nav_buttons.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="page_info"
    ))
    
    # Кнопка "Следующая страница"
    if end_idx < len(cars):
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед →",
            callback_data=f"cars_page:{page + 1}"
        ))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки действий
    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_cars"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_car_details_keyboard(car_id: int, is_available: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру для детальной информации о автомобиле с цветными кнопками (Bot API 9.4)"""
    keyboard = []
    
    if is_available:
        keyboard.append([InlineKeyboardButton(
            text="🚗 Забронировать",
            callback_data=f"book_car:{car_id}",
            style="primary"
        )])
        keyboard.append([InlineKeyboardButton(
            text="📞 Связаться с менеджером",
            url=f"tg://user?id={BOOKING_CONTACT_ID}" if BOOKING_CONTACT_ID else None,
            callback_data="contact_manager" if not BOOKING_CONTACT_ID else None
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="⏰ Уведомить о появлении",
            callback_data=f"notify_car:{car_id}",
            style="primary"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="← Каталог", callback_data="back_to_catalog"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_empty_catalog_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для пустого каталога"""
    keyboard = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_cars", style="primary")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_profile_keyboard(
    has_rental: bool = False,
    referral_enabled: bool = False,
    booking_contact_id: int = None
) -> InlineKeyboardMarkup:
    """Создает красивую клавиатуру профиля с цветными кнопками (Bot API 9.4)"""
    keyboard = []
    
    if has_rental:
        # Кнопки для активной аренды
        if booking_contact_id:
            keyboard.append([InlineKeyboardButton(
                text="📞 Связаться с менеджером",
                url=f"tg://user?id={booking_contact_id}",
                style="primary"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                text="📞 Связаться с менеджером",
                callback_data="contact_manager",
                style="primary"
            )])
        
        if referral_enabled:
            keyboard.append([InlineKeyboardButton(
                text="🤝 Пригласить друга",
                callback_data="user_invite_friend"
            )])
        
        keyboard.append([
            InlineKeyboardButton(text="🚗 Каталог", callback_data="back_to_catalog"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ])
    else:
        # Кнопки для пользователя без аренды
        keyboard.append([InlineKeyboardButton(
            text="🚗 Каталог автомобилей",
            callback_data="back_to_catalog",
            style="primary"
        )])
        
        if referral_enabled:
            keyboard.append([InlineKeyboardButton(
                text="🤝 Пригласить друга",
                callback_data="user_invite_friend"
            )])
        
        keyboard.append([
            InlineKeyboardButton(text="📞 Контакты", callback_data="back_to_main"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_webapp_keyboard():
    """Создает клавиатуру с кнопкой для открытия Web App"""
    # IMPORTANT: Замените URL на ваш GitHub Pages URL
    # Пример: https://yourname.github.io/atlant_bot/
    web_app_url = "https://regeraq.github.io/atlant_bot/"
    
    web_app_info = WebAppInfo(url=web_app_url)
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚗 Открыть гараж (Web App)", web_app=web_app_info)]
        ],
        resize_keyboard=True,
        persistent=True
    )