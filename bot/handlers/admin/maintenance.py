"""
Обработчики для журнала обслуживания автомобилей (Модуль 5)
"""
import logging
import re
from typing import Optional
from datetime import datetime, date
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.database.database import get_car_maintenance_entries, add_car_maintenance, get_car_by_id, remove_maintenance_reminder
from bot.keyboards.admin_keyboards import get_cancel_keyboard
from bot.utils.helpers import safe_callback_answer
from bot.utils.errors import error_handler
from .common import admin_required
from .states import MaintenanceStates

logger = logging.getLogger(__name__)


@admin_required
@error_handler
async def handle_car_maintenance_callback(callback: CallbackQuery) -> None:
    """Показывает журнал обслуживания автомобиля (Модуль 5)"""
    try:
        car_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный ID автомобиля", show_alert=True)
        return
    
    # Получаем информацию об автомобиле
    car = await get_car_by_id(car_id)
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Получаем записи обслуживания
    entries = await get_car_maintenance_entries(car_id)
    
    car_name = car.get('name', 'Неизвестный автомобиль')
    
    text = f"""🛠️ <b>ЖУРНАЛ ОБСЛУЖИВАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
━━━━━━━━━━━━━━━━━━━━━━

"""
    
    keyboard_buttons = []
    
    if entries:
        text += f"<b>Всего записей: {len(entries)}</b>\n\n"
        
        for i, entry in enumerate(entries, 1):
            entry_id = entry.get('id')
            entry_type = entry.get('entry_type', 'Неизвестно')
            description = entry.get('description', '')
            mileage = entry.get('mileage')
            event_date_str = entry.get('event_date', '')
            reminder_date_str = entry.get('reminder_date')
            
            # Форматируем дату события
            try:
                if event_date_str:
                    event_date_obj = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                    event_formatted = event_date_obj.strftime('%d.%m.%Y')
                else:
                    event_formatted = 'Не указана'
            except:
                event_formatted = 'Не указана'
            
            # Обрезаем длинный текст
            desc_short = description[:60] if len(description) > 60 else description
            if len(description) > 60:
                desc_short += "..."
            
            mileage_text = f"{mileage:,} км" if mileage else "—"
            reminder_text = "🔔 Есть напоминание" if reminder_date_str else ""
            
            text += f"<b>{i}.</b> [{entry_type.upper()}] <i>{event_formatted}</i> {reminder_text}\n"
            text += f"{desc_short}\n"
            text += f"📏 <b>Пробег:</b> {mileage_text}\n\n"
            
            # Добавляем кнопку для удаления напоминания, если оно есть
            if reminder_date_str and entry_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"🗑️ Удалить напоминание #{i}",
                        callback_data=f"maintenance_remove_reminder:{entry_id}:{car_id}",
                        style="danger"
                    )
                ])
    else:
        text += "<i>Записей пока нет</i>\n"
    
    text += "\n💡 <i>Выберите действие:</i>"
    
    # Добавляем основные кнопки
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="➕ Новая запись", callback_data=f"maintenance_add:{car_id}", style="primary")],
        [InlineKeyboardButton(text="⬅️ Назад к авто", callback_data=f"admin_edit_car:{car_id}")]
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_maintenance_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс добавления записи обслуживания (Модуль 5)"""
    try:
        car_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный ID автомобиля", show_alert=True)
        return
    
    car = await get_car_by_id(car_id)
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    await state.set_state(MaintenanceStates.waiting_for_entry_type)
    await state.update_data(car_id=car_id)
    
    car_name = car.get('name', 'Неизвестный автомобиль')
    
    await callback.message.edit_text(
        f"""➕ <b>НОВАЯ ЗАПИСЬ ОБСЛУЖИВАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите тип записи:</i>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 ТО", callback_data="maintenance_type:ТО")],
            [InlineKeyboardButton(text="🛡️ Страховка", callback_data="maintenance_type:Страховка")],
            [InlineKeyboardButton(text="🔨 Ремонт", callback_data="maintenance_type:Ремонт")],
            [InlineKeyboardButton(text="📋 Другое", callback_data="maintenance_type:Другое")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action", style="danger")]
        ]),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_maintenance_type_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор типа записи (Модуль 5)"""
    try:
        entry_type = callback.data.split(':')[1]
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный тип", show_alert=True)
        return
    
    await state.update_data(entry_type=entry_type)
    await state.set_state(MaintenanceStates.waiting_for_description)
    
    await callback.message.edit_text(
        f"""✅ <b>Тип выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Тип:</b> {entry_type.upper()}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>НОВАЯ ЗАПИСЬ ОБСЛУЖИВАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 2 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите описание:</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_maintenance_description_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод описания (Модуль 5)"""
    description = message.text.strip()
    
    if not description:
        await message.answer(
            "❌ <b>Описание не может быть пустым</b>\n\n💡 Введите описание:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await state.update_data(description=description)
    await state.set_state(MaintenanceStates.waiting_for_mileage)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await message.answer(
        f"""✅ <b>Описание сохранено!</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Описание:</b> {description[:50]}{'...' if len(description) > 50 else ''}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>НОВАЯ ЗАПИСЬ ОБСЛУЖИВАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 3 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите пробег автомобиля (км):</i>

💡 <i>Если пробег не применим, введите 0</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )


@admin_required
@error_handler
async def handle_maintenance_mileage_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод пробега (Модуль 5)"""
    try:
        mileage = int(message.text.strip())
        if mileage < 0:
            raise ValueError("Отрицательное число")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат пробега</b>\n\n💡 Введите целое число (например: 50000 или 0):",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await state.update_data(mileage=mileage if mileage > 0 else None)
    await state.set_state(MaintenanceStates.waiting_for_event_date)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await message.answer(
        f"""✅ <b>Пробег сохранен!</b>

━━━━━━━━━━━━━━━━━━━━━━
📏 <b>Пробег:</b> {mileage:,} км
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>НОВАЯ ЗАПИСЬ ОБСЛУЖИВАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 4 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите дату события в формате ДД.ММ.ГГГГ:</i>

📝 <i>Например:</i> 25.12.2024

💡 <i>Или введите "сегодня" для текущей даты</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )


@admin_required
@error_handler
async def handle_maintenance_event_date_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод даты события (Модуль 5)"""
    date_input = message.text.strip().lower()
    
    # Проверяем, не хочет ли пользователь установить напоминание
    if date_input == "сегодня":
        event_date = date.today().isoformat()
    else:
        # Парсим дату в формате ДД.ММ.ГГГГ
        date_pattern = r'^(\d{2})\.(\d{2})\.(\d{4})$'
        match = re.match(date_pattern, date_input)
        if not match:
            await message.answer(
                "❌ <b>Неверный формат даты</b>\n\n💡 Введите дату в формате <code>ДД.ММ.ГГГГ</code>:\n\n📝 <i>Например:</i> 25.12.2024",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
            return
        
        try:
            day, month, year = map(int, match.groups())
            event_date_obj = date(year, month, day)
            event_date = event_date_obj.isoformat()
        except ValueError:
            await message.answer(
                "❌ <b>Некорректная дата</b>\n\n💡 Введите корректную дату в формате <code>ДД.ММ.ГГГГ</code>:",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
            return
    
    await state.update_data(event_date=event_date)
    await state.set_state(MaintenanceStates.waiting_for_reminder_decision)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    try:
        event_date_formatted = datetime.strptime(event_date, '%Y-%m-%d').strftime('%d.%m.%Y')
    except Exception:
        event_date_formatted = event_date
    
    await message.answer(
        f"""✅ <b>Дата сохранена!</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Дата события:</b> {event_date_formatted}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Хотите установить дату напоминания?</i>

💡 <i>Напоминание будет отправлено администратору в указанную дату</i>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, установить", callback_data="maintenance_reminder_yes")],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="maintenance_reminder_no")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action", style="danger")]
        ]),
        parse_mode='HTML'
    )


@admin_required
@error_handler
async def handle_maintenance_reminder_decision_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает решение о напоминании (Модуль 5)"""
    # Callback_data имеет формат "maintenance_reminder_yes" или "maintenance_reminder_no"
    decision = 'yes' if callback.data.endswith('_yes') else 'no'
    
    data = await state.get_data()
    car_id = data.get('car_id')
    
    if decision == 'yes':
        await state.set_state(MaintenanceStates.waiting_for_reminder_date)
        await callback.message.edit_text(
            """📅 <b>УСТАНОВКА НАПОМИНАНИЯ</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Введите дату напоминания в формате ДД.ММ.ГГГГ:</i>

📝 <i>Например:</i> 25.12.2024

💡 <i>Или введите "сегодня" для текущей даты</i>""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="maintenance_reminder_no")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action", style="danger")]
            ]),
            parse_mode='HTML'
        )
    else:
        # Сохраняем запись без напоминания
        await save_maintenance_entry(callback.message, state, None)
    
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_maintenance_reminder_date_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод даты напоминания (Модуль 5)"""
    date_input = message.text.strip().lower()
    
    if date_input == "пропустить" or date_input == "⏭️ пропустить":
        await save_maintenance_entry(message, state, None)
        return
    
    if date_input == "сегодня":
        reminder_date = date.today().isoformat()
    else:
        # Парсим дату в формате ДД.ММ.ГГГГ
        date_pattern = r'^(\d{2})\.(\d{2})\.(\d{4})$'
        match = re.match(date_pattern, date_input)
        if not match:
            await message.answer(
                "❌ <b>Неверный формат даты</b>\n\n💡 Введите дату в формате <code>ДД.ММ.ГГГГ</code> или нажмите 'Пропустить':",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="maintenance_reminder_no")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action", style="danger")]
                ]),
                parse_mode='HTML'
            )
            return
        
        try:
            day, month, year = map(int, match.groups())
            reminder_date_obj = date(year, month, day)
            reminder_date = reminder_date_obj.isoformat()
        except ValueError:
            await message.answer(
                "❌ <b>Некорректная дата</b>\n\n💡 Введите корректную дату:",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
            return
    
    await save_maintenance_entry(message, state, reminder_date)


async def save_maintenance_entry(message_or_callback, state: FSMContext, reminder_date: Optional[str]) -> None:
    """Сохраняет запись обслуживания в БД (Модуль 5)"""
    data = await state.get_data()
    car_id = data.get('car_id')
    entry_type = data.get('entry_type')
    description = data.get('description')
    mileage = data.get('mileage')
    event_date = data.get('event_date')
    
    # Добавляем запись
    entry_id = await add_car_maintenance(car_id, entry_type, description, mileage, event_date, reminder_date)
    
    if entry_id:
        # Удаляем сообщение пользователя, если это Message
        if hasattr(message_or_callback, 'delete'):
            try:
                await message_or_callback.delete()
            except:
                pass
        
        # Определяем, как отправлять ответ
        try:
            event_date_formatted = datetime.strptime(event_date, '%Y-%m-%d').strftime('%d.%m.%Y')
            reminder_text = f"\n🔔 <b>Напоминание:</b> {datetime.strptime(reminder_date, '%Y-%m-%d').strftime('%d.%m.%Y')}" if reminder_date else ""
        except Exception as e:
            logger.error(f"Ошибка форматирования даты: {e}")
            event_date_formatted = event_date
            reminder_text = f"\n🔔 <b>Напоминание:</b> {reminder_date}" if reminder_date else ""
        
        if hasattr(message_or_callback, 'edit_text'):
            # Это CallbackQuery
            await message_or_callback.edit_text(
                f"""✅ <b>ЗАПИСЬ ДОБАВЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Тип:</b> {entry_type.upper()}
📅 <b>Дата:</b> {event_date_formatted}{reminder_text}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к журналу обслуживания...</i>""",
                parse_mode='HTML'
            )
        else:
            # Это Message
            await message_or_callback.answer(
                f"""✅ <b>ЗАПИСЬ ДОБАВЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Тип:</b> {entry_type.upper()}
📅 <b>Дата:</b> {event_date_formatted}{reminder_text}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к журналу обслуживания...</i>""",
                parse_mode='HTML'
            )
        
        # Возвращаемся к журналу обслуживания
        import asyncio
        await asyncio.sleep(1)
        
        # Создаем фейковый callback для возврата
        class FakeCallback:
            def __init__(self, car_id: int, msg):
                self.data = f"car_maintenance:{car_id}"
                if hasattr(msg, 'message'):
                    self.message = msg.message
                    self.from_user = msg.from_user
                else:
                    self.message = msg
                    self.from_user = msg.from_user
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(car_id, message_or_callback)
        await handle_car_maintenance_callback(fake_callback)
    else:
        # Fix: Улучшено логирование ошибок при сохранении записей обслуживания
        logger.error(f"Ошибка при добавлении записи обслуживания: car_id={car_id}, type={entry_type}, event_date={event_date}")
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer(
                "❌ <b>ОШИБКА ПРИ ДОБАВЛЕНИИ ЗАПИСИ</b>\n\n💡 Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
    
    await state.clear()


@admin_required
@error_handler
async def handle_maintenance_remove_reminder_callback(callback: CallbackQuery) -> None:
    """Удаляет напоминание из записи обслуживания (Модуль 5)"""
    try:
        data_parts = callback.data.split(':')
        entry_id = int(data_parts[1])
        car_id = int(data_parts[2])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверные параметры", show_alert=True)
        return
    
    # Удаляем напоминание
    success = await remove_maintenance_reminder(entry_id)
    
    if success:
        await safe_callback_answer(callback, "✅ Напоминание удалено", show_alert=False)
        
        # Возвращаемся к журналу обслуживания
        class FakeCallback:
            def __init__(self, car_id: int, msg):
                self.data = f"car_maintenance:{car_id}"
                self.message = msg
                self.from_user = msg.from_user
                
            async def answer(self, **kwargs):
                pass
        
        fake_callback = FakeCallback(car_id, callback.message)
        await handle_car_maintenance_callback(fake_callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при удалении напоминания", show_alert=True)


__all__ = [
    'handle_car_maintenance_callback',
    'handle_maintenance_add_callback',
    'handle_maintenance_type_callback',
    'handle_maintenance_description_input',
    'handle_maintenance_mileage_input',
    'handle_maintenance_event_date_input',
    'handle_maintenance_reminder_decision_callback',
    'handle_maintenance_reminder_date_input',
    'handle_maintenance_remove_reminder_callback',
]

