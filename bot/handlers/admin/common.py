"""
Общие функции и декораторы для admin handlers
"""
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.database.database import is_admin
from bot.keyboards.user_keyboards import get_main_menu
from bot.utils.helpers import safe_callback_answer


def admin_required(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(message_or_callback, *args, **kwargs):
        user_id = message_or_callback.from_user.id if message_or_callback.from_user else None
        if not user_id or not await is_admin(user_id):
            if isinstance(message_or_callback, CallbackQuery):
                await safe_callback_answer(
                    message_or_callback,
                    "❌ У вас нет прав администратора",
                    show_alert=True
                )
            else:
                await message_or_callback.answer(
                    "❌ У вас нет прав администратора.\n\nЭта функция доступна только для администраторов.",
                    reply_markup=get_main_menu()
                )
            return
        return await func(message_or_callback, *args, **kwargs)
    return wrapper


async def handle_cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    """Универсальный обработчик отмены действий"""
    await state.clear()
    # Импортируем здесь, чтобы избежать циклического импорта
    from .panel import handle_admin_panel_callback
    await handle_admin_panel_callback(callback)

