"""
Обработчики главной панели администратора
"""
import logging
from aiogram.types import Message, CallbackQuery
from bot.database.database import get_all_cars, get_all_users, get_all_active_rentals
from bot.keyboards.admin_keyboards import get_admin_panel_keyboard
from bot.utils.helpers import safe_callback_answer
from .common import admin_required

logger = logging.getLogger(__name__)


@admin_required
async def handle_admin_panel_button(message: Message):
    """Обработчик кнопки 'Админ панель'"""
    # Получаем быструю статистику
    cars = await get_all_cars()
    users = await get_all_users()
    rentals = await get_all_active_rentals()
    
    available_cars = sum(1 for car in cars if car['available'])
    
    admin_text = f"""🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>

📊 <b>Быстрая статистика:</b>
🚗 Автомобилей: <b>{len(cars)}</b> (доступно: {available_cars})
👥 Пользователей: <b>{len(users)}</b>
📝 Активных аренд: <b>{len(rentals)}</b>

📋 <b>Доступные функции:</b>
• 🚗 Управление автопарком
• 📝 Работа с арендой
• 📢 Рассылка сообщений
• 📊 Статистика и аналитика
• 👥 Управление доступом
• 📞 Управление контактами

💡 <i>Выберите действие из меню ниже</i>"""
    
    await message.answer(
        admin_text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode='HTML'
    )


@admin_required
async def handle_admin_panel_callback(callback: CallbackQuery):
    """Возврат в главную админ панель"""
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Получаем быструю статистику
    cars = await get_all_cars()
    users = await get_all_users()
    rentals = await get_all_active_rentals()
    
    available_cars = sum(1 for car in cars if car['available'])
    
    admin_text = f"""🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>БЫСТРАЯ СТАТИСТИКА</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Автомобилей: <b>{len(cars)}</b> (доступно: {available_cars})
👥 Пользователей: <b>{len(users)}</b>
📝 Активных аренд: <b>{len(rentals)}</b>

━━━━━━━━━━━━━━━━━━━━━━

📋 <b>Доступные функции:</b>
• 🚗 Управление автопарком
• 📝 Работа с арендой
• 📢 Рассылка сообщений
• 📊 Статистика и аналитика
• 👥 Управление доступом
• 📞 Управление контактами

💡 <i>Выберите действие из меню ниже</i>"""
    
    await callback.message.answer(
        admin_text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)




