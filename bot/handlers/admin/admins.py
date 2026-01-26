"""
Обработчики управления администраторами
"""
import asyncio
import logging
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.database.database import get_all_admins, add_admin, delete_admin, is_admin
from bot.keyboards.admin_keyboards import (
    get_admin_management_keyboard,
    get_cancel_keyboard,
    get_admin_list_keyboard,
    get_admin_delete_confirm_keyboard
)
from bot.utils.helpers import safe_callback_answer
from .common import admin_required
from .states import AdminManagementStates

logger = logging.getLogger(__name__)


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




