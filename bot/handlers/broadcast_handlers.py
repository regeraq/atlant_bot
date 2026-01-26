"""
📢 Обработчики системы рассылки сообщений
Поддерживает: текст, фото, видео, документы, кнопки
"""
from aiogram import types, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

from bot.database.database import is_admin, get_all_users, get_broadcast_history
from bot.keyboards.admin_keyboards import (
    get_broadcast_main_keyboard, get_broadcast_content_keyboard,
    get_broadcast_confirm_keyboard,
    get_admin_panel_keyboard, get_cancel_keyboard
)
from bot.utils.notifications import BroadcastManager, format_broadcast_stats
from bot.utils.helpers import safe_callback_answer

# FSM состояния для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_text = State()          # Ожидание текста
    waiting_for_media = State()         # Ожидание медиа-файла
    waiting_for_button_text = State()   # Ожидание текста кнопки
    waiting_for_button_url = State()    # Ожидание URL кнопки
    content_ready = State()             # Контент готов к отправке

# Декоратор для проверки прав администратора
def admin_required(func):
    async def wrapper(callback_or_message, *args, **kwargs):
        user_id = callback_or_message.from_user.id if callback_or_message.from_user else None
        if not user_id or not await is_admin(user_id):
            if isinstance(callback_or_message, CallbackQuery):
                await callback_or_message.answer("❌ У вас нет прав администратора", show_alert=True)
            else:
                await callback_or_message.answer("❌ У вас нет прав администратора")
            return
        return await func(callback_or_message, *args, **kwargs)
    return wrapper

@admin_required
async def handle_admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Главное меню рассылки"""
    await state.clear()
    
    users_count = len(await get_all_users())
    
    text = f"""📢 <b>Система рассылки сообщений</b>

👥 Всего пользователей в боте: <b>{users_count:,}</b>

Вы можете создать рассылку с различными типами контента:
• Текстовое сообщение
• Фотография с подписью
• Видео с подписью  
• Документ с подписью

Также можно добавить кнопки к любому типу сообщения.

<i>Выберите тип рассылки:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_main_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_text_callback(callback: CallbackQuery, state: FSMContext):
    """Создание текстовой рассылки"""
    await state.set_state(BroadcastStates.waiting_for_text)
    await state.update_data(content_type='text')
    
    text = """✍️ <b>Создание текстовой рассылки</b>

📝 Отправьте текст сообщения для рассылки.

Вы можете использовать HTML-форматирование:
• <b>жирный текст</b>
• <i>курсив</i>
• <u>подчеркнутый</u>
• <code>моноширинный</code>
• <a href="https://example.com">ссылка</a>

<i>Напишите ваше сообщение:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_photo_callback(callback: CallbackQuery, state: FSMContext):
    """Создание рассылки с фото"""
    await state.set_state(BroadcastStates.waiting_for_media)
    await state.update_data(content_type='photo')
    
    text = """🖼️ <b>Создание рассылки с фотографией</b>

📷 Отправьте фотографию для рассылки.
Вы можете добавить подпись к фотографии.

<i>Отправьте фотографию:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_video_callback(callback: CallbackQuery, state: FSMContext):
    """Создание рассылки с видео"""
    await state.set_state(BroadcastStates.waiting_for_media)
    await state.update_data(content_type='video')
    
    text = """🎥 <b>Создание рассылки с видео</b>

📹 Отправьте видеофайл для рассылки.
Вы можете добавить подпись к видео.

<i>Отправьте видеофайл:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_document_callback(callback: CallbackQuery, state: FSMContext):
    """Создание рассылки с документом"""
    await state.set_state(BroadcastStates.waiting_for_media)
    await state.update_data(content_type='document')
    
    text = """📎 <b>Создание рассылки с документом</b>

📄 Отправьте документ для рассылки.
Вы можете добавить подпись к документу.

<i>Отправьте документ:</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_text_input(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода текста для рассылки"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение")
        return
    
    await state.update_data(text=message.text)
    await state.set_state(BroadcastStates.content_ready)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    text = f"""✅ <b>Текстовая рассылка готова!</b>

📝 <b>Ваше сообщение:</b>
{message.text}

<i>Выберите действие:</i>"""
    
    await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=get_broadcast_content_keyboard(),
        parse_mode='HTML'
    )

@admin_required 
async def handle_broadcast_media_input(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода медиа для рассылки"""
    data = await state.get_data()
    content_type = data.get('content_type')
    
    file_id = None
    caption = message.caption
    
    if content_type == 'photo' and message.photo:
        file_id = message.photo[-1].file_id
    elif content_type == 'video' and message.video:
        file_id = message.video.file_id
    elif content_type == 'document' and message.document:
        file_id = message.document.file_id
    else:
        await message.answer(f"❌ Пожалуйста, отправьте {content_type}")
        return
    
    await state.update_data(file_id=file_id, text=caption)
    await state.set_state(BroadcastStates.content_ready)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    media_name = {"photo": "фотография", "video": "видео", "document": "документ"}.get(content_type, "медиа")
    
    text = f"""✅ <b>Рассылка с {media_name} готова!</b>

📎 <b>Медиа:</b> загружено
📝 <b>Подпись:</b> {caption or 'отсутствует'}

<i>Выберите действие:</i>"""
    
    await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=get_broadcast_content_keyboard(),
        parse_mode='HTML'
    )

@admin_required
async def handle_broadcast_preview_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Предварительный просмотр рассылки"""
    data = await state.get_data()
    
    # Создаем менеджер рассылки и отправляем превью
    broadcast_manager = BroadcastManager(bot)
    
    stats = await broadcast_manager.send_broadcast(
        content_type=data.get('content_type'),
        text=data.get('text'),
        file_id=data.get('file_id'),
        reply_markup=data.get('reply_markup'),
        admin_id=callback.from_user.id,
        preview_only=True
    )
    
    # Отправляем результат превью
    result_text = format_broadcast_stats(stats)
    
    await callback.message.edit_text(
        result_text,
        reply_markup=get_broadcast_content_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback, "👀 Предварительный просмотр отправлен!")

@admin_required
async def handle_broadcast_send_all_callback(callback: CallbackQuery, state: FSMContext):
    """Подтверждение отправки рассылки всем"""
    users_count = len(await get_all_users())
    
    text = f"""🚀 <b>Подтверждение массовой рассылки</b>

⚠️ Вы действительно хотите отправить рассылку всем пользователям?

👥 Всего получателей: <b>{users_count:,}</b>

<i>Это действие нельзя отменить!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_confirm_send_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Окончательная отправка рассылки"""
    data = await state.get_data()
    
    # Показываем, что начинается рассылка
    await callback.message.edit_text(
        "📡 <b>Рассылка началась...</b>\n\n⏳ Пожалуйста, подождите. Это может занять несколько минут.",
        parse_mode='HTML'
    )
    await safe_callback_answer(callback, "🚀 Рассылка запущена!")
    
    # Создаем менеджер рассылки и отправляем
    broadcast_manager = BroadcastManager(bot)
    
    stats = await broadcast_manager.send_broadcast(
        content_type=data.get('content_type'),
        text=data.get('text'),
        file_id=data.get('file_id'),
        reply_markup=data.get('reply_markup'),
        admin_id=callback.from_user.id,
        preview_only=False
    )
    
    # Показываем результаты
    result_text = format_broadcast_stats(stats)
    
    await callback.message.edit_text(
        result_text,
        reply_markup=get_broadcast_main_keyboard(),
        parse_mode='HTML'
    )
    
    # Очищаем состояние
    await state.clear()

@admin_required
async def handle_broadcast_history_callback(callback: CallbackQuery):
    """Показ истории рассылок"""
    history = await get_broadcast_history(5)
    
    if not history:
        text = """📊 <b>История рассылок</b>

📭 Рассылки еще не производились.

<i>Создайте первую рассылку!</i>"""
    else:
        text = "📊 <b>История рассылок</b>\n\n"
        
        for i, log in enumerate(history, 1):
            success_rate = (log['sent_count'] / log['total_users'] * 100) if log['total_users'] > 0 else 0
            date = log['created_at'][:16].replace('T', ' ')  # Форматируем дату
            
            text += f"""<b>{i}.</b> {log['content_type'].upper()} | {date}
👥 {log['total_users']} | ✅ {log['sent_count']} ({success_rate:.1f}%)
❌ {log['failed_count']} | 🚫 {log['blocked_count']}

"""
    
    text += "\n<i>Показаны последние 5 рассылок</i>"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к рассылке", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🏠 Админ панель", callback_data="back_to_admin_panel")]
    ])
    reply_markup = back_keyboard
    
    await callback.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

@admin_required
async def handle_broadcast_reset_callback(callback: CallbackQuery, state: FSMContext):
    """Сброс данных рассылки"""
    await state.clear()
    await handle_admin_broadcast_callback(callback, state)

@admin_required
async def handle_broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена создания рассылки"""
    await state.clear()
    await handle_admin_broadcast_callback(callback, state)