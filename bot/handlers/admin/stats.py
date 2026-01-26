"""
Обработчики статистики для администраторов
"""
import logging
from aiogram.types import CallbackQuery
from bot.database.database import get_all_cars, get_all_users, get_all_admins, get_users_by_source, get_referral_stats
from bot.keyboards.admin_keyboards import get_admin_stats_keyboard
from bot.utils.helpers import safe_callback_answer
from .common import admin_required

logger = logging.getLogger(__name__)


@admin_required
async def handle_admin_stats_callback(callback: CallbackQuery):
    """Обработчик статистики"""
    cars = await get_all_cars()
    users = await get_all_users()
    admins = await get_all_admins()
    
    available_cars = sum(1 for car in cars if car['available'])
    unavailable_cars = len(cars) - available_cars
    
    # Подсчет ценовых категорий
    cheap_cars = sum(1 for car in cars if car['daily_price'] < 6000)
    medium_cars = sum(1 for car in cars if 6000 <= car['daily_price'] < 10000)
    premium_cars = sum(1 for car in cars if car['daily_price'] >= 10000)
    
    # Модуль 6: Статистика реферальной системы
    referral_stats = await get_referral_stats()
    
    # Модуль 7: Статистика источников пользователей
    source_stats = await get_users_by_source()
    source_stats_text = ""
    if source_stats:
        source_stats_text = "\n━━━━━━━━━━━━━━━━━━━━━━\n📈 <b>ИСТОЧНИКИ ПОЛЬЗОВАТЕЛЕЙ</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
            source_stats_text += f"• {source}: <b>{count}</b>\n"
    
    stats_text = f"""📊 <b>СТАТИСТИКА СИСТЕМЫ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>АВТОПАРК</b>
━━━━━━━━━━━━━━━━━━━━━━

🚗 Всего автомобилей: <b>{len(cars)}</b>
✅ Доступно: <b>{available_cars}</b>
❌ Недоступно: <b>{unavailable_cars}</b>

━━━━━━━━━━━━━━━━━━━━━━
💰 <b>ПО ЦЕНОВЫМ КАТЕГОРИЯМ</b>
━━━━━━━━━━━━━━━━━━━━━━

💵 Эконом (&lt;6000₽): <b>{cheap_cars}</b>
💎 Комфорт (6000-10000₽): <b>{medium_cars}</b>
👑 Премиум (&gt;10000₽): <b>{premium_cars}</b>

━━━━━━━━━━━━━━━━━━━━━━
👥 <b>ПОЛЬЗОВАТЕЛИ</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего пользователей: <b>{len(users)}</b>
🔧 Администраторов: <b>{len(admins)}</b>

{source_stats_text}━━━━━━━━━━━━━━━━━━━━━━
🏆 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего приглашенных пользователей: <b>{referral_stats.get('referred_count', 0)}</b>

━━━━━━━━━━━━━━━━━━━━━━

📅 <i>Данные обновлены: сейчас</i>"""
    
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        stats_text,
        reply_markup=get_admin_stats_keyboard(),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)


@admin_required
async def handle_admin_refresh_stats_callback(callback: CallbackQuery):
    """Обновление статистики"""
    await handle_admin_stats_callback(callback)


@admin_required
async def handle_admin_page_info_callback(callback: CallbackQuery):
    """Информация о странице"""
    await safe_callback_answer(callback, "📄 Информация о текущей странице")




