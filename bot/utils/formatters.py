"""
Утилиты для красивого форматирования сообщений
Использует современные возможности Telegram Bot API 9.4
"""
from typing import Optional, Tuple
from datetime import datetime, date


def format_profile_header(user_name: Optional[str] = None) -> str:
    """Создает красивый заголовок профиля"""
    name = user_name or "Пользователь"
    return f"""👤 <b>МОЙ ПРОФИЛЬ</b>

👋 <b>Привет, {name}!</b>"""


def format_section(title: str, content: str, emoji: str = "📋") -> str:
    """Форматирует секцию с заголовком"""
    return f"""
{emoji} <b>{title}</b>
{content}
"""


def format_info_line(label: str, value: str, emoji: str = "•") -> str:
    """Форматирует строку информации"""
    return f"{emoji} <b>{label}:</b> {value}"


def format_status_badge(status: str, is_active: bool = True) -> str:
    """Создает красивый бейдж статуса"""
    if is_active:
        return f"🟢 <b>{status}</b>"
    else:
        return f"🔴 <b>{status}</b>"


def format_price(amount: float, currency: str = "₽") -> str:
    """Форматирует цену"""
    return f"<code>{amount:,.0f} {currency}</code>"


def format_date(date_obj, format_str: str = "%d.%m.%Y") -> str:
    """Форматирует дату"""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except:
            return date_obj
    if isinstance(date_obj, (datetime, date)):
        return date_obj.strftime(format_str)
    return str(date_obj)


def format_days_count(days: int) -> str:
    """Форматирует количество дней с правильным склонением"""
    if days == 0:
        return "сегодня"
    elif days == 1:
        return "1 день"
    elif 2 <= days <= 4:
        return f"{days} дня"
    elif 5 <= days <= 20:
        return f"{days} дней"
    elif days % 10 == 1:
        return f"{days} день"
    elif days % 10 in [2, 3, 4]:
        return f"{days} дня"
    else:
        return f"{days} дней"


def format_deposit_status(status: str) -> Tuple[str, str]:
    """Возвращает эмодзи и текст статуса залога"""
    status_map = {
        'pending': ('⏳', 'Ожидается'),
        'paid': ('✅', 'Внесен'),
        'returned': ('↩️', 'Возвращен')
    }
    return status_map.get(status, ('❓', status))


def format_divider(style: str = "thin") -> str:
    """Создает разделитель"""
    if style == "thin":
        return "━━━━━━━━━━━━━━━━━━━━━━"
    elif style == "thick":
        return "═══════════════════════"
    elif style == "dotted":
        return "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    else:
        return "━━━━━━━━━━━━━━━━━━━━━━"


def format_card(title: str, content: str, emoji: str = "📦") -> str:
    """Создает карточку с информацией"""
    return f"""
┌─ {emoji} <b>{title}</b> ─┐
│ {content}
└─────────────────────────┘
"""


def format_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Создает текстовый прогресс-бар"""
    filled = int((current / total) * length) if total > 0 else 0
    empty = length - filled
    return "█" * filled + "░" * empty


def format_rental_summary(
    car_name: str,
    daily_price: float,
    days_rented: int,
    start_date: str,
    end_date: Optional[str] = None,
    deposit_amount: float = 0,
    deposit_status: str = "pending",
    referral_discount: int = 0
) -> str:
    """Форматирует сводку об аренде"""
    price_text = format_price(daily_price)
    days_text = format_days_count(days_rented)
    
    # Расчет общей стоимости
    total_cost = daily_price * days_rented
    if referral_discount > 0:
        discount_amount = total_cost * (referral_discount / 100)
        total_cost -= discount_amount
        discount_text = f"\n🎁 <b>Скидка {referral_discount}%:</b> -{format_price(discount_amount)}"
    else:
        discount_text = ""
    
    deposit_text = ""
    if deposit_amount > 0:
        deposit_emoji, deposit_status_text = format_deposit_status(deposit_status)
        deposit_text = f"\n{deposit_emoji} <b>Залог:</b> {format_price(deposit_amount)} ({deposit_status_text})"
    
    end_date_text = format_date(end_date) if end_date else "Не указана"
    
    return f"""
🚗 <b>{car_name}</b>

💰 <b>Стоимость:</b> {price_text}/день
📅 <b>Начало:</b> {format_date(start_date)}
📅 <b>Окончание:</b> {end_date_text}
📆 <b>Дней в аренде:</b> {days_text}
💵 <b>Общая стоимость:</b> {format_price(total_cost)}{discount_text}{deposit_text}
"""

