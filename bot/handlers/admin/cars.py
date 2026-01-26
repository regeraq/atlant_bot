"""
Обработчики управления автомобилями
Полная версия с type hints и улучшенной обработкой ошибок
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from bot.database.database import (
    get_all_cars, get_car_by_id, add_car, update_car, delete_car
)
from bot.database.db_pool import db_pool
from bot.keyboards.admin_keyboards import (
    get_admin_cars_management_keyboard,
    get_car_edit_keyboard,
    get_car_delete_confirm_keyboard,
    get_cancel_keyboard,
    get_car_images_keyboard,
    get_admin_panel_keyboard
)
from bot.utils.helpers import safe_callback_answer
from bot.utils.notifications import send_new_car_notification
from bot.utils.errors import error_handler, NotFoundError
from .common import admin_required
from .states import CarCreationStates, CarEditStates, CarImageStates

logger = logging.getLogger(__name__)


# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===

@admin_required
@error_handler
async def handle_admin_manage_cars_callback(callback: CallbackQuery) -> None:
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
@error_handler
async def handle_admin_cars_page_callback(callback: CallbackQuery) -> None:
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
@error_handler
async def handle_admin_edit_car_callback(callback: CallbackQuery) -> None:
    """Обработчик редактирования автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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


# === СОЗДАНИЕ АВТОМОБИЛЯ ===

@admin_required
@error_handler
async def handle_admin_add_car_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
@error_handler
async def handle_car_name_input(message: Message, state: FSMContext) -> None:
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
@error_handler
async def handle_car_description_input(message: Message, state: FSMContext) -> None:
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
@error_handler
async def handle_car_price_input(message: Message, state: FSMContext, bot: Bot) -> None:
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


# === РЕДАКТИРОВАНИЕ АВТОМОБИЛЕЙ ===

@admin_required
@error_handler
async def handle_edit_car_name_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования названия автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_edit_car_desc_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования описания автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_edit_car_price_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования цены автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_new_car_name_input(message: Message, state: FSMContext) -> None:
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
            def __init__(self, car_id: int, msg: Message, user):
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
@error_handler
async def handle_new_car_desc_input(message: Message, state: FSMContext) -> None:
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
            def __init__(self, car_id: int, msg: Message):
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
@error_handler
async def handle_new_car_price_input(message: Message, state: FSMContext) -> None:
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
            def __init__(self, car_id: int, msg: Message):
                self.data = f"admin_edit_car:{car_id}"
                self.message = msg
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(car_id, message)
        await handle_admin_edit_car_callback(fake_callback)
    else:
        await message.answer("❌ Ошибка при обновлении цены")
        await state.clear()


# === УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ ===

@admin_required
@error_handler
async def handle_edit_car_images_callback(callback: CallbackQuery) -> None:
    """Обработчик управления изображениями автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_upload_image_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
@error_handler
async def handle_delete_image_callback(callback: CallbackQuery) -> None:
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

async def handle_image_upload(message: Message, state: FSMContext, image_slot: str, bot: Optional[Bot] = None) -> None:
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


async def handle_car_images_complete(message: Message, state: FSMContext, bot: Optional[Bot]) -> None:
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


@admin_required
@error_handler
async def handle_car_image_1_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработчик загрузки первого изображения"""
    await handle_image_upload(message, state, "1", bot)


@admin_required
@error_handler
async def handle_car_image_2_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработчик загрузки второго изображения"""
    await handle_image_upload(message, state, "2", bot)


@admin_required
@error_handler
async def handle_car_image_3_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработчик загрузки третьего изображения"""
    await handle_image_upload(message, state, "3", bot)


# === ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ФОТОГРАФИЙ ПРИ СОЗДАНИИ АВТОМОБИЛЯ ===

@admin_required
@error_handler
async def handle_car_add_images_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
@error_handler
async def handle_car_skip_images_callback(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
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
@error_handler
async def handle_car_broadcast_yes_callback(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
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
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_car_broadcast_no_callback(callback: CallbackQuery, state: FSMContext) -> None:
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


# === УДАЛЕНИЕ АВТОМОБИЛЯ ===

@admin_required
@error_handler
async def handle_delete_car_callback(callback: CallbackQuery) -> None:
    """Обработчик подтверждения удаления автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
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
@error_handler
async def handle_confirm_delete_car_callback(callback: CallbackQuery) -> None:
    """Подтверждение удаления автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
    car_name = car['name']
    
    # Проверяем наличие активных аренд
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
            def __init__(self, msg: Message, user):
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


# === ИЗМЕНЕНИЕ СТАТУСА ===

@admin_required
@error_handler
async def handle_edit_car_status_callback(callback: CallbackQuery) -> None:
    """Переключение статуса автомобиля (доступен/недоступен)"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        raise NotFoundError(f"Автомобиль с ID {car_id} не найден")
    
    # Переключаем статус
    new_status = not car['available']
    
    if await update_car(car_id, available=new_status):
        status_text = "доступен" if new_status else "недоступен"
        await safe_callback_answer(callback, f"✅ Статус изменен: автомобиль теперь {status_text}")
        
        # Обновляем информацию об автомобиле
        await handle_admin_edit_car_callback(callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при изменении статуса", show_alert=True)


# === ОБНОВЛЕНИЕ СПИСКА ===

@admin_required
@error_handler
async def handle_admin_refresh_cars_callback(callback: CallbackQuery) -> None:
    """Обновление списка автомобилей"""
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


# Экспортируем функции
__all__ = [
    'handle_admin_manage_cars_callback',
    'handle_admin_cars_page_callback',
    'handle_admin_edit_car_callback',
    'handle_admin_add_car_callback',
    'handle_car_name_input',
    'handle_car_description_input',
    'handle_car_price_input',
    'handle_edit_car_name_callback',
    'handle_edit_car_desc_callback',
    'handle_edit_car_price_callback',
    'handle_new_car_name_input',
    'handle_new_car_desc_input',
    'handle_new_car_price_input',
    'handle_edit_car_images_callback',
    'handle_upload_image_callback',
    'handle_delete_image_callback',
    'handle_car_image_1_input',
    'handle_car_image_2_input',
    'handle_car_image_3_input',
    'handle_car_add_images_callback',
    'handle_car_skip_images_callback',
    'handle_car_broadcast_yes_callback',
    'handle_car_broadcast_no_callback',
    'handle_delete_car_callback',
    'handle_confirm_delete_car_callback',
    'handle_edit_car_status_callback',
    'handle_admin_refresh_cars_callback',
]
