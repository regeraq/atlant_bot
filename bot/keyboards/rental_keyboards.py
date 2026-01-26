"""
Клавиатуры для управления арендой
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_rentals_management_keyboard(rentals: List[Dict[str, Any]], page: int = 0, rentals_per_page: int = 5) -> InlineKeyboardMarkup:
    """Создает клавиатуру управления арендой"""
    keyboard = []
    
    # Рассчитываем границы страницы
    start_idx = page * rentals_per_page
    end_idx = min(start_idx + rentals_per_page, len(rentals))
    
    # Добавляем кнопки аренд
    for i in range(start_idx, end_idx):
        rental = rentals[i]
        car_name = rental.get('car_name', 'Неизвестный автомобиль')
        user_name = rental.get('first_name', f"ID: {rental['user_id']}")
        price = rental.get('daily_price', 0)
        
        button_text = f"{car_name}\n{user_name} • {price:,} ₽/день"
        callback_data = f"admin_rental_details:{rental['id']}"
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        )])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="← Назад",
            callback_data=f"admin_rentals_page:{page - 1}"
        ))
    
    total_pages = (len(rentals) - 1) // rentals_per_page + 1 if rentals else 1
    nav_buttons.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="admin_rentals_page_info"
    ))
    
    if end_idx < len(rentals):
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед →",
            callback_data=f"admin_rentals_page:{page + 1}"
        ))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки действий
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить аренду", callback_data="admin_add_rental"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh_rentals")
    ])
    
    keyboard.append([InlineKeyboardButton(
        text="🔙 Назад в админ панель",
        callback_data="back_to_admin_panel"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_rental_details_keyboard(rental_id: int, user_id: int = None, deposit_status: str = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру для детальной информации об аренде"""
    keyboard = [
        [InlineKeyboardButton(text="⏰ Изменить время напоминания", callback_data=f"admin_rental_reminder:{rental_id}")],
        [InlineKeyboardButton(text="📅 Изменить дату окончания", callback_data=f"admin_rental_end_date:{rental_id}")],
    ]
    
    # Добавляем кнопку заметок о пользователе, если передан user_id (Модуль 2)
    if user_id is not None:
        keyboard.append([InlineKeyboardButton(text="📝 Заметки о пользователе", callback_data=f"user_notes:{user_id}")])
    
    # Добавляем кнопку инцидентов (Модуль 3)
    keyboard.append([InlineKeyboardButton(text="🚨 Инциденты", callback_data=f"rental_incidents:{rental_id}")])
    
    # Модуль 4: Кнопки управления залогом
    if deposit_status:
        if deposit_status == 'pending':
            keyboard.append([InlineKeyboardButton(text="✅ Залог внесен", callback_data=f"deposit_paid:{rental_id}")])
        elif deposit_status == 'paid':
            keyboard.append([InlineKeyboardButton(text="↩️ Залог возвращен", callback_data=f"deposit_returned:{rental_id}")])
    
    keyboard.extend([
        [InlineKeyboardButton(text="✅ Завершить аренду", callback_data=f"admin_end_rental:{rental_id}")],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin_manage_rentals"),
            InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_rental_confirm_end_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения завершения аренды"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, завершить", callback_data=f"admin_confirm_end_rental:{rental_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_rental_details:{rental_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_rental_details:{rental_id}")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

