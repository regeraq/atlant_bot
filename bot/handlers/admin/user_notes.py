"""
Обработчики для работы с заметками о пользователях (Модуль 2)
"""
import logging
from typing import Optional
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from bot.database.database import get_user_notes, add_user_note, delete_user_note, get_user_by_id, is_admin
from bot.keyboards.admin_keyboards import get_cancel_keyboard
from bot.utils.helpers import safe_callback_answer
from bot.utils.errors import error_handler
from .common import admin_required
from .states import UserNotesStates

logger = logging.getLogger(__name__)


@admin_required
@error_handler
async def handle_user_notes_callback(callback: CallbackQuery, user_id: Optional[int] = None) -> None:
    """Показывает список заметок о пользователе (Модуль 2)"""
    # Получаем user_id из callback data или параметра
    if user_id is None:
        try:
            user_id = int(callback.data.split(':')[1])
        except (IndexError, ValueError):
            await safe_callback_answer(callback, "❌ Ошибка: неверный ID пользователя", show_alert=True)
            return
    
    # Получаем информацию о пользователе
    user = await get_user_by_id(user_id)
    if not user:
        await safe_callback_answer(callback, "❌ Пользователь не найден", show_alert=True)
        return
    
    # Получаем заметки
    notes = await get_user_notes(user_id)
    
    user_name = user.get('first_name', f"ID: {user_id}")
    username = user.get('username', '')
    username_text = f"(@{username})" if username else ""
    
    text = f"""📝 <b>ЗАМЕТКИ О ПОЛЬЗОВАТЕЛЕ</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> {user_name} {username_text}
━━━━━━━━━━━━━━━━━━━━━━

"""
    
    if notes:
        text += f"<b>Всего заметок: {len(notes)}</b>\n\n"
        for i, note in enumerate(notes, 1):
            created_at_str = note.get('created_at', '')
            try:
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                else:
                    created_at = created_at_str
                created_formatted = created_at.strftime('%d.%m.%Y %H:%M')
            except:
                created_formatted = 'Неизвестно'
            
            admin_id = note.get('admin_telegram_id', 'Неизвестно')
            note_text = note.get('note_text', '')
            # Обрезаем длинный текст
            if len(note_text) > 100:
                note_text = note_text[:100] + "..."
            
            text += f"<b>{i}.</b> <i>{created_formatted}</i> (Админ: {admin_id})\n{note_text}\n\n"
    else:
        text += "<i>Заметок пока нет</i>\n"
    
    text += "\n💡 <i>Выберите действие:</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить заметку", callback_data=f"user_note_add:{user_id}")],
    ])
    
    if notes:
        # Добавляем кнопки удаления для каждой заметки
        for note in notes[:5]:  # Ограничиваем 5 заметками для кнопок
            note_id = note['id']
            note_text_short = note.get('note_text', '')[:30]
            if len(note_text_short) < len(note.get('note_text', '')):
                note_text_short += "..."
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑️ Удалить: {note_text_short}",
                    callback_data=f"user_note_delete:{note_id}:{user_id}"
                )
            ])
    
    # Добавляем кнопку возврата
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin_panel")])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_user_note_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс добавления заметки (Модуль 2)"""
    try:
        user_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверный ID пользователя", show_alert=True)
        return
    
    user = await get_user_by_id(user_id)
    if not user:
        await safe_callback_answer(callback, "❌ Пользователь не найден", show_alert=True)
        return
    
    await state.set_state(UserNotesStates.waiting_for_note_text)
    await state.update_data(user_id=user_id)
    
    user_name = user.get('first_name', f"ID: {user_id}")
    
    await callback.message.edit_text(
        f"""➕ <b>ДОБАВЛЕНИЕ ЗАМЕТКИ</b>

━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Пользователь:</b> {user_name}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите текст заметки:</i>

📝 <i>Максимум 1000 символов</i>""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_user_note_text_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод текста заметки (Модуль 2)"""
    note_text = message.text.strip()
    
    if not note_text:
        await message.answer(
            "❌ <b>Заметка не может быть пустой</b>\n\n💡 Введите текст заметки:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    if len(note_text) > 1000:
        await message.answer(
            "❌ <b>Заметка слишком длинная</b>\n\n💡 Максимум 1000 символов. Введите более короткий текст:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    user_id = data.get('user_id')
    
    if not user_id:
        await message.answer("❌ Ошибка: не найден ID пользователя", reply_markup=get_cancel_keyboard())
        await state.clear()
        return
    
    # Получаем admin_id из сообщения
    admin_id = message.from_user.id if message.from_user else None
    if not admin_id:
        await message.answer("❌ Ошибка: не удалось определить администратора", reply_markup=get_cancel_keyboard())
        await state.clear()
        return
    
    # Проверяем, является ли пользователь админом
    if not await is_admin(admin_id):
        await message.answer("❌ У вас нет прав администратора", reply_markup=get_cancel_keyboard())
        await state.clear()
        return
    
    # Добавляем заметку
    note_id = await add_user_note(user_id, admin_id, note_text)
    
    if note_id:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"""✅ <b>ЗАМЕТКА ДОБАВЛЕНА!</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 Заметка успешно сохранена
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Возвращаемся к заметкам пользователя...</i>""",
            parse_mode='HTML'
        )
        
        # Возвращаемся к списку заметок
        import asyncio
        await asyncio.sleep(1)
        
        # Создаем фейковый callback для возврата к списку заметок
        class FakeCallback:
            def __init__(self, user_id: int, msg: Message):
                self.data = f"user_notes:{user_id}"
                self.message = msg
                self.from_user = msg.from_user
                
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(user_id, message)
        await handle_user_notes_callback(fake_callback, user_id)
    else:
        logger.error(f"Ошибка при добавлении заметки: user_id={user_id}, admin_id={admin_id}")
        await message.answer(
            "❌ <b>ОШИБКА ПРИ ДОБАВЛЕНИИ ЗАМЕТКИ</b>\n\n💡 Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
    
    await state.clear()


@admin_required
@error_handler
async def handle_user_note_delete_callback(callback: CallbackQuery) -> None:
    """Удаляет заметку (Модуль 2)"""
    try:
        note_id, user_id = map(int, callback.data.split(':')[1:3])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Ошибка: неверные параметры", show_alert=True)
        return
    
    success = await delete_user_note(note_id)
    
    if success:
        await safe_callback_answer(callback, "✅ Заметка удалена!", show_alert=False)
        
        # Возвращаемся к списку заметок
        await handle_user_notes_callback(callback, user_id)
    else:
        await safe_callback_answer(callback, "❌ Ошибка при удалении заметки", show_alert=True)


__all__ = [
    'handle_user_notes_callback',
    'handle_user_note_add_callback',
    'handle_user_note_text_input',
    'handle_user_note_delete_callback',
]

