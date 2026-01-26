"""
Обработчики для реферальной системы (Модуль 6)
"""
import logging
from typing import Optional
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.database.database import get_setting, set_setting, get_referral_stats, get_referral_statistics
from bot.keyboards.admin_keyboards import get_cancel_keyboard
from bot.utils.helpers import safe_callback_answer
from bot.utils.errors import error_handler
from .common import admin_required
from .states import ReferralManagementStates

logger = logging.getLogger(__name__)


async def _get_referral_system_text_and_keyboard():
    """Вспомогательная функция для формирования текста и клавиатуры реферальной системы"""
    referral_enabled = await get_setting('referral_system_enabled')
    bonus_percentage = await get_setting('referral_bonus_percentage') or '10'
    bonus_duration = await get_setting('referral_bonus_duration_days') or '30'
    
    stats = await get_referral_statistics()
    
    status_text = "✅ Включена" if referral_enabled == 'true' else "❌ Выключена"
    
    text = f"""🏆 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Статус:</b> {status_text}
💰 <b>Процент скидки:</b> {bonus_percentage}%
📅 <b>Срок действия бонуса:</b> {bonus_duration} дней

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>СТАТИСТИКА</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего приглашенных пользователей: <b>{stats.get('referred_count', 0)}</b>
🎁 Использовано бонусов: <b>{stats.get('used_bonus_count', 0)}</b>
💰 Общая сумма выданных скидок: <b>≈{stats.get('total_discount_amount', 0):,} ₽</b>

━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Выберите действие:</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Включить систему" if referral_enabled != 'true' else "❌ Выключить систему",
            callback_data="referral_toggle"
        )],
        [InlineKeyboardButton(text="✏️ Изменить % скидки", callback_data="referral_edit_percentage")],
        [InlineKeyboardButton(text="✏️ Изменить срок действия (дни)", callback_data="referral_edit_duration")],
        [InlineKeyboardButton(text="🔙 Назад к статистике", callback_data="admin_stats")]
    ])
    
    return text, keyboard


@admin_required
@error_handler
async def handle_referral_system_callback(callback: CallbackQuery) -> None:
    """Показывает управление реферальной системой (Модуль 6)"""
    text, keyboard = await _get_referral_system_text_and_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_referral_toggle_callback(callback: CallbackQuery) -> None:
    """Переключает реферальную систему (Модуль 6)"""
    current_status = await get_setting('referral_system_enabled')
    new_status = 'false' if current_status == 'true' else 'true'
    
    await set_setting('referral_system_enabled', new_status)
    
    await safe_callback_answer(callback, f"✅ Реферальная система {'включена' if new_status == 'true' else 'выключена'}!", show_alert=False)
    
    # Возвращаемся к управлению реферальной системой
    await handle_referral_system_callback(callback)


@admin_required
@error_handler
async def handle_referral_edit_percentage_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает редактирование процента скидки (Модуль 6)"""
    await state.set_state(ReferralManagementStates.waiting_for_percentage)
    
    current_percentage = await get_setting('referral_bonus_percentage') or '10'
    
    await callback.message.edit_text(
        f"""✏️ <b>ИЗМЕНЕНИЕ ПРОЦЕНТА СКИДКИ</b>

━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Текущий процент:</b> {current_percentage}%
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новый процент скидки (от 1 до 100):</i>

📝 <i>Например:</i> 15""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_referral_percentage_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод процента скидки (Модуль 6)"""
    try:
        percentage = int(message.text.strip())
        if percentage < 1 or percentage > 100:
            raise ValueError("Вне диапазона")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n💡 Введите число от 1 до 100:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await set_setting('referral_bonus_percentage', str(percentage))
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await state.clear()
    
    # Возвращаемся к управлению реферальной системой
    text, keyboard = await _get_referral_system_text_and_keyboard()
    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')


@admin_required
@error_handler
async def handle_referral_edit_duration_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает редактирование срока действия бонуса (Модуль 6)"""
    await state.set_state(ReferralManagementStates.waiting_for_duration)
    
    current_duration = await get_setting('referral_bonus_duration_days') or '30'
    
    await callback.message.edit_text(
        f"""✏️ <b>ИЗМЕНЕНИЕ СРОКА ДЕЙСТВИЯ БОНУСА</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Текущий срок:</b> {current_duration} дней
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Введите новый срок действия бонуса в днях:</i>

📝 <i>Например:</i> 30""",
        reply_markup=get_cancel_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
@error_handler
async def handle_referral_duration_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод срока действия (Модуль 6)"""
    try:
        duration = int(message.text.strip())
        if duration < 1 or duration > 365:
            raise ValueError("Вне диапазона")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n💡 Введите число от 1 до 365:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await set_setting('referral_bonus_duration_days', str(duration))
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await state.clear()
    
    # Возвращаемся к управлению реферальной системой
    text, keyboard = await _get_referral_system_text_and_keyboard()
    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')


__all__ = [
    'handle_referral_system_callback',
    'handle_referral_toggle_callback',
    'handle_referral_edit_percentage_callback',
    'handle_referral_percentage_input',
    'handle_referral_edit_duration_callback',
    'handle_referral_duration_input',
]

