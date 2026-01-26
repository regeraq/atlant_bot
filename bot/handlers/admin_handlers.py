from aiogram import types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError, TelegramForbiddenError
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from bot.database.database import (
    is_admin, get_all_cars, get_car_by_id, add_car, update_car, delete_car,
    get_all_users, get_all_admins, add_admin, delete_admin,
    add_rental, get_all_active_rentals, end_rental, update_rental_reminder_time,
    get_rental_by_id, get_active_rental_by_user, get_contact, update_contact
)

from bot.keyboards.admin_keyboards import (
    get_admin_panel_keyboard, get_admin_cars_management_keyboard,
    get_car_edit_keyboard, get_car_delete_confirm_keyboard,
    get_admin_stats_keyboard, get_admin_management_keyboard,
    get_cancel_keyboard, get_admin_main_menu, get_car_images_keyboard,
    get_admin_list_keyboard, get_admin_delete_confirm_keyboard,
    get_contacts_management_keyboard
)
from bot.keyboards.rental_keyboards import (
    get_rentals_management_keyboard, get_rental_details_keyboard,
    get_rental_confirm_end_keyboard
)
from bot.keyboards.user_keyboards import get_main_menu
from bot.utils.notifications import send_new_car_notification
from bot.utils.helpers import safe_callback_answer

# FSM States для добавления и редактирования автомобилей
class CarCreationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_images = State()
    waiting_for_broadcast_decision = State()

class CarEditStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_description = State()
    waiting_for_new_price = State()

class AdminManagementStates(StatesGroup):
    waiting_for_admin_id = State()

class CarImageStates(StatesGroup):
    waiting_for_image_1 = State()
    waiting_for_image_2 = State()
    waiting_for_image_3 = State()

class RentalManagementStates(StatesGroup):
    waiting_for_user_input = State()
    waiting_for_car_selection = State()
    waiting_for_reminder_type = State()
    waiting_for_reminder_time = State()

class ContactManagementStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_telegram = State()

# Декоратор для проверки прав администратора
def admin_required(func):
    async def wrapper(message_or_callback, *args, **kwargs):
        user_id = message_or_callback.from_user.id if message_or_callback.from_user else None
        if not user_id or not await is_admin(user_id):
            if isinstance(message_or_callback, CallbackQuery):
                await safe_callback_answer(message_or_callback, "❌ У вас нет прав администратора", show_alert=True)
            else:
                await message_or_callback.answer(
                    "❌ У вас нет прав администратора.\n\nЭта функция доступна только для администраторов.",
                    reply_markup=get_main_menu()
                )
            return
        return await func(message_or_callback, *args, **kwargs)
    return wrapper

@admin_required
async def handle_admin_panel_button(message: Message):
    """Обработчик кнопки 'Админ панель'"""
    from bot.database.database import get_all_cars, get_all_users, get_all_active_rentals
    
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
    from bot.database.database import get_all_cars, get_all_users, get_all_active_rentals
    
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

@admin_required
async def handle_admin_manage_cars_callback(callback: CallbackQuery):
    """Обработчик управления автомобилями"""
    cars = await get_all_cars()
    
    if not cars:
        text = """📋 <b>УПРАВЛЕНИЕ АВТОМОБИЛЯМИ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚫 <b>В автопарке пока нет автомобилей</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Нажмите кнопку ниже, чтобы добавить первый автомобиль</i>"""
        keyboard = get_admin_cars_management_keyboard([])
    else:
        available_count = sum(1 for car in cars if car['available'])
        unavailable_count = len(cars) - available_count
        
        text = f"""📋 <b>УПРАВЛЕНИЕ АВТОМОБИЛЯМИ</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>СТАТИСТИКА</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Всего автомобилей: <b>{len(cars)}</b>
✅ Доступных: <b>{available_count}</b>
❌ Недоступных: <b>{unavailable_count}</b>

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите автомобиль для редактирования:</i>"""
        keyboard = get_admin_cars_management_keyboard(cars)
    
    # Пытаемся отредактировать сообщение, если не получается - отправляем новое
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение, отправляем новое: {e}")
        try:
            await callback.message.delete()
        except (TelegramBadRequest, TelegramAPIError):
            pass
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_cars_page_callback(callback: CallbackQuery):
    """Обработчик пагинации для админов"""
    page = int(callback.data.split(':')[1])
    cars = await get_all_cars()
    
    available_count = sum(1 for car in cars if car['available'])
    unavailable_count = len(cars) - available_count
    
    text = f"""📋 <b>УПРАВЛЕНИЕ АВТОМОБИЛЯМИ</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>СТАТИСТИКА</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Всего автомобилей: <b>{len(cars)}</b>
✅ Доступных: <b>{available_count}</b>
❌ Недоступных: <b>{unavailable_count}</b>

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите автомобиль для редактирования:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_cars_management_keyboard(cars, page=page),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_edit_car_callback(callback: CallbackQuery):
    """Обработчик редактирования автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    status_text = "✅ Доступен" if car['available'] else "❌ Недоступен"
    price_formatted = f"{car['daily_price']:,} ₽"
    
    text = f"""✏️ <b>РЕДАКТИРОВАНИЕ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {car['name']}
📊 <b>Статус:</b> {status_text}
💰 <b>Цена:</b> {price_formatted}/день
━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Описание:</b>
<i>{car['description'] or 'Описание отсутствует'}</i>

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите параметр для изменения:</i>"""
    
    await callback.message.answer(
        text,
        reply_markup=get_car_edit_keyboard(car_id),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_add_car_callback(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления автомобиля"""
    await callback.message.edit_text(
        """➕ <b>ДОБАВЛЕНИЕ НОВОГО АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 1 из 3</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите название автомобиля:</i>

📝 <i>Например:</i>
• BMW X5 2021
• Toyota Camry 2022
• Mercedes-Benz C-Class 2020""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(CarCreationStates.waiting_for_name)
    await safe_callback_answer(callback)

@admin_required
async def handle_car_name_input(message: Message, state: FSMContext):
    """Обработка ввода названия автомобиля"""
    car_name = message.text.strip()
    
    if len(car_name) < 3:
        await message.answer(
            """❌ <b>Название слишком короткое</b>

💡 Минимум 3 символа.
Попробуйте еще раз:""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Сохраняем название в состоянии
    await state.update_data(name=car_name)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except (TelegramBadRequest, TelegramAPIError):
        pass
    
    await message.answer(
        f"""✅ <b>Название сохранено!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {car_name}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ НОВОГО АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 2 из 3</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Теперь введите описание автомобиля:</i>

📝 <i>Опишите особенности, комплектацию, преимущества</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(CarCreationStates.waiting_for_description)

@admin_required
async def handle_car_description_input(message: Message, state: FSMContext):
    """Обработка ввода описания автомобиля"""
    description = message.text.strip()
    
    if len(description) < 10:
        await message.answer(
            """❌ <b>Описание слишком короткое</b>

💡 Минимум 10 символов.
Попробуйте еще раз:""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Сохраняем описание в состоянии
    await state.update_data(description=description)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except (TelegramBadRequest, TelegramAPIError):
        pass
    
    await message.answer(
        f"""✅ <b>Описание сохранено!</b>

━━━━━━━━━━━━━━━━━━━━━━
➕ <b>ДОБАВЛЕНИЕ НОВОГО АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 3 из 3</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите цену за день в рублях:</i>

📝 <i>Только число, например:</i>
• 5000
• 7200
• 12000""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(CarCreationStates.waiting_for_price)

@admin_required
async def handle_car_price_input(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода цены автомобиля"""
    try:
        price = int(message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        if price > 1000000:
            raise ValueError("Цена слишком большая")
    except ValueError:
        await message.answer(
            """❌ <b>Некорректная цена</b>

💡 Введите число от 1 до 1000000

📝 <i>Например:</i> 5000, 7200, 12000""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Получаем сохраненные данные
    data = await state.get_data()
    name = data['name']
    description = data['description']
    
    # Добавляем автомобиль в базу данных (по умолчанию available=True)
    car_id = await add_car(name, description, price, available=True)
    
    if car_id:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        # Сохраняем car_id в состоянии для дальнейшего использования
        await state.update_data(car_id=car_id, name=name, description=description, price=price)
        
        # Предлагаем добавить фотографии
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📷 Добавить фотографии", callback_data=f"car_add_images:{car_id}")],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"car_skip_images:{car_id}")]
        ])
        
        await message.answer(
            f"""✅ <b>АВТОМОБИЛЬ УСПЕШНО ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Хотите добавить фотографии автомобиля?</i>

📷 Вы можете добавить до 3 фотографий или пропустить этот шаг.""",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        await state.set_state(CarCreationStates.waiting_for_images)
    else:
        await message.answer(
            """❌ <b>ОШИБКА ПРИ ДОБАВЛЕНИИ АВТОМОБИЛЯ</b>

💡 Попробуйте еще раз позже.""",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode='HTML'
        )
        await state.clear()

# === ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ АВТОМОБИЛЕЙ ===

@admin_required
async def handle_edit_car_name_callback(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Сохраняем ID автомобиля в состоянии
    await state.update_data(car_id=car_id)
    
    await callback.message.edit_text(
        f"""✏️ <b>ИЗМЕНЕНИЕ НАЗВАНИЯ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Текущее название:</b> {car['name']}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новое название автомобиля:</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(CarEditStates.waiting_for_new_name)
    await safe_callback_answer(callback)

@admin_required
async def handle_edit_car_desc_callback(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования описания автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    await state.update_data(car_id=car_id)
    
    await callback.message.edit_text(
        f"""✏️ <b>ИЗМЕНЕНИЕ ОПИСАНИЯ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car['name']}
━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Текущее описание:</b>
<i>{car['description'] or 'Описание отсутствует'}</i>

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новое описание автомобиля:</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(CarEditStates.waiting_for_new_description)
    await safe_callback_answer(callback)

@admin_required
async def handle_edit_car_price_callback(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования цены автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    await state.update_data(car_id=car_id)
    
    await callback.message.edit_text(
        f"""✏️ <b>ИЗМЕНЕНИЕ ЦЕНЫ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car['name']}
💰 <b>Текущая цена:</b> {car['daily_price']:,} ₽/день
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новую цену за день в рублях:</i>

📝 <i>Только число, например:</i> 6500""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(CarEditStates.waiting_for_new_price)
    await safe_callback_answer(callback)

@admin_required
async def handle_new_car_name_input(message: Message, state: FSMContext):
    """Обработка ввода нового названия автомобиля"""
    new_name = message.text.strip()
    
    if len(new_name) < 3:
        await message.answer(
            """❌ <b>Название слишком короткое</b>

💡 Минимум 3 символа.
Попробуйте еще раз:""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Получаем ID автомобиля
    data = await state.get_data()
    car_id = data.get('car_id')
    
    if not car_id:
        await message.answer("❌ Ошибка: ID автомобиля не найден")
        await state.clear()
        return
    
    # Обновляем название в базе данных
    success = await update_car(car_id, name=new_name)
    
    if success:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>НАЗВАНИЕ УСПЕШНО ИЗМЕНЕНО!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Новое название:</b> {new_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к редактированию автомобиля...</i>""",
            parse_mode='HTML'
        )
        
        # Возвращаемся к карточке автомобиля
        await state.clear()
        await asyncio.sleep(1)
        
        # Имитируем callback для возврата к редактированию
        class FakeCallback:
            def __init__(self, car_id, msg, user):
                self.data = f"admin_edit_car:{car_id}"
                self.message = msg
                self.from_user = user
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(car_id, message, message.from_user)
        await handle_admin_edit_car_callback(fake_callback)
    else:
        await message.answer("❌ Ошибка при обновлении названия")
        await state.clear()

@admin_required
async def handle_new_car_desc_input(message: Message, state: FSMContext):
    """Обработка ввода нового описания автомобиля"""
    new_desc = message.text.strip()
    
    if len(new_desc) < 10:
        await message.answer(
            """❌ <b>Описание слишком короткое</b>

💡 Минимум 10 символов.
Попробуйте еще раз:""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    car_id = data.get('car_id')
    
    if not car_id:
        await message.answer("❌ Ошибка: ID автомобиля не найден")
        await state.clear()
        return
    
    success = await update_car(car_id, description=new_desc)
    
    if success:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>ОПИСАНИЕ УСПЕШНО ИЗМЕНЕНО!</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Возвращаемся к редактированию автомобиля...</i>""",
            parse_mode='HTML'
        )
        await state.clear()
        await asyncio.sleep(1)
        
        class FakeCallback:
            def __init__(self, car_id, msg):
                self.data = f"admin_edit_car:{car_id}"
                self.message = msg
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(car_id, message)
        await handle_admin_edit_car_callback(fake_callback)
    else:
        await message.answer("❌ Ошибка при обновлении описания")
        await state.clear()

@admin_required
async def handle_new_car_price_input(message: Message, state: FSMContext):
    """Обработка ввода новой цены автомобиля"""
    try:
        new_price = int(message.text.strip())
        if new_price <= 0:
            raise ValueError("Цена должна быть положительной")
        if new_price > 1000000:
            raise ValueError("Цена слишком большая")
    except ValueError:
        await message.answer(
            """❌ <b>Некорректная цена</b>

💡 Введите число от 1 до 1000000

📝 <i>Например:</i> 5000, 7200, 12000""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    car_id = data.get('car_id')
    
    if not car_id:
        await message.answer("❌ Ошибка: ID автомобиля не найден")
        await state.clear()
        return
    
    success = await update_car(car_id, daily_price=new_price)
    
    if success:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>ЦЕНА УСПЕШНО ИЗМЕНЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Новая цена:</b> {new_price:,} ₽/день
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к редактированию автомобиля...</i>""",
            parse_mode='HTML'
        )
        await state.clear()
        await asyncio.sleep(1)
        
        class FakeCallback:
            def __init__(self, car_id, msg):
                self.data = f"admin_edit_car:{car_id}"
                self.message = msg
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(car_id, message)
        await handle_admin_edit_car_callback(fake_callback)
    else:
        await message.answer("❌ Ошибка при обновлении цены")
        await state.clear()

# === ОБРАБОТЧИК ОТМЕНЫ ДЕЙСТВИЙ ===

async def handle_cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    """Универсальный обработчик отмены действий"""
    await state.clear()
    await handle_admin_panel_callback(callback)

# === ОБРАБОТЧИКИ УПРАВЛЕНИЯ ИЗОБРАЖЕНИЯМИ ===

@admin_required
async def handle_edit_car_images_callback(callback: CallbackQuery):
    """Обработчик управления изображениями автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Формируем информацию о текущих изображениях
    images_info = []
    for i in range(1, 4):
        image_field = f"image_{i}"
        if car.get(image_field):
            images_info.append(f"📷 Изображение {i}: ✅ загружено")
        else:
            images_info.append(f"📷 Изображение {i}: ❌ не загружено")
    
    text = f"""🖼️ <b>УПРАВЛЕНИЕ ФОТОГРАФИЯМИ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car['name']}
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Статус изображений:</b>
{chr(10).join(images_info)}

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_car_images_keyboard(car_id),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_upload_image_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала загрузки изображения"""
    data = callback.data.split(':')
    image_slot = data[0].split('_')[-1]  # Получаем номер слота (1, 2, 3)
    car_id = int(data[1])
    
    # Сохраняем данные в состоянии
    await state.update_data(car_id=car_id, image_slot=image_slot)
    
    # Устанавливаем состояние ожидания изображения
    if image_slot == "1":
        await state.set_state(CarImageStates.waiting_for_image_1)
    elif image_slot == "2":
        await state.set_state(CarImageStates.waiting_for_image_2)
    else:
        await state.set_state(CarImageStates.waiting_for_image_3)
    
    await callback.message.edit_text(
        f"""📷 <b>ЗАГРУЗКА ИЗОБРАЖЕНИЯ {image_slot}</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 <b>Отправьте фотографию</b>
━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Рекомендации:</b>
• Фото должно быть хорошего качества
• Размер файла не более 20 МБ
• Формат: JPEG или PNG

💡 <i>Отправьте фото или нажмите 'Отмена'</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_delete_image_callback(callback: CallbackQuery):
    """Обработчик удаления изображения"""
    data = callback.data.split(':')
    image_slot = data[0].split('_')[-1]  # Получаем номер слота (1, 2, 3)
    car_id = int(data[1])
    
    # Обновляем автомобиль, удаляя изображение
    image_field = f"image_{image_slot}"
    update_data = {image_field: None}
    
    success = await update_car(car_id, **update_data)
    
    if success:
        await safe_callback_answer(callback, f"✅ Изображение {image_slot} удалено")
        # Возвращаемся к экрану управления изображениями
        await handle_edit_car_images_callback(callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при удалении изображения", show_alert=True)

# === FSM ОБРАБОТЧИКИ ЗАГРУЗКИ ИЗОБРАЖЕНИЙ ===

async def handle_image_upload(message: Message, state: FSMContext, image_slot: str, bot: Bot = None):
    """Универсальный обработчик загрузки изображения"""
    if not message.photo:
        await message.answer(
            """❌ <b>Пожалуйста, отправьте фотографию</b>

💡 Попробуйте еще раз или нажмите 'Отмена'.""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    car_id = data.get('car_id')
    is_creation = data.get('is_creation', False)  # Флаг создания нового автомобиля
    
    if not car_id:
        await message.answer("❌ Ошибка: данные автомобиля не найдены")
        await state.clear()
        return
    
    # Получаем file_id самого большого фото
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Обновляем автомобиль с новым изображением
    image_field = f"image_{image_slot}"
    update_data = {image_field: file_id}
    
    success = await update_car(car_id, **update_data)
    
    if success:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        # Если это создание нового автомобиля, переходим к следующему шагу
        if is_creation:
            car = await get_car_by_id(car_id)
            uploaded_count = sum(1 for i in range(1, 4) if car.get(f"image_{i}"))
            
            # Определяем следующий слот для загрузки
            next_slot = None
            for i in range(1, 4):
                if not car.get(f"image_{i}"):
                    next_slot = i
                    break
            
            if next_slot:
                # Есть еще свободные слоты
                await message.answer(
                    f"""✅ <b>Фотография {image_slot} загружена!</b>

━━━━━━━━━━━━━━━━━━━━━━
📷 Загружено фотографий: {uploaded_count}/3
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Отправьте следующую фотографию или нажмите 'Пропустить':</i>""",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"car_skip_images:{car_id}")],
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
                    ]),
                    parse_mode='HTML'
                )
                
                # Устанавливаем следующее состояние
                if next_slot == 2:
                    await state.set_state(CarImageStates.waiting_for_image_2)
                elif next_slot == 3:
                    await state.set_state(CarImageStates.waiting_for_image_3)
            else:
                # Все фотографии загружены, переходим к решению о рассылке
                await handle_car_images_complete(message, state, bot)
        else:
            # Обычное редактирование изображений
            await message.answer(
                f"""✅ <b>ИЗОБРАЖЕНИЕ {image_slot} УСПЕШНО ЗАГРУЖЕНО!</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Фотография сохранена и будет отображаться в карточке автомобиля</i>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению изображениями...</i>""",
                parse_mode='HTML'
            )
            await state.clear()
            await asyncio.sleep(1)
            
            # Возвращаемся к управлению изображениями
            car = await get_car_by_id(car_id)
            if car:
                # Формируем информацию о текущих изображениях
                images_info = []
                for i in range(1, 4):
                    img_field = f"image_{i}"
                    if car.get(img_field):
                        images_info.append(f"📷 Изображение {i}: ✅ загружено")
                    else:
                        images_info.append(f"📷 Изображение {i}: ❌ не загружено")
                
                text = f"""🖼️ <b>УПРАВЛЕНИЕ ФОТОГРАФИЯМИ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car['name']}
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Статус изображений:</b>
{chr(10).join(images_info)}

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
                
                await message.answer(
                    text,
                    reply_markup=get_car_images_keyboard(car_id),
                    parse_mode='HTML'
                )
    else:
        await message.answer(
            """❌ <b>Ошибка при сохранении изображения</b>

💡 Попробуйте еще раз или обратитесь к администратору.""",
            parse_mode='HTML'
        )

async def handle_car_images_complete(message: Message, state: FSMContext, bot: Bot):
    """Завершение загрузки фотографий при создании автомобиля"""
    data = await state.get_data()
    car_id = data.get('car_id')
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    
    # Предлагаем сделать рассылку
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data=f"car_broadcast_yes:{car_id}")],
        [InlineKeyboardButton(text="⏭️ Пропустить рассылку", callback_data=f"car_broadcast_no:{car_id}")]
    ])
    
    await message.answer(
        f"""✅ <b>ФОТОГРАФИИ ЗАГРУЖЕНЫ!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Хотите сделать рассылку о новом автомобиле всем пользователям?</i>

📢 Рассылка уведомит всех пользователей о появлении нового автомобиля в каталоге.""",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    await state.set_state(CarCreationStates.waiting_for_broadcast_decision)

async def handle_car_image_1_input(message: Message, state: FSMContext, bot: Bot):
    """Обработчик загрузки первого изображения"""
    await handle_image_upload(message, state, "1", bot)

async def handle_car_image_2_input(message: Message, state: FSMContext, bot: Bot):
    """Обработчик загрузки второго изображения"""
    await handle_image_upload(message, state, "2", bot)

async def handle_car_image_3_input(message: Message, state: FSMContext, bot: Bot):
    """Обработчик загрузки третьего изображения"""
    await handle_image_upload(message, state, "3", bot)

# === ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ФОТОГРАФИЙ ПРИ СОЗДАНИИ АВТОМОБИЛЯ ===

@admin_required
async def handle_car_add_images_callback(callback: CallbackQuery, state: FSMContext):
    """Начало добавления фотографий при создании автомобиля"""
    car_id = int(callback.data.split(':')[1])
    
    # Сохраняем car_id и флаг создания в состоянии
    await state.update_data(car_id=car_id, is_creation=True)
    
    await callback.message.edit_text(
        f"""📷 <b>ДОБАВЛЕНИЕ ФОТОГРАФИЙ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Вы можете добавить до 3 фотографий</i>

📝 <b>Рекомендации:</b>
• Фото должно быть хорошего качества
• Размер файла не более 20 МБ
• Формат: JPEG или PNG

💡 <i>Отправьте первую фотографию или нажмите 'Пропустить':</i>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"car_skip_images:{car_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]),
        parse_mode='HTML'
    )
    
    await state.set_state(CarImageStates.waiting_for_image_1)
    await safe_callback_answer(callback)

@admin_required
async def handle_car_skip_images_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Пропуск добавления фотографий и переход к решению о рассылке"""
    car_id = int(callback.data.split(':')[1])
    
    # Получаем данные автомобиля
    data = await state.get_data()
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    
    # Предлагаем сделать рассылку
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data=f"car_broadcast_yes:{car_id}")],
        [InlineKeyboardButton(text="⏭️ Пропустить рассылку", callback_data=f"car_broadcast_no:{car_id}")]
    ])
    
    await callback.message.edit_text(
        f"""✅ <b>АВТОМОБИЛЬ УСПЕШНО ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Хотите сделать рассылку о новом автомобиле всем пользователям?</i>

📢 Рассылка уведомит всех пользователей о появлении нового автомобиля в каталоге.""",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    await state.set_state(CarCreationStates.waiting_for_broadcast_decision)
    await safe_callback_answer(callback)

@admin_required
async def handle_car_broadcast_yes_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение рассылки о новом автомобиле"""
    car_id = int(callback.data.split(':')[1])
    
    # Получаем данные автомобиля
    data = await state.get_data()
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    
    # Получаем информацию об автомобиле для рассылки
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        await state.clear()
        return
    
    await callback.message.edit_text(
        "📡 <b>Рассылка началась...</b>\n\n⏳ Пожалуйста, подождите. Это может занять несколько минут.",
        parse_mode='HTML'
    )
    await safe_callback_answer(callback, "🚀 Рассылка запущена!")
    
    # Делаем рассылку
    try:
        car_data = {
            'id': car_id,
            'name': name,
            'description': description,
            'daily_price': price
        }
        
        stats = await send_new_car_notification(bot, car_data, callback.from_user.id)
        
        # Показываем результаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Управление автомобилями", callback_data="admin_manage_cars")],
            [InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")]
        ])
        
        if stats.get('total', 0) > 0:
            sent = stats.get('sent', 0)
            failed = stats.get('failed', 0)
            blocked = stats.get('blocked', 0)
            
            await callback.message.edit_text(
                f"""✅ <b>АВТОМОБИЛЬ ДОБАВЛЕН И РАССЫЛКА ЗАВЕРШЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

📢 <b>Статистика рассылки:</b>
👥 Уведомление отправлено: <b>{sent}</b> пользователям
❌ Не доставлено: <b>{failed}</b>
🚫 Заблокировали бота: <b>{blocked}</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Автомобиль добавлен в каталог и доступен для аренды</i>""",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.message.edit_text(
                f"""✅ <b>АВТОМОБИЛЬ ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

⚠️ Рассылка не выполнена (нет пользователей в системе)

💡 <i>Автомобиль добавлен в каталог и доступен для аренды</i>""",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Ошибка при рассылке: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Управление автомобилями", callback_data="admin_manage_cars")],
            [InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")]
        ])
        await callback.message.edit_text(
            f"""✅ <b>АВТОМОБИЛЬ ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

⚠️ Автомобиль добавлен успешно, но ошибка рассылки: {str(e)[:100]}

💡 <i>Автомобиль добавлен в каталог и доступен для аренды</i>""",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    await state.clear()

@admin_required
async def handle_car_broadcast_no_callback(callback: CallbackQuery, state: FSMContext):
    """Отказ от рассылки о новом автомобиле"""
    car_id = int(callback.data.split(':')[1])
    
    # Получаем данные автомобиля
    data = await state.get_data()
    name = data.get('name')
    price = data.get('price')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Управление автомобилями", callback_data="admin_manage_cars")],
        [InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")]
    ])
    
    await callback.message.edit_text(
        f"""✅ <b>АВТОМОБИЛЬ УСПЕШНО ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Название:</b> {name}
💰 <b>Цена:</b> {price:,} ₽/день
🆔 <b>ID:</b> #{car_id}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Автомобиль добавлен в каталог и доступен для аренды</i>

💡 <i>Рассылка не выполнена. Вы можете сделать её позже через управление автомобилями.</i>""",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    await state.clear()
    await safe_callback_answer(callback)

@admin_required  
async def handle_admin_stats_callback(callback: CallbackQuery):
    """Обработчик статистики"""
    cars = await get_all_cars()
    users = await get_all_users()
    admins = await get_all_admins()
    
    available_cars = sum(1 for car in cars if car['available'])
    unavailable_cars = len(cars) - available_cars
    
    # Подсчет ценовых категорий
    cheap_cars = sum(1 for car in cars if car['daily_price'] < 6000)
    medium_cars = sum(1 for car in cars if 6000 <= car['daily_price'] < 10000)
    premium_cars = sum(1 for car in cars if car['daily_price'] >= 10000)
    
    stats_text = f"""📊 <b>СТАТИСТИКА СИСТЕМЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>АВТОПАРК</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Всего автомобилей: <b>{len(cars)}</b>
✅ Доступно: <b>{available_cars}</b>
❌ Недоступно: <b>{unavailable_cars}</b>

━━━━━━━━━━━━━━━━━━━━━━
💰 <b>ПО ЦЕНОВЫМ КАТЕГОРИЯМ</b>
━━━━━━━━━━━━━━━━━━━━━━

💵 Эконом (&lt;6000₽): <b>{cheap_cars}</b>
💎 Комфорт (6000-10000₽): <b>{medium_cars}</b>
👑 Премиум (&gt;10000₽): <b>{premium_cars}</b>

━━━━━━━━━━━━━━━━━━━━━━
👥 <b>ПОЛЬЗОВАТЕЛИ</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего пользователей: <b>{len(users)}</b>
🔧 Администраторов: <b>{len(admins)}</b>

━━━━━━━━━━━━━━━━━━━━━━

📅 <i>Данные обновлены: сейчас</i>"""
    
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        stats_text,
        reply_markup=get_admin_stats_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_delete_car_callback(callback: CallbackQuery):
    """Обработчик подтверждения удаления автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    warning_text = f"""🗑️ <b>УДАЛЕНИЕ АВТОМОБИЛЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>ВНИМАНИЕ!</b> Это действие нельзя отменить.
━━━━━━━━━━━━━━━━━━━━━━

🚗 <b>Удаляемый автомобиль:</b>
• {car['name']}
• {car['daily_price']:,} ₽/день

━━━━━━━━━━━━━━━━━━━━━━

❓ <i>Вы действительно хотите удалить этот автомобиль?</i>"""
    
    await callback.message.edit_text(
        warning_text,
        reply_markup=get_car_delete_confirm_keyboard(car_id),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_confirm_delete_car_callback(callback: CallbackQuery):
    """Подтверждение удаления автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    car_name = car['name']
    
    # Проверяем наличие активных аренд
    from bot.database.db_pool import db_pool
    active_rentals = await db_pool.execute_fetchall(
        "SELECT id FROM rentals WHERE car_id = ? AND is_active = 1",
        (car_id,)
    )
    
    if active_rentals:
        # Проверяем общее количество аренд
        all_rentals = await db_pool.execute_fetchall(
            "SELECT id FROM rentals WHERE car_id = ?",
            (car_id,)
        )
        
        await callback.message.edit_text(
            f"""❌ <b>НЕВОЗМОЖНО УДАЛИТЬ АВТОМОБИЛЬ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>У этого автомобиля есть активные аренды ({len(active_rentals)})</b>
📋 Всего аренд в истории: {len(all_rentals)}

💡 <i>Сначала завершите все активные аренды, затем попробуйте удалить автомобиль снова.</i>

💡 <i>Перейдите в "Управление арендой" для завершения аренд.</i>

⚠️ <i>Примечание: После завершения всех активных аренд, при удалении автомобиля будут также удалены все записи об аренде из истории.</i>""",
            reply_markup=get_car_edit_keyboard(car_id),
            parse_mode='HTML'
        )
        await safe_callback_answer(callback, f"⚠️ У автомобиля есть {len(active_rentals)} активных аренд", show_alert=True)
        return
    
    # Удаляем автомобиль
    success = await delete_car(car_id)
    
    if success:
        await callback.message.edit_text(
            f"""✅ <b>АВТОМОБИЛЬ УДАЛЕН</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 Автомобиль <b>{car_name}</b> успешно удален из системы.
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению автопарком...</i>""",
            parse_mode='HTML'
        )
        
        # Создаем новый callback для обновления списка
        class FakeCallback:
            def __init__(self, msg, user):
                self.data = "admin_manage_cars"
                self.message = msg
                self.from_user = user
                
            async def answer(self):
                pass
        
        # Показываем обновленный список через 1 секунду
        await asyncio.sleep(1)
        fake_callback = FakeCallback(callback.message, callback.from_user)
        await handle_admin_manage_cars_callback(fake_callback)
        await safe_callback_answer(callback, f"✅ Автомобиль {car_name} удален")
    else:
        await safe_callback_answer(callback, "❌ Ошибка при удалении автомобиля", show_alert=True)

@admin_required
async def handle_edit_car_status_callback(callback: CallbackQuery):
    """Переключение статуса автомобиля (доступен/недоступен)"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Переключаем статус
    new_status = not car['available']
    
    if await update_car(car_id, available=new_status):
        status_text = "доступен" if new_status else "недоступен"
        await safe_callback_answer(callback, f"✅ Статус изменен: автомобиль теперь {status_text}")
        
        # Обновляем информацию об автомобиле
        await handle_admin_edit_car_callback(callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при изменении статуса", show_alert=True)

# === ФУНКЦИИ УПРАВЛЕНИЯ АДМИНИСТРАТОРАМИ ===

@admin_required
async def handle_admin_manage_admins_callback(callback: CallbackQuery):
    """Управление администраторами"""
    admins = await get_all_admins()
    
    text = f"""👥 <b>УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего администраторов: <b>{len(admins)}</b>
━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>Доступные действия:</b>
• ➕ Добавить нового администратора
• 📋 Просмотреть список всех администраторов
• 🗑️ Удалить администратора из системы

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_management_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_add_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления администратора"""
    await state.set_state(AdminManagementStates.waiting_for_admin_id)
    
    text = """➕ <b>ДОБАВЛЕНИЕ АДМИНИСТРАТОРА</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 <b>Отправьте Telegram ID пользователя</b>
━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Как узнать Telegram ID:</b>
• Попросите пользователя написать боту @userinfobot
• Или воспользуйтесь любым другим ID-ботом

📝 <b>Пример:</b> 123456789

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Отправьте ID или нажмите 'Отмена':</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_list_admins_callback(callback: CallbackQuery):
    """Просмотр списка всех администраторов"""
    admins = await get_all_admins()
    
    if not admins:
        text = """👥 <b>СПИСОК АДМИНИСТРАТОРОВ</b>

━━━━━━━━━━━━━━━━━━━━━━
❌ Администраторы не найдены
━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i>Это странно, должен быть хотя бы один администратор.</i>"""
    else:
        admin_list = []
        for i, admin in enumerate(admins, 1):
            admin_list.append(f"{i}. ID: <code>{admin['telegram_id']}</code>")
        
        text = f"""👥 <b>СПИСОК АДМИНИСТРАТОРОВ</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего администраторов: <b>{len(admins)}</b>
━━━━━━━━━━━━━━━━━━━━━━

📋 <b>Список:</b>
{chr(10).join(admin_list)}

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Чтобы удалить администратора, используйте функцию удаления.</i>"""
    
    # Создаем клавиатуру с кнопкой назад
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к управлению", callback_data="admin_manage_admins")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_delete_admin_callback(callback: CallbackQuery):
    """Начало процесса удаления администратора"""
    admins = await get_all_admins()
    
    if len(admins) <= 1:
        await safe_callback_answer(
            callback,
            "⚠️ Нельзя удалить последнего администратора!",
            show_alert=True
        )
        return
    
    await callback.message.edit_text(
        """🗑️ <b>УДАЛЕНИЕ АДМИНИСТРАТОРА</b>

━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>ВНИМАНИЕ!</b> Это действие нельзя отменить.
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите администратора для удаления:</i>""",
        reply_markup=get_admin_list_keyboard(admins),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_confirm_delete_admin_callback(callback: CallbackQuery):
    """Подтверждение удаления администратора"""
    admin_id = int(callback.data.split(':')[1])
    
    admins = await get_all_admins()
    if len(admins) <= 1:
        await safe_callback_answer(
            callback,
            "⚠️ Нельзя удалить последнего администратора!",
            show_alert=True
        )
        return
    
    await callback.message.edit_text(
        f"""🗑️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>ВНИМАНИЕ!</b> Это действие нельзя отменить.
━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Удаляемый администратор:</b>
ID: <code>{admin_id}</code>

━━━━━━━━━━━━━━━━━━━━━━

❓ <i>Вы действительно хотите удалить этого администратора?</i>""",
        reply_markup=get_admin_delete_confirm_keyboard(admin_id),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_confirm_delete_admin_final_callback(callback: CallbackQuery):
    """Окончательное удаление администратора"""
    admin_id = int(callback.data.split(':')[1])
    
    admins = await get_all_admins()
    if len(admins) <= 1:
        await safe_callback_answer(
            callback,
            "⚠️ Нельзя удалить последнего администратора!",
            show_alert=True
        )
        return
    
    if await delete_admin(admin_id):
        await callback.message.edit_text(
            f"""✅ <b>АДМИНИСТРАТОР УДАЛЕН</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 Администратор с ID <code>{admin_id}</code> успешно удален из системы.
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению администраторами...</i>""",
            parse_mode='HTML'
        )
        await asyncio.sleep(2)
        await handle_admin_manage_admins_callback(callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при удалении администратора", show_alert=True)

@admin_required
async def handle_admin_id_input(message: Message, state: FSMContext):
    """Обработчик ввода Telegram ID для добавления администратора"""
    try:
        # Пытаемся преобразовать в число
        admin_id = int(message.text.strip())
        
        # Проверяем, не является ли пользователь уже администратором
        if await is_admin(admin_id):
            await message.answer(
                f"""⚠️ <b>Пользователь уже является администратором</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 Пользователь с ID <code>{admin_id}</code> уже является администратором!
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Попробуйте другой ID или нажмите 'Отмена'</i>""",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Добавляем администратора
        if await add_admin(admin_id):
            # Удаляем сообщение пользователя
            try:
                await message.delete()
            except:
                pass
            
            await message.answer(
                f"""✅ <b>АДМИНИСТРАТОР УСПЕШНО ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Telegram ID:</b> <code>{admin_id}</code>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Новый администратор теперь имеет доступ к админ панели</i>

💡 <i>Возвращаемся к управлению администраторами...</i>""",
                parse_mode='HTML'
            )
            await state.clear()
            await asyncio.sleep(2)
            
            # Показываем обновленное управление администраторами
            admins = await get_all_admins()
            text = f"""👥 <b>УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего администраторов: <b>{len(admins)}</b>
━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>Доступные действия:</b>
• ➕ Добавить нового администратора
• 📋 Просмотреть список всех администраторов
• 🗑️ Удалить администратора из системы

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
            
            await message.answer(
                text,
                reply_markup=get_admin_management_keyboard(),
                parse_mode='HTML'
            )
        else:
            # Проверяем, возможно администратор уже существует (двойная проверка)
            if await is_admin(admin_id):
                await message.answer(
                    f"""⚠️ <b>Пользователь уже является администратором</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 Пользователь с ID <code>{admin_id}</code> уже является администратором!
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Попробуйте другой ID или нажмите 'Отмена'</i>""",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await message.answer(
                    """❌ <b>ОШИБКА ПРИ ДОБАВЛЕНИИ АДМИНИСТРАТОРА</b>

💡 Попробуйте еще раз или обратитесь к разработчику.""",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode='HTML'
                )
            
    except ValueError:
        await message.answer(
            """❌ <b>НЕВЕРНЫЙ ФОРМАТ ID</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 Telegram ID должен быть числом.
━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Например:</b> <code>123456789</code>

💡 <i>Попробуйте еще раз или нажмите 'Отмена':</i>""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}")
        await message.answer(
            """❌ <b>ПРОИЗОШЛА ОШИБКА</b>

💡 Попробуйте еще раз или обратитесь к разработчику.""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )

@admin_required
async def handle_admin_refresh_cars_callback(callback: CallbackQuery):
    """Обновление списка автомобилей"""
    from datetime import datetime
    
    cars = await get_all_cars()
    
    if not cars:
        current_time = datetime.now().strftime('%H:%M:%S')
        text = f"""🚫 <b>УПРАВЛЕНИЕ АВТОПАРКОМ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚫 В данный момент нет автомобилей в системе.
━━━━━━━━━━━━━━━━━━━━━━

⏰ Обновлено: {current_time}

💡 <i>Добавьте первый автомобиль, чтобы начать работу</i>"""
        keyboard = get_admin_cars_management_keyboard([])
    else:
        available_count = sum(1 for car in cars if car['available'])
        unavailable_count = len(cars) - available_count
        current_time = datetime.now().strftime('%H:%M:%S')
        
        text = f"""🚗 <b>УПРАВЛЕНИЕ АВТОПАРКОМ</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>СТАТИСТИКА</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Всего автомобилей: <b>{len(cars)}</b>
✅ Доступных: <b>{available_count}</b>
❌ Недоступных: <b>{unavailable_count}</b>

━━━━━━━━━━━━━━━━━━━━━━

⏰ Обновлено: {current_time}

💡 <i>Выберите автомобиль для редактирования или добавьте новый:</i>"""
        keyboard = get_admin_cars_management_keyboard(cars)
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    await safe_callback_answer(callback, "🔄 Список автомобилей обновлен!")

@admin_required
async def handle_admin_refresh_stats_callback(callback: CallbackQuery):
    """Обновление статистики"""
    import time
    current_time = int(time.time())
    
    # Получаем актуальные данные
    cars = await get_all_cars()
    users = await get_all_users()
    admins = await get_all_admins()
    
    # Подсчитываем статистику
    total_cars = len(cars)
    available_cars = sum(1 for car in cars if car['available'])
    unavailable_cars = total_cars - available_cars
    total_users = len(users)
    total_admins = len(admins)
    
    # Подсчет ценовых категорий
    cheap_cars = sum(1 for car in cars if car['daily_price'] < 6000)
    medium_cars = sum(1 for car in cars if 6000 <= car['daily_price'] < 10000)
    premium_cars = sum(1 for car in cars if car['daily_price'] >= 10000)
    
    text = f"""📊 <b>СТАТИСТИКА СИСТЕМЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>АВТОПАРК</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Всего автомобилей: <b>{total_cars}</b>
✅ Доступных: <b>{available_cars}</b>
❌ Недоступных: <b>{unavailable_cars}</b>

━━━━━━━━━━━━━━━━━━━━━━
💰 <b>ПО ЦЕНОВЫМ КАТЕГОРИЯМ</b>
━━━━━━━━━━━━━━━━━━━━━━

💵 Эконом (&lt;6000₽): <b>{cheap_cars}</b>
💎 Комфорт (6000-10000₽): <b>{medium_cars}</b>
👑 Премиум (&gt;10000₽): <b>{premium_cars}</b>

━━━━━━━━━━━━━━━━━━━━━━
👥 <b>ПОЛЬЗОВАТЕЛИ</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего пользователей: <b>{total_users}</b>
🔧 Администраторов: <b>{total_admins}</b>

━━━━━━━━━━━━━━━━━━━━━━

⏰ <b>Обновлено:</b> <t:{current_time}:R>

💡 <i>Нажмите кнопки ниже для управления:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_stats_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback, "📊 Статистика обновлена!")

async def handle_admin_page_info_callback(callback: CallbackQuery):
    """Информация о странице админ панели"""
    await safe_callback_answer(callback, "📄 Информация о текущей странице")

# === ОБРАБОТЧИКИ УПРАВЛЕНИЯ АРЕНДОЙ ===

@admin_required
async def handle_admin_manage_rentals_callback(callback: CallbackQuery):
    """Управление арендой"""
    rentals = await get_all_active_rentals()
    
    text = f"""🚗 <b>УПРАВЛЕНИЕ АРЕНДОЙ</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Активные аренды: {len(rentals)}</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите аренду для управления:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_rentals_management_keyboard(rentals),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_add_rental_callback(callback: CallbackQuery, state: FSMContext):
    """Добавление аренды"""
    await state.set_state(RentalManagementStates.waiting_for_user_input)
    
    await callback.message.edit_text(
        """➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 1 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите Telegram ID пользователя:</i>

📝 <i>Например:</i> 123456789""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_rental_user_input(message: Message, state: FSMContext):
    """Обработка ввода ID пользователя для аренды"""
    try:
        user_id = int(message.text.strip())
        
        # Проверяем, нет ли уже активной аренды
        existing_rental = await get_active_rental_by_user(user_id)
        if existing_rental:
            await message.answer(
                """⚠️ <b>У ПОЛЬЗОВАТЕЛЯ УЖЕ ЕСТЬ АКТИВНАЯ АРЕНДА</b>

💡 Сначала завершите текущую аренду или выберите другого пользователя.""",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
            return
        
        await state.update_data(user_id=user_id)
        
        # Получаем список ВСЕХ автомобилей (для администратора нужно показывать все, даже недоступные)
        cars = await get_all_cars(available_only=False)
        
        if not cars:
            await message.answer(
                """❌ <b>В АВТОПАРКЕ НЕТ АВТОМОБИЛЕЙ</b>

💡 Сначала добавьте автомобили в автопарк через управление автопарком.""",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
            await state.clear()
            return
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>Пользователь выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Telegram ID:</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 2 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите автомобиль для аренды:</i>""",
            reply_markup=get_admin_cars_management_keyboard(cars, callback_prefix="rental_car_select"),
            parse_mode='HTML'
        )
        await state.set_state(RentalManagementStates.waiting_for_car_selection)
        # Сохраняем список автомобилей в state для пагинации
        await state.update_data(cars_list=cars)
        
    except ValueError:
        await message.answer(
            """❌ <b>НЕВЕРНЫЙ ФОРМАТ ID</b>

💡 Введите числовой Telegram ID пользователя.""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )

@admin_required
async def handle_admin_rental_cars_page_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик пагинации при выборе автомобиля для аренды"""
    page = int(callback.data.split(':')[1])
    
    # Получаем список автомобилей из state или из базы данных
    data = await state.get_data()
    cars = data.get('cars_list')
    
    if not cars:
        # Если нет в state, получаем из базы данных
        cars = await get_all_cars(available_only=False)
        await state.update_data(cars_list=cars)
    
    if not cars:
        await safe_callback_answer(callback, "❌ В автопарке нет автомобилей", show_alert=True)
        return
    
    # Получаем user_id из state
    user_id = data.get('user_id')
    
    text = f"""✅ <b>Пользователь выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Telegram ID:</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 2 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите автомобиль для аренды:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_cars_management_keyboard(cars, page=page, callback_prefix="rental_car_select"),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_select_car_for_rental_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор автомобиля для аренды"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    await state.update_data(car_id=car_id, daily_price=car['daily_price'])
    
    await callback.message.edit_text(
        f"""✅ <b>Автомобиль выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car['name']}
💰 <b>Цена:</b> {car['daily_price']:,} ₽/день
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 3 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите частоту напоминаний об оплате:</i>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Ежедневно", callback_data="rental_reminder_type:daily")],
            [InlineKeyboardButton(text="📆 Еженедельно (7 дней)", callback_data="rental_reminder_type:weekly")],
            [InlineKeyboardButton(text="📅 Ежемесячно (30 дней)", callback_data="rental_reminder_type:monthly")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_rental_reminder_type_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор типа напоминания для аренды"""
    reminder_type = callback.data.split(':')[1]
    
    type_names = {
        'daily': 'Ежедневно',
        'weekly': 'Еженедельно (7 дней)',
        'monthly': 'Ежемесячно (30 дней)'
    }
    
    await state.update_data(reminder_type=reminder_type)
    await state.set_state(RentalManagementStates.waiting_for_reminder_time)
    
    await callback.message.edit_text(
        f"""✅ <b>Тип напоминания выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
⏰ <b>Частота:</b> {type_names.get(reminder_type, reminder_type)}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 4 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите время напоминания в формате ЧЧ:ММ:</i>

📝 <i>Например:</i> 12:00, 09:30""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_rental_reminder_time_input(message: Message, state: FSMContext):
    """Обработка ввода времени напоминания для аренды"""
    import re
    
    reminder_time = message.text.strip()
    time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    
    if not re.match(time_pattern, reminder_time):
        await message.answer(
            """❌ <b>НЕВЕРНЫЙ ФОРМАТ ВРЕМЕНИ</b>

💡 Отправьте время в формате <code>ЧЧ:ММ</code>

📝 <i>Например:</i> 12:00, 09:30""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    user_id = data.get('user_id')
    car_id = data.get('car_id')
    daily_price = data.get('daily_price')
    reminder_type = data.get('reminder_type', 'daily')
    
    # Добавляем аренду
    rental_id = await add_rental(user_id, car_id, daily_price, reminder_time, reminder_type)
    
    if rental_id:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        car = await get_car_by_id(car_id)
        car_name = car['name'] if car else 'Неизвестный автомобиль'
        
        type_names = {
            'daily': 'Ежедневно',
            'weekly': 'Еженедельно (7 дней)',
            'monthly': 'Ежемесячно (30 дней)'
        }
        type_name = type_names.get(reminder_type, reminder_type)
        
        await message.answer(
            f"""✅ <b>АРЕНДА УСПЕШНО ДОБАВЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> <code>{user_id}</code>
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Цена:</b> {daily_price:,} ₽/день
⏰ <b>Время напоминания:</b> {reminder_time}
📅 <b>Частота:</b> {type_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Бот будет напоминать пользователю об оплате в установленное время</i>

💡 <i>Возвращаемся к управлению арендой...</i>""",
            parse_mode='HTML'
        )
        
        # Отправляем уведомление пользователю
        try:
            # Используем bot из контекста сообщения вместо создания нового экземпляра
            notification_bot = message.bot
            
            await notification_bot.send_message(
                chat_id=user_id,
                text=f"""🎉 <b>АРЕНДА ОФОРМЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Стоимость:</b> <code>{daily_price:,} ₽</code> <i>в сутки</i>
⏰ <b>Напоминание об оплате:</b> {reminder_time}
📅 <b>Частота напоминаний:</b> {type_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Бот будет напоминать вам об оплате в установленное время</i>

👆 Нажмите "👤 Мой профиль" чтобы посмотреть информацию об аренде""",
                parse_mode='HTML'
            )
        except TelegramForbiddenError:
            # Пользователь заблокировал бота - это нормальная ситуация
            logger.warning(f"Пользователь {user_id} заблокировал бота, уведомление не отправлено")
        except TelegramBadRequest as e:
            logger.warning(f"Ошибка Telegram API при отправке уведомления пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления пользователю {user_id}: {e}")
        
        # Возвращаемся к управлению арендой
        await asyncio.sleep(2)
        rentals = await get_all_active_rentals()
        text = f"""🚗 <b>УПРАВЛЕНИЕ АРЕНДОЙ</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Активные аренды: {len(rentals)}</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите аренду для управления:</i>"""
        
        await message.answer(
            text,
            reply_markup=get_rentals_management_keyboard(rentals),
            parse_mode='HTML'
        )
    else:
        await message.answer(
            """❌ <b>ОШИБКА ПРИ ДОБАВЛЕНИИ АРЕНДЫ</b>

💡 Возможно, у пользователя уже есть активная аренда.""",
            parse_mode='HTML'
        )
    
    await state.clear()

@admin_required
async def handle_admin_rental_details_callback(callback: CallbackQuery):
    """Детальная информация об аренде"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    car_name = rental.get('car_name', 'Неизвестный автомобиль')
    user_name = rental.get('first_name', f"ID: {rental['user_id']}")
    daily_price = rental.get('daily_price', 0)
    reminder_time = rental.get('reminder_time', '12:00')
    reminder_type = rental.get('reminder_type', 'daily')
    start_date = rental.get('start_date', '')
    
    type_names = {
        'daily': 'Каждый день',
        'weekly': 'Каждую неделю (7 дней)',
        'monthly': 'Каждый месяц (30 дней)'
    }
    type_name = type_names.get(reminder_type, 'Каждый день')
    
    # Форматируем дату
    try:
        if start_date:
            if isinstance(start_date, str):
                start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start_date_obj = start_date
            start_date_formatted = start_date_obj.strftime('%d.%m.%Y %H:%M')
        else:
            start_date_formatted = 'Не указана'
    except:
        start_date_formatted = 'Не указана'
    
    text = f"""🚗 <b>ИНФОРМАЦИЯ ОБ АРЕНДЕ</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> {user_name}
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Цена:</b> {daily_price:,} ₽/день
📅 <b>Начало:</b> {start_date_formatted}
⏰ <b>Время напоминания:</b> {reminder_time}
📅 <b>Частота:</b> {type_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_rental_details_keyboard(rental_id),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_rental_reminder_callback(callback: CallbackQuery, state: FSMContext):
    """Изменение времени напоминания"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    await state.update_data(rental_id=rental_id)
    await state.set_state(RentalManagementStates.waiting_for_reminder_time)
    
    current_time = rental.get('reminder_time', '12:00')
    
    await callback.message.edit_text(
        f"""⏰ <b>ИЗМЕНЕНИЕ ВРЕМЕНИ НАПОМИНАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
⏰ <b>Текущее время:</b> <code>{current_time}</code>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Отправьте новое время в формате <code>ЧЧ:ММ</code></i>

📝 <i>Например:</i> 12:00 или 09:30""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_rental_reminder_time_update(message: Message, state: FSMContext):
    """Обновление времени напоминания"""
    import re
    
    reminder_time = message.text.strip()
    time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    
    if not re.match(time_pattern, reminder_time):
        await message.answer(
            """❌ <b>НЕВЕРНЫЙ ФОРМАТ ВРЕМЕНИ</b>

💡 Отправьте время в формате <code>ЧЧ:ММ</code>""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    rental_id = data.get('rental_id')
    
    success = await update_rental_reminder_time(rental_id, reminder_time)
    
    if success:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>ВРЕМЯ НАПОМИНАНИЯ ОБНОВЛЕНО!</b>

━━━━━━━━━━━━━━━━━━━━━━
⏰ <b>Новое время:</b> <code>{reminder_time}</code>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к информации об аренде...</i>""",
            parse_mode='HTML'
        )
        
        await state.clear()
        await asyncio.sleep(1)
        
        # Возвращаемся к информации об аренде
        class FakeCallback:
            def __init__(self, rental_id, msg, user):
                self.data = f"admin_rental_details:{rental_id}"
                self.message = msg
                self.from_user = user
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(rental_id, message, message.from_user)
        await handle_admin_rental_details_callback(fake_callback)
    else:
        await message.answer("❌ Ошибка при обновлении времени напоминания")
        await state.clear()

@admin_required
async def handle_admin_end_rental_callback(callback: CallbackQuery):
    """Подтверждение завершения аренды"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    car_name = rental.get('car_name', 'Неизвестный автомобиль')
    user_name = rental.get('first_name', f"ID: {rental['user_id']}")
    
    await callback.message.edit_text(
        f"""🗑️ <b>ЗАВЕРШЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>ВНИМАНИЕ!</b> Это действие нельзя отменить.
━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Пользователь:</b> {user_name}
🚗 <b>Автомобиль:</b> {car_name}

━━━━━━━━━━━━━━━━━━━━━━

❓ <i>Вы действительно хотите завершить эту аренду?</i>""",
        reply_markup=get_rental_confirm_end_keyboard(rental_id),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_confirm_end_rental_callback(callback: CallbackQuery):
    """Окончательное завершение аренды"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    user_id = rental['user_id']
    car_name = rental.get('car_name', 'Неизвестный автомобиль')
    
    success = await end_rental(rental_id)
    
    if success:
        # Отправляем уведомление пользователю
        try:
            # Используем bot из контекста callback вместо создания нового экземпляра
            notification_bot = callback.message.bot
            await notification_bot.send_message(
                chat_id=user_id,
                text=f"""📋 <b>АРЕНДА ЗАВЕРШЕНА</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>{car_name}</b>
━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Ваша аренда была завершена администратором</b>

💡 <i>Спасибо за использование нашего сервиса!</i>""",
                parse_mode='HTML'
            )
        except TelegramForbiddenError:
            # Пользователь заблокировал бота - это нормальная ситуация
            logger.warning(f"Пользователь {user_id} заблокировал бота, уведомление не отправлено")
        except TelegramBadRequest as e:
            logger.warning(f"Ошибка Telegram API при отправке уведомления пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления пользователю {user_id}: {e}")
        
        await callback.message.edit_text(
            f"""✅ <b>АРЕНДА ЗАВЕРШЕНА</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 Автомобиль: {car_name}
👤 Пользователь уведомлен
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению арендой...</i>""",
            parse_mode='HTML'
        )
        
        await asyncio.sleep(2)
        await handle_admin_manage_rentals_callback(callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при завершении аренды", show_alert=True)

@admin_required
async def handle_admin_rentals_page_callback(callback: CallbackQuery):
    """Пагинация аренд"""
    page = int(callback.data.split(':')[1])
    rentals = await get_all_active_rentals()
    
    text = f"""🚗 <b>УПРАВЛЕНИЕ АРЕНДОЙ</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Активные аренды: {len(rentals)}</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите аренду для управления:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_rentals_management_keyboard(rentals, page=page),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_refresh_rentals_callback(callback: CallbackQuery):
    """Обновление списка аренд"""
    rentals = await get_all_active_rentals()
    
    text = f"""🚗 <b>УПРАВЛЕНИЕ АРЕНДОЙ</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Активные аренды: {len(rentals)}</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите аренду для управления:</i>"""
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_rentals_management_keyboard(rentals),
            parse_mode='HTML'
        )
        await safe_callback_answer(callback, "🔄 Список аренд обновлен!")
    except TelegramBadRequest as e:
        # Игнорируем ошибку "message is not modified" - это нормально, если список не изменился
        if "not modified" in str(e).lower():
            await safe_callback_answer(callback, "📋 Список актуален")
        else:
            raise

@admin_required
async def handle_admin_export_db_callback(callback: CallbackQuery):
    """Обработчик выгрузки базы данных"""
    from bot.database.database import export_database
    from datetime import datetime
    from aiogram.types import FSInputFile
    import tempfile
    import os
    
    await safe_callback_answer(callback, "⏳ Подготовка базы данных...")
    
    # Экспортируем БД
    db_data = await export_database()
    
    if not db_data:
        await callback.message.answer(
            """❌ <b>ОШИБКА ПРИ ВЫГРУЗКЕ БАЗЫ ДАННЫХ</b>

💡 Не удалось создать резервную копию. Попробуйте позже.""",
            parse_mode='HTML'
        )
        return
    
    # Формируем имя файла с датой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bot_database_backup_{timestamp}.db"
    
    try:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            tmp_file.write(db_data)
            tmp_path = tmp_file.name
        
        # Отправляем файл
        document = FSInputFile(tmp_path, filename=filename)
        await callback.message.answer_document(
            document=document,
            caption=f"""💾 <b>Резервная копия базы данных</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Создана:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
📦 <b>Размер:</b> {len(db_data) / 1024:.2f} КБ
━━━━━━━━━━━━━━━━━━━━━━""",
            parse_mode='HTML'
        )
        
        # Удаляем временный файл
        os.unlink(tmp_path)
        
        await safe_callback_answer(callback, "✅ База данных успешно выгружена!")
        
    except Exception as e:
        await callback.message.answer(
            f"""❌ <b>ОШИБКА ПРИ ОТПРАВКЕ ФАЙЛА</b>

💡 Детали: {str(e)[:200]}""",
            parse_mode='HTML'
        )
        # Удаляем временный файл в случае ошибки
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass
