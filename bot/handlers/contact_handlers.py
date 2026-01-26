"""
Обработчики управления контактами
"""
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from bot.database.database import get_contact, update_contact
from bot.keyboards.admin_keyboards import get_contacts_management_keyboard, get_cancel_keyboard
from bot.utils.helpers import safe_callback_answer

from bot.handlers.admin import admin_required

@admin_required
async def handle_admin_manage_contacts_callback(callback: CallbackQuery):
    """Управление контактами"""
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    contact = await get_contact('booking')
    
    if contact:
        name = contact.get('name', 'Не указано')
        phone = contact.get('phone', 'Не указано')
        telegram = contact.get('telegram_username', 'Не указано')
        if telegram and not telegram.startswith('@'):
            telegram = '@' + telegram
    else:
        name = 'Не указано'
        phone = 'Не указано'
        telegram = 'Не указано'
    
    text = f"""📞 <b>УПРАВЛЕНИЕ КОНТАКТАМИ</b>

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>ТЕКУЩИЕ ДАННЫЕ</b>
━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Имя:</b> {name}
📱 <b>Телефон:</b> {phone}
💬 <b>Telegram:</b> {telegram}

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите параметр для изменения:</i>"""
    
    await callback.message.answer(
        text,
        reply_markup=get_contacts_management_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_contact_edit_name_callback(callback: CallbackQuery, state: FSMContext):
    """Редактирование имени контакта"""
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    from bot.handlers.admin import ContactManagementStates
    await state.set_state(ContactManagementStates.waiting_for_name)
    
    contact = await get_contact('booking')
    current_name = contact.get('name', 'Не указано') if contact else 'Не указано'
    
    await callback.message.answer(
        f"""✏️ <b>ИЗМЕНЕНИЕ ИМЕНИ КОНТАКТА</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Текущее имя:</b> {current_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новое имя контакта:</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_contact_edit_phone_callback(callback: CallbackQuery, state: FSMContext):
    """Редактирование телефона контакта"""
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    from bot.handlers.admin import ContactManagementStates
    await state.set_state(ContactManagementStates.waiting_for_phone)
    
    contact = await get_contact('booking')
    current_phone = contact.get('phone', 'Не указано') if contact else 'Не указано'
    
    await callback.message.answer(
        f"""✏️ <b>ИЗМЕНЕНИЕ ТЕЛЕФОНА КОНТАКТА</b>

━━━━━━━━━━━━━━━━━━━━━━
📱 <b>Текущий телефон:</b> {current_phone}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новый номер телефона</i>
📝 <i>Например: +7 919 634-90-91</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_admin_contact_edit_telegram_callback(callback: CallbackQuery, state: FSMContext):
    """Редактирование Telegram контакта"""
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    from bot.handlers.admin import ContactManagementStates
    await state.set_state(ContactManagementStates.waiting_for_telegram)
    
    contact = await get_contact('booking')
    current_telegram = contact.get('telegram_username', 'Не указано') if contact else 'Не указано'
    if current_telegram and not current_telegram.startswith('@'):
        current_telegram = '@' + current_telegram
    
    await callback.message.answer(
        f"""✏️ <b>ИЗМЕНЕНИЕ TELEGRAM КОНТАКТА</b>

━━━━━━━━━━━━━━━━━━━━━━
💬 <b>Текущий Telegram:</b> {current_telegram}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите Telegram username или ID</i>
📝 <i>Например: @username или 123456789</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_contact_name_input(message: Message, state: FSMContext):
    """Обработка ввода имени контакта"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer(
            "<b>Имя слишком короткое</b>\n\n"
            "Введите имя длиной от 2 символов",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    success = await update_contact('booking', name=name)
    
    if success:
        # Удаляем предыдущее сообщение для чистоты
        try:
            await message.delete()
        except (TelegramBadRequest, TelegramAPIError):
            pass
        
        await message.answer(
            f"""✅ <b>ИМЯ УСПЕШНО ИЗМЕНЕНО!</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Новое имя:</b> {name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению контактами...</i>""",
            parse_mode='HTML'
        )
        await state.clear()
        
        # Обновляем отображение
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.data = "admin_manage_contacts"
                self.from_user = user
            async def answer(self):
                pass
        fake_cb = FakeCallback(message, message.from_user)
        await handle_admin_manage_contacts_callback(fake_cb)
    else:
        await message.answer("Ошибка при обновлении имени", reply_markup=get_cancel_keyboard())

@admin_required
async def handle_contact_phone_input(message: Message, state: FSMContext):
    """Обработка ввода телефона контакта"""
    phone = message.text.strip()
    
    if len(phone) < 5:
        await message.answer(
            "<b>Номер телефона слишком короткий</b>\n\n"
            "Введите корректный номер телефона",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    success = await update_contact('booking', phone=phone)
    
    if success:
        # Удаляем предыдущее сообщение для чистоты
        try:
            await message.delete()
        except (TelegramBadRequest, TelegramAPIError):
            pass
        
        await message.answer(
            f"""✅ <b>ТЕЛЕФОН УСПЕШНО ИЗМЕНЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
📱 <b>Новый телефон:</b> {phone}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению контактами...</i>""",
            parse_mode='HTML'
        )
        await state.clear()
        
        # Обновляем отображение
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.data = "admin_manage_contacts"
                self.from_user = user
            async def answer(self):
                pass
        fake_cb = FakeCallback(message, message.from_user)
        await handle_admin_manage_contacts_callback(fake_cb)
    else:
        await message.answer("Ошибка при обновлении телефона", reply_markup=get_cancel_keyboard())

@admin_required
async def handle_contact_telegram_input(message: Message, state: FSMContext):
    """Обработка ввода Telegram контакта"""
    telegram_input = message.text.strip()
    
    telegram_username = None
    telegram_id = None
    
    # Пытаемся определить, это username или ID
    if telegram_input.isdigit():
        telegram_id = int(telegram_input)
    elif telegram_input.startswith('@'):
        telegram_username = telegram_input[1:]
    else:
        telegram_username = telegram_input
    
    success = await update_contact('booking', telegram_username=telegram_username, telegram_id=telegram_id)
    
    if success:
        # Удаляем предыдущее сообщение для чистоты
        try:
            await message.delete()
        except (TelegramBadRequest, TelegramAPIError):
            pass
        
        telegram_display = f"@{telegram_username}" if telegram_username else f"ID: {telegram_id}" if telegram_id else "Не указано"
        
        await message.answer(
            f"""✅ <b>TELEGRAM УСПЕШНО ИЗМЕНЕН!</b>

━━━━━━━━━━━━━━━━━━━━━━
💬 <b>Новый Telegram:</b> {telegram_display}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к управлению контактами...</i>""",
            parse_mode='HTML'
        )
        await state.clear()
        
        # Обновляем отображение
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.data = "admin_manage_contacts"
                self.from_user = user
            async def answer(self):
                pass
        fake_cb = FakeCallback(message, message.from_user)
        await handle_admin_manage_contacts_callback(fake_cb)
    else:
        await message.answer("Ошибка при обновлении Telegram", reply_markup=get_cancel_keyboard())

