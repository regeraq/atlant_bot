"""
Обработчики для учета инцидентов (Модуль 3)
"""
import logging
from typing import Optional
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from bot.database.database import get_rental_incidents, add_rental_incident, delete_rental_incident, get_rental_by_id
from bot.keyboards.admin_keyboards import get_cancel_keyboard
from bot.utils.helpers import safe_callback_answer
from bot.utils.errors import error_handler
from .common import admin_required
from .states import IncidentManagementStates

logger = logging.getLogger(__name__)


@admin_required
@error_handler
async def handle_rental_incidents_callback(callback: CallbackQuery) -> None:
    """Показывает список инцидентов по аренде (Модуль 3)"""
    try:
        rental_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный ID аренды", show_alert=True)
        return
    
    # Получаем информацию об аренде
    rental = await get_rental_by_id(rental_id)
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    # Получаем инциденты
    incidents = await get_rental_incidents(rental_id)
    
    car_name = rental.get('car_name', 'Неизвестный автомобиль')
    
    text = f"""🚨 <b>ИНЦИДЕНТЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
━━━━━━━━━━━━━━━━━━━━━━

"""
    
    if incidents:
        text += f"<b>Всего инцидентов: {len(incidents)}</b>\n\n"
        
        total_amount = 0.0
        for i, incident in enumerate(incidents, 1):
            incident_type = incident.get('incident_type', 'Неизвестно')
            description = incident.get('description', '')
            amount = float(incident.get('amount', 0) or 0)
            total_amount += amount
            
            created_at_str = incident.get('created_at', '')
            try:
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                else:
                    created_at = created_at_str
                created_formatted = created_at.strftime('%d.%m.%Y %H:%M')
            except:
                created_formatted = 'Неизвестно'
            
            # Обрезаем длинный текст
            desc_short = description[:50] if len(description) > 50 else description
            if len(description) > 50:
                desc_short += "..."
            
            amount_text = f"{amount:,.2f} ₽" if amount > 0 else "—"
            
            text += f"<b>{i}.</b> [{incident_type.upper()}] <i>{created_formatted}</i>\n"
            text += f"{desc_short}\n"
            text += f"💰 <b>Сумма:</b> {amount_text}\n\n"
        
        if total_amount > 0:
            text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
            text += f"<b>Общая сумма: {total_amount:,.2f} ₽</b>\n\n"
    else:
        text += "<i>Инцидентов пока нет</i>\n"
    
    text += "\n💡 <i>Выберите действие:</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить инцидент", callback_data=f"incident_add:{rental_id}")],
    ])
    
    if incidents:
        # Добавляем кнопки удаления для каждого инцидента (максимум 5 для удобства)
        incidents_to_show = incidents[:5]
        for incident in incidents_to_show:
            incident_id = incident['id']
            incident_type = incident.get('incident_type', 'Инцидент')
            amount = float(incident.get('amount', 0) or 0)
            
            # Форматируем дату
            created_at_str = incident.get('created_at', '')
            try:
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                else:
                    created_at = created_at_str
                date_short = created_at.strftime('%d.%m')
            except:
                date_short = ''
            
            amount_text = f" {amount:,.0f}₽" if amount > 0 else ""
            button_text = f"🗑️ {date_short} {incident_type}{amount_text}" if date_short else f"🗑️ {incident_type}{amount_text}"
            
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"incident_delete:{incident_id}:{rental_id}"
                )
            ])
        
        if len(incidents) > 5:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"📄 ... и еще {len(incidents) - 5} инцидентов",
                    callback_data="incidents_info"
                )
            ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к аренде", callback_data=f"admin_rental_details:{rental_id}")
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_incident_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс добавления инцидента (Модуль 3)"""
    try:
        rental_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный ID аренды", show_alert=True)
        return
    
    rental = await get_rental_by_id(rental_id)
    if not rental:
        await safe_callback_answer(callback, "❌ Аренда не найдена", show_alert=True)
        return
    
    await state.set_state(IncidentManagementStates.waiting_for_incident_type)
    await state.update_data(rental_id=rental_id)
    
    car_name = rental.get('car_name', 'Неизвестный автомобиль')
    
    await callback.message.edit_text(
        f"""➕ <b>ДОБАВЛЕНИЕ ИНЦИДЕНТА</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите тип инцидента:</i>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚨 Штраф", callback_data="incident_type:штраф")],
            [InlineKeyboardButton(text="🔧 Повреждение", callback_data="incident_type:повреждение")],
            [InlineKeyboardButton(text="📋 Другое", callback_data="incident_type:другое")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_incident_type_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор типа инцидента (Модуль 3)"""
    try:
        incident_type = callback.data.split(':')[1]
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный тип инцидента", show_alert=True)
        return
    
    await state.update_data(incident_type=incident_type)
    await state.set_state(IncidentManagementStates.waiting_for_incident_description)
    
    await callback.message.edit_text(
        f"""✅ <b>Тип выбран!</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Тип:</b> {incident_type.upper()}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ ИНЦИДЕНТА</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 2 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите описание инцидента:</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_incident_description_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод описания инцидента (Модуль 3)"""
    description = message.text.strip()
    
    if not description:
        await message.answer(
            "❌ <b>Описание не может быть пустым</b>\n\n💡 Введите описание инцидента:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    if len(description) > 1000:
        await message.answer(
            "❌ <b>Описание слишком длинное</b>\n\n💡 Максимум 1000 символов. Введите более короткое описание:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await state.update_data(description=description)
    await state.set_state(IncidentManagementStates.waiting_for_incident_amount)
    
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

➕ <b>ДОБАВЛЕНИЕ ИНЦИДЕНТА</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 3 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите сумму ущерба/штрафа в рублях:</i>

💡 <i>Если суммы нет, введите 0</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )


@admin_required
@error_handler
async def handle_incident_amount_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод суммы инцидента (Модуль 3)"""
    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount < 0:
            raise ValueError("Отрицательное число")
        if amount > 99999999.99:
            raise ValueError("Сумма слишком большая")
    except ValueError as e:
        error_message = "❌ <b>Неверный формат суммы</b>\n\n💡 Введите число (например: 5000 или 5000.50):"
        if "слишком большая" in str(e):
            error_message = "❌ <b>Сумма слишком большая</b>\n\n💡 Максимальная сумма: 99 999 999.99 ₽"
        await message.answer(
            error_message,
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await state.update_data(amount=amount)
    await state.set_state(IncidentManagementStates.waiting_for_incident_photo_decision)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    amount_text = f"{amount:,.2f} ₽" if amount > 0 else "0 ₽"
    
    await message.answer(
        f"""✅ <b>Сумма сохранена!</b>

━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Сумма:</b> {amount_text}
━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ДОБАВЛЕНИЕ ИНЦИДЕНТА</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>ШАГ 4 из 4</b>
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Хотите прикрепить фотографию?</i>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📷 Да, прикрепить фото", callback_data="incident_photo_yes")],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="incident_photo_no")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]),
        parse_mode='HTML'
    )


@admin_required
@error_handler
async def handle_incident_photo_decision_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает решение о прикреплении фото (Модуль 3)"""
    # Callback_data имеет формат "incident_photo_yes" или "incident_photo_no"
    decision = 'yes' if callback.data.endswith('_yes') else 'no'
    
    data = await state.get_data()
    rental_id = data.get('rental_id')
    
    if decision == 'yes':
        await state.set_state(IncidentManagementStates.waiting_for_incident_photo)
        await callback.message.edit_text(
            """📷 <b>ОЖИДАНИЕ ФОТОГРАФИИ</b>

━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Отправьте фотографию инцидента:</i>

💡 <i>Или нажмите "Пропустить"</i>""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="incident_photo_no")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
            ]),
            parse_mode='HTML'
        )
    else:
        # Сохраняем инцидент без фото
        await save_incident(callback.message, state, None)
    
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_incident_photo_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает загрузку фото инцидента (Модуль 3)"""
    photo_file_id = None
    
    if message.photo:
        # Берем фото наибольшего размера
        photo_file_id = message.photo[-1].file_id
    elif message.document:
        # Если отправлен документ (например, фото как файл)
        photo_file_id = message.document.file_id
    
    if not photo_file_id:
        await message.answer(
            "❌ <b>Фотография не обнаружена</b>\n\n💡 Отправьте фотографию или нажмите 'Пропустить':",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="incident_photo_no")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
            ]),
            parse_mode='HTML'
        )
        return
    
    await save_incident(message, state, photo_file_id)


async def save_incident(message_or_callback, state: FSMContext, photo_file_id: Optional[str]) -> None:
    """Сохраняет инцидент в БД (Модуль 3)"""
    data = await state.get_data()
    rental_id = data.get('rental_id')
    incident_type = data.get('incident_type')
    description = data.get('description')
    amount = data.get('amount', 0.0)
    
    # Валидация данных
    if not rental_id or not incident_type or not description:
        logger.error(f"Неполные данные для сохранения инцидента: rental_id={rental_id}, type={incident_type}")
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer(
                "❌ <b>ОШИБКА: Неполные данные</b>\n\n💡 Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
        await state.clear()
        return
    
    # Добавляем инцидент
    incident_id = await add_rental_incident(rental_id, incident_type, description, amount, photo_file_id)
    
    if incident_id:
        logger.info(f"Инцидент добавлен: rental_id={rental_id}, incident_id={incident_id}, type={incident_type}, amount={amount}")
        # Удаляем сообщение пользователя, если это Message
        if hasattr(message_or_callback, 'delete'):
            try:
                await message_or_callback.delete()
            except:
                pass
        
        # Определяем, как отправлять ответ
        if hasattr(message_or_callback, 'answer') and hasattr(message_or_callback, 'edit_text'):
            # Это CallbackQuery
            await message_or_callback.edit_text(
                f"""✅ <b>ИНЦИДЕНТ ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Тип:</b> {incident_type.upper()}
💰 <b>Сумма:</b> {amount:,.2f} ₽
{'📷 Фото: Прикреплено' if photo_file_id else ''}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к списку инцидентов...</i>""",
                parse_mode='HTML'
            )
        else:
            # Это Message
            await message_or_callback.answer(
                f"""✅ <b>ИНЦИДЕНТ ДОБАВЛЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Тип:</b> {incident_type.upper()}
💰 <b>Сумма:</b> {amount:,.2f} ₽
{'📷 Фото: Прикреплено' if photo_file_id else ''}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к списку инцидентов...</i>""",
                parse_mode='HTML'
            )
        
        # Возвращаемся к списку инцидентов
        import asyncio
        await asyncio.sleep(1)
        
        # Создаем фейковый callback для возврата к списку инцидентов
        class FakeCallback:
            def __init__(self, rental_id: int, msg):
                self.data = f"rental_incidents:{rental_id}"
                if hasattr(msg, 'message'):
                    self.message = msg.message
                    self.from_user = msg.from_user
                else:
                    self.message = msg
                    self.from_user = msg.from_user
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(rental_id, message_or_callback)
        await handle_rental_incidents_callback(fake_callback)
    else:
        logger.error(f"Ошибка при добавлении инцидента: rental_id={rental_id}, type={incident_type}, amount={amount}")
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer(
                "❌ <b>ОШИБКА ПРИ ДОБАВЛЕНИИ ИНЦИДЕНТА</b>\n\n💡 Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
                parse_mode='HTML'
            )
    
    await state.clear()


@admin_required
@error_handler
async def handle_incident_delete_callback(callback: CallbackQuery) -> None:
    """Удаляет инцидент (Модуль 3)"""
    try:
        incident_id, rental_id = map(int, callback.data.split(':')[1:3])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверные параметры", show_alert=True)
        return
    
    success = await delete_rental_incident(incident_id)
    
    if success:
        await safe_callback_answer(callback, "✅ Инцидент удален!", show_alert=False)
        
        # Возвращаемся к списку инцидентов
        callback.data = f"rental_incidents:{rental_id}"
        await handle_rental_incidents_callback(callback)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при удалении инцидента", show_alert=True)


__all__ = [
    'handle_rental_incidents_callback',
    'handle_incident_add_callback',
    'handle_incident_type_callback',
    'handle_incident_description_input',
    'handle_incident_amount_input',
    'handle_incident_photo_decision_callback',
    'handle_incident_photo_input',
    'handle_incident_delete_callback',
]

