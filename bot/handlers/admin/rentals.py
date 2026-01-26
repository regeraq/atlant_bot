"""
Обработчики управления арендой
Полная версия с type hints и улучшенной обработкой ошибок
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from bot.database.database import (
    get_all_cars, get_car_by_id, add_rental, get_all_active_rentals,
    get_rental_by_id, get_active_rental_by_user, end_rental,
    update_rental_reminder_time, update_rental_reminder_type,
    update_rental_deposit_status, update_rental_end_date
)
from bot.database.db_pool import db_pool
from bot.keyboards.admin_keyboards import (
    get_admin_cars_management_keyboard,
    get_cancel_keyboard
)
from bot.keyboards.rental_keyboards import (
    get_rentals_management_keyboard,
    get_rental_details_keyboard,
    get_rental_confirm_end_keyboard
)
from bot.utils.helpers import safe_callback_answer
from bot.utils.errors import error_handler, NotFoundError
from bot.utils.admin_notifications import send_new_rental_notification
from .common import admin_required
from .states import RentalManagementStates

logger = logging.getLogger(__name__)


# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===

@admin_required
@error_handler
async def handle_admin_manage_rentals_callback(callback: CallbackQuery) -> None:
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
@error_handler
async def handle_admin_add_rental_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
@error_handler
async def handle_admin_rental_user_input(message: Message, state: FSMContext) -> None:
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
        
        # Получаем информацию о пользователе для отображения
        from bot.database.database import get_user_by_id as get_user
        user_info = await get_user(user_id)
        user_name = user_info.get('first_name', f"ID: {user_id}") if user_info else f"ID: {user_id}"
        
        # Создаем клавиатуру с кнопкой заметок
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        cars_keyboard = get_admin_cars_management_keyboard(cars, callback_prefix="rental_car_select")
        
        # Добавляем кнопку заметок в начало клавиатуры
        notes_button = InlineKeyboardButton(text="📝 Заметки о пользователе", callback_data=f"user_notes:{user_id}")
        cars_keyboard.inline_keyboard.insert(0, [notes_button])
        
        await message.answer(
            f"""✅ <b>Пользователь выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> {user_name}
📱 <b>Telegram ID:</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 2 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите автомобиль для аренды:</i>""",
            reply_markup=cars_keyboard,
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
@error_handler
async def handle_admin_rental_cars_page_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
@error_handler
async def handle_admin_select_car_for_rental_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор автомобиля для аренды"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_admin_rental_reminder_type_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
📝 <b>ШАГ 4 из 5</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите время напоминания в формате ЧЧ:ММ:</i>

📝 <i>Например:</i> 12:00, 09:30""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_admin_rental_reminder_time_input(message: Message, state: FSMContext) -> None:
    """Обработка ввода времени напоминания для аренды"""
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
    
    # Сохраняем время напоминания и переходим к шагу 5 (ввод залога) - Модуль 4
    await state.update_data(reminder_time=reminder_time)
    await state.set_state(RentalManagementStates.waiting_for_deposit_amount)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await message.answer(
        f"""✅ <b>Время напоминания сохранено!</b>

━━━━━━━━━━━━━━━━━━━━━━
⏰ <b>Время:</b> {reminder_time}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 5 из 5</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите сумму залога (депозита) в рублях. Если залога нет, введите 0:</i>

📝 <i>Например:</i> 50000 или 0""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )


@admin_required
@error_handler
async def handle_admin_rental_deposit_amount_input(message: Message, state: FSMContext) -> None:
    """Обработка ввода суммы залога для аренды (Модуль 4)"""
    try:
        deposit_amount = float(message.text.strip().replace(',', '.'))
        if deposit_amount < 0:
            raise ValueError("Отрицательное число")
        if deposit_amount > 99999999.99:
            raise ValueError("Сумма слишком большая")
    except ValueError as e:
        error_message = """❌ <b>НЕВЕРНЫЙ ФОРМАТ СУММЫ</b>

💡 Введите число (например: 50000 или 0):

📝 <i>Если залога нет, введите 0</i>"""
        if "слишком большая" in str(e):
            error_message = """❌ <b>СУММА СЛИШКОМ БОЛЬШАЯ</b>

💡 Максимальная сумма залога: 99 999 999.99 ₽

📝 <i>Если залога нет, введите 0</i>"""
        await message.answer(
            error_message,
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    user_id = data.get('user_id')
    car_id = data.get('car_id')
    daily_price = data.get('daily_price')
    reminder_type = data.get('reminder_type', 'daily')
    reminder_time = data.get('reminder_time', '12:00')
    
    # Определяем статус залога
    # Fix: Если залог = 0, статус не устанавливается (None)
    # Если залог > 0, статус = 'pending'
    deposit_status = 'pending' if deposit_amount > 0 else None
    
    # Вычисляем дату окончания аренды на основе типа напоминания (по умолчанию)
    # daily = 7 дней, weekly = 30 дней, monthly = 90 дней
    from datetime import date, timedelta
    rental_periods = {
        'daily': 7,
        'weekly': 30,
        'monthly': 90
    }
    period_days = rental_periods.get(reminder_type, 7)
    end_date = (date.today() + timedelta(days=period_days)).isoformat()
    
    # Модуль 6: Проверяем, есть ли у пользователя активный реферальный бонус
    referral_discount_percentage = 0
    from bot.database.database import check_user_referral_bonus_eligibility
    bonus_info = await check_user_referral_bonus_eligibility(user_id)
    
    if bonus_info:
        referral_discount_percentage = bonus_info.get('percentage', 0)
    
    # Добавляем аренду с залогом и реферальной скидкой (если есть)
    rental_id = await add_rental(
        user_id, car_id, daily_price, reminder_time, reminder_type, 
        deposit_amount, deposit_status, end_date, referral_discount_percentage
    )
    
    if rental_id:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        car = await get_car_by_id(car_id)
        car_name = car['name'] if car else 'Неизвестный автомобиль'
        
        # Получаем финальную цену с учетом скидки (из БД уже применена скидка)
        # Получаем аренду из БД, чтобы показать финальную цену
        rental = await db_pool.execute_fetchone("SELECT daily_price FROM rentals WHERE id = ?", (rental_id,))
        final_price = rental['daily_price'] if rental else daily_price
        
        type_names = {
            'daily': 'Ежедневно',
            'weekly': 'Еженедельно (7 дней)',
            'monthly': 'Ежемесячно (30 дней)'
        }
        type_name = type_names.get(reminder_type, reminder_type)
        
        # Форматируем дату окончания
        from datetime import datetime as dt
        try:
            end_date_formatted = dt.strptime(end_date, '%Y-%m-%d').strftime('%d.%m.%Y')
        except Exception:
            end_date_formatted = end_date
        
        # Формируем текст с информацией о залоге и скидке
        deposit_text = ""
        if deposit_amount > 0:
            deposit_text = f"\n💡 <b>Залог:</b> {deposit_amount:,.2f} ₽ (Статус: Ожидается)"
        
        discount_text = ""
        if referral_discount_percentage > 0:
            discount_text = f"\n🎁 <b>Реферальная скидка:</b> {referral_discount_percentage}% применена"
        
        # Вычисляем оригинальную цену для отображения, если была скидка
        original_price = daily_price
        if referral_discount_percentage > 0:
            # Если скидка применена, вычисляем оригинальную цену
            # final_price = original_price * (1 - discount/100)
            # original_price = final_price / (1 - discount/100)
            if referral_discount_percentage < 100:
                original_price = int((final_price * 100) / (100 - referral_discount_percentage))
        
        price_text = f"{final_price:,} ₽/день"
        if referral_discount_percentage > 0 and original_price > final_price:
            price_text += f" (было {original_price:,} ₽)"
        
        await message.answer(
            f"""✅ <b>АРЕНДА УСПЕШНО ДОБАВЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> <code>{user_id}</code>
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Цена:</b> {price_text}
📅 <b>Дата окончания:</b> {end_date_formatted}
⏰ <b>Время напоминания:</b> {reminder_time}
📅 <b>Частота:</b> {type_name}{deposit_text}{discount_text}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Бот будет напоминать пользователю об оплате в установленное время</i>

💡 <i>Возвращаемся к управлению арендой...</i>""",
            parse_mode='HTML'
        )
        
        # Отправляем проактивное уведомление администраторам о новой аренде (Модуль 1)
        try:
            await send_new_rental_notification(message.bot, rental_id)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администраторам о новой аренде: {e}")
        
        # Отправляем уведомление пользователю
        try:
            # Используем bot из контекста сообщения вместо создания нового экземпляра
            notification_bot = message.bot
            
            # Формируем сообщение с учетом скидки
            final_price = daily_price
            discount_text = ""
            if referral_discount_percentage > 0:
                discount = (daily_price * referral_discount_percentage) // 100
                final_price = daily_price - discount
                discount_text = f"\n🎁 <b>Реферальная скидка {referral_discount_percentage}% применена!</b>"
            
            price_text = f"{final_price:,} ₽"
            if referral_discount_percentage > 0:
                price_text += f" (было {daily_price:,} ₽)"
            
            from datetime import datetime as dt
            end_date_formatted = dt.strptime(end_date, '%Y-%m-%d').strftime('%d.%m.%Y')
            
            await notification_bot.send_message(
                chat_id=user_id,
                text=f"""🎉 <b>АРЕНДА ОФОРМЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Стоимость:</b> <code>{price_text}</code> <i>в сутки</i>
📅 <b>Дата окончания:</b> {end_date_formatted}{discount_text}
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
@error_handler
async def handle_admin_rental_details_callback(callback: CallbackQuery) -> None:
    """Детальная информация об аренде"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        raise NotFoundError(f"Аренда с ID {rental_id} не найдена")
    
    car_name = rental.get('car_name', 'Неизвестный автомобиль')
    user_name = rental.get('first_name', f"ID: {rental['user_id']}")
    daily_price = rental.get('daily_price', 0)
    reminder_time = rental.get('reminder_time', '12:00')
    reminder_type = rental.get('reminder_type', 'daily')
    start_date = rental.get('start_date', '')
    end_date = rental.get('end_date', '')
    referral_discount = rental.get('referral_discount_percentage', 0) or 0
    
    # Модуль 4: Информация о залоге
    deposit_amount = float(rental.get('deposit_amount', 0) or 0)
    deposit_status = rental.get('deposit_status', 'pending')
    status_names = {
        'pending': 'Ожидается',
        'paid': 'Внесен',
        'returned': 'Возвращен'
    }
    status_text = status_names.get(deposit_status, deposit_status)
    
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
    
    # Форматируем дату окончания
    end_date_formatted = 'Не указана'
    if end_date:
        try:
            if isinstance(end_date, str):
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_date_obj = end_date
            end_date_formatted = end_date_obj.strftime('%d.%m.%Y')
        except:
            pass
    
    # Формируем информацию о скидке
    discount_text = ""
    if referral_discount > 0:
        discount_text = f"\n🎁 <b>Реферальная скидка:</b> {referral_discount}% применена"
    
    text = f"""🚗 <b>ИНФОРМАЦИЯ ОБ АРЕНДЕ</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> {user_name}
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Цена:</b> {daily_price:,} ₽/день{discount_text}
📅 <b>Начало:</b> {start_date_formatted}
📅 <b>Окончание:</b> {end_date_formatted}
⏰ <b>Время напоминания:</b> {reminder_time}
📅 <b>Частота:</b> {type_name}
💡 <b>Залог:</b> {deposit_amount:,.2f} ₽ (Статус: {status_text})
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
    
    user_id = rental.get('user_id')
    deposit_status = rental.get('deposit_status', 'pending')
    await callback.message.edit_text(
        text,
        reply_markup=get_rental_details_keyboard(rental_id, user_id, deposit_status),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_admin_rental_reminder_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменение времени напоминания"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        raise NotFoundError(f"Аренда с ID {rental_id} не найдена")
    
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
@error_handler
async def handle_admin_rental_reminder_time_update(message: Message, state: FSMContext) -> None:
    """Обновление времени напоминания"""
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
            def __init__(self, rental_id: int, msg: Message, user):
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
@error_handler
async def handle_admin_rental_end_date_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменение даты окончания аренды"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        raise NotFoundError(f"Аренда с ID {rental_id} не найдена")
    
    await state.update_data(rental_id=rental_id)
    await state.set_state(RentalManagementStates.waiting_for_end_date)
    
    end_date = rental.get('end_date', '')
    end_date_formatted = 'Не указана'
    if end_date:
        try:
            if isinstance(end_date, str):
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_date_obj = end_date
            end_date_formatted = end_date_obj.strftime('%d.%m.%Y')
        except:
            pass
    
    await callback.message.edit_text(
        f"""📅 <b>ИЗМЕНЕНИЕ ДАТЫ ОКОНЧАНИЯ АРЕНДЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Текущая дата:</b> <code>{end_date_formatted}</code>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Отправьте новую дату в формате <code>ДД.ММ.ГГГГ</code></i>

📝 <i>Например:</i> 31.12.2024""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_admin_rental_end_date_update(message: Message, state: FSMContext) -> None:
    """Обновление даты окончания аренды"""
    date_text = message.text.strip()
    
    # Парсим дату в формате ДД.ММ.ГГГГ
    try:
        date_obj = datetime.strptime(date_text, '%d.%m.%Y')
        end_date = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        await message.answer(
            """❌ <b>НЕВЕРНЫЙ ФОРМАТ ДАТЫ</b>

💡 Отправьте дату в формате <code>ДД.ММ.ГГГГ</code>

📝 <i>Например:</i> 31.12.2024""",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    rental_id = data.get('rental_id')
    
    success = await update_rental_end_date(rental_id, end_date)
    
    if success:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>ДАТА ОКОНЧАНИЯ АРЕНДЫ ОБНОВЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Новая дата:</b> <code>{date_obj.strftime('%d.%m.%Y')}</code>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к информации об аренде...</i>""",
            parse_mode='HTML'
        )
        
        await state.clear()
        await asyncio.sleep(1)
        
        # Возвращаемся к информации об аренде
        class FakeCallback:
            def __init__(self, rental_id: int, msg: Message, user):
                self.data = f"admin_rental_details:{rental_id}"
                self.message = msg
                self.from_user = user
                
            async def answer(self, *args, **kwargs):
                pass
        
        fake_callback = FakeCallback(rental_id, message, message.from_user)
        await handle_admin_rental_details_callback(fake_callback)
    else:
        await message.answer("❌ Ошибка при обновлении даты окончания аренды")
        await state.clear()


@admin_required
@error_handler
async def handle_admin_end_rental_callback(callback: CallbackQuery) -> None:
    """Подтверждение завершения аренды"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        raise NotFoundError(f"Аренда с ID {rental_id} не найдена")
    
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
@error_handler
async def handle_admin_confirm_end_rental_callback(callback: CallbackQuery) -> None:
    """Окончательное завершение аренды"""
    rental_id = int(callback.data.split(':')[1])
    rental = await get_rental_by_id(rental_id)
    
    if not rental:
        raise NotFoundError(f"Аренда с ID {rental_id} не найдена")
    
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
@error_handler
async def handle_admin_rentals_page_callback(callback: CallbackQuery) -> None:
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
@error_handler
async def handle_admin_refresh_rentals_callback(callback: CallbackQuery) -> None:
    """Обновление списка аренд"""
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
    await safe_callback_answer(callback, "🔄 Список аренд обновлен!")


@admin_required
@error_handler
async def handle_deposit_status_change_callback(callback: CallbackQuery) -> None:
    """Обработка изменения статуса залога (Модуль 4)"""
    try:
        action, rental_id_str = callback.data.split(':')
        rental_id = int(rental_id_str)
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный ID аренды", show_alert=True)
        return
    
    # Получаем текущий статус залога для валидации переходов
    rental = await get_rental_by_id(rental_id)
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    current_status = rental.get('deposit_status')
    
    # Определяем новый статус и валидируем переход
    if action == 'deposit_paid':
        # Fix: Валидация переходов статусов - нельзя перейти из 'returned' в 'paid'
        if current_status == 'returned':
            await safe_callback_answer(callback, "❌ Невозможно изменить статус: залог уже возвращен", show_alert=True)
            return
        new_status = 'paid'
        status_text = "внесен"
    elif action == 'deposit_returned':
        # Fix: Валидация переходов статусов - можно перейти только из 'paid' в 'returned'
        if current_status != 'paid':
            await safe_callback_answer(callback, "❌ Невозможно вернуть залог: статус должен быть 'внесен'", show_alert=True)
            return
        new_status = 'returned'
        status_text = "возвращен"
    else:
        await safe_callback_answer(callback, "❌ Неизвестное действие", show_alert=True)
        return
    
    # Обновляем статус
    success = await update_rental_deposit_status(rental_id, new_status)
    
    if success:
        await safe_callback_answer(callback, f"✅ Залог {status_text}!", show_alert=False)
        
        # Возвращаемся к информации об аренде
        class FakeCallback:
            def __init__(self, rental_id: int, msg, user):
                self.data = f"admin_rental_details:{rental_id}"
                self.message = msg
                self.from_user = user
                
            async def answer(self, **kwargs):
                pass
        
        fake_callback = FakeCallback(rental_id, callback.message, callback.from_user)
        await handle_admin_rental_details_callback(fake_callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при обновлении статуса залога", show_alert=True)


# Экспортируем функции
__all__ = [
    'handle_admin_manage_rentals_callback',
    'handle_admin_add_rental_callback',
    'handle_admin_rental_user_input',
    'handle_admin_select_car_for_rental_callback',
    'handle_admin_rental_cars_page_callback',
    'handle_admin_rental_reminder_type_callback',
    'handle_admin_rental_reminder_time_input',
    'handle_admin_rental_reminder_time_update',
    'handle_admin_rental_deposit_amount_input',
    'handle_admin_rental_details_callback',
    'handle_admin_rental_reminder_callback',
    'handle_admin_rental_end_date_callback',
    'handle_admin_rental_end_date_update',
    'handle_admin_end_rental_callback',
    'handle_admin_confirm_end_rental_callback',
    'handle_admin_rentals_page_callback',
    'handle_admin_refresh_rentals_callback',
    'handle_deposit_status_change_callback',
]
