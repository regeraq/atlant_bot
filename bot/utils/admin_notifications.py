"""
Проактивные уведомления для администратора (Модуль 1)
Интеграция с APScheduler для отправки уведомлений админам о ключевых событиях
"""
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Set
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from bot.config import ADMIN_IDS, NOTIFICATION_TIME
from bot.database.database import get_all_active_rentals, get_rental_by_id, get_all_admins, get_maintenance_reminders_for_today

logger = logging.getLogger(__name__)


async def _send_notification_to_admins(
    bot: Bot,
    notification_text: str,
    admin_ids: List[int],
    valid_admin_ids: Optional[Set[int]] = None
) -> int:
    """
    Вспомогательная функция для отправки уведомлений админам параллельно (DRY принцип)
    
    Args:
        bot: Экземпляр бота
        notification_text: Текст уведомления
        admin_ids: Список ID администраторов
        valid_admin_ids: Множество валидных ID админов (если None, проверяется для каждого)
    
    Returns:
        Количество успешно отправленных уведомлений
    """
    if not admin_ids:
        return 0
    
    # Если не передано множество валидных админов, загружаем всех админов одним запросом
    if valid_admin_ids is None:
        all_admins = await get_all_admins()
        valid_admin_ids = {admin['telegram_id'] for admin in all_admins}
    
    # Фильтруем только валидных админов
    valid_ids = [admin_id for admin_id in admin_ids if admin_id in valid_admin_ids]
    
    if not valid_ids:
        logger.warning("Нет валидных администраторов для отправки уведомлений")
        return 0
    
    # Отправляем уведомления параллельно
    async def send_to_admin(admin_id: int) -> bool:
        """Отправляет уведомление одному админу"""
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            return True
        except TelegramForbiddenError:
            logger.warning(f"Администратор {admin_id} заблокировал бота")
            return False
        except TelegramBadRequest as e:
            logger.warning(f"Ошибка Telegram API при отправке уведомления админу {admin_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления админу {admin_id}: {e}")
            return False
    
    # Параллельная отправка через asyncio.gather
    results = await asyncio.gather(*[send_to_admin(admin_id) for admin_id in valid_ids], return_exceptions=True)
    sent_count = sum(1 for result in results if result is True)
    
    return sent_count


async def send_new_rental_notification(bot: Bot, rental_id: int, admin_ids: Optional[List[int]] = None) -> None:
    """
    Отправляет мгновенное уведомление админам о новой аренде (Модуль 1)
    
    Args:
        bot: Экземпляр бота
        rental_id: ID созданной аренды
        admin_ids: Список ID администраторов для уведомления (если None, используется ADMIN_IDS из config)
    """
    try:
        # Получаем информацию об аренде
        rental = await get_rental_by_id(rental_id)
        if not rental:
            logger.warning(f"Аренда с ID {rental_id} не найдена для уведомления")
            return
        
        # Определяем список админов для уведомления
        if admin_ids is None:
            admin_ids = ADMIN_IDS
        
        if not admin_ids:
            logger.warning("Список администраторов для уведомлений пуст")
            return
        
        user_name = rental.get('first_name', f"ID: {rental['user_id']}")
        user_username = rental.get('username', '')
        car_name = rental.get('car_name', 'Неизвестный автомобиль')
        
        # Форматируем дату начала
        start_date_str = rental.get('start_date', '')
        try:
            if start_date_str:
                if isinstance(start_date_str, str):
                    start_date_obj = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                else:
                    start_date_obj = start_date_str
                start_date_formatted = start_date_obj.strftime('%d.%m.%Y')
            else:
                start_date_formatted = 'Не указана'
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Ошибка парсинга даты начала аренды {rental_id}: {e}")
            start_date_formatted = 'Не указана'
        
        username_text = f"(@{user_username})" if user_username else ""
        
        notification_text = f"""🔔 **Новая аренда!**

Пользователь {user_name} {username_text} арендовал **{car_name}** с {start_date_formatted}."""
        
        # Отправляем уведомления параллельно через оптимизированную функцию
        sent_count = await _send_notification_to_admins(bot, notification_text, admin_ids)
        
        logger.info(f"✅ Отправлено {sent_count} уведомлений администраторам о новой аренде {rental_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о новой аренде: {e}")


async def check_ending_rentals_notification(bot: Bot, admin_ids: Optional[List[int]] = None) -> None:
    """
    Проверяет аренды, которые заканчиваются завтра, и отправляет уведомление админам (Модуль 1)
    
    Args:
        bot: Экземпляр бота
        admin_ids: Список ID администраторов для уведомления (если None, используется ADMIN_IDS из config)
    """
    try:
        # Определяем список админов для уведомления
        if admin_ids is None:
            admin_ids = ADMIN_IDS
        
        if not admin_ids:
            logger.warning("Список администраторов для уведомлений о завершающихся арендах пуст")
            return
        
        # Получаем все активные аренды
        rentals = await get_all_active_rentals()
        
        # Вычисляем завтрашнюю дату
        tomorrow = date.today() + timedelta(days=1)
        
        # Находим аренды, которые заканчиваются завтра
        ending_rentals = []
        for rental in rentals:
            end_date_str = rental.get('end_date')
            
            # Если указана дата окончания, используем её
            if end_date_str:
                try:
                    if isinstance(end_date_str, str):
                        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    else:
                        end_date_obj = end_date_str.date() if hasattr(end_date_str, 'date') else end_date_str
                    
                    # Проверяем, заканчивается ли аренда завтра
                    if end_date_obj == tomorrow:
                        ending_rentals.append(rental)
                        
                except (ValueError, TypeError, AttributeError) as e:
                    # Fix: Используем конкретные типы исключений для обработки ошибок парсинга дат
                    logger.warning(f"Ошибка при обработке даты окончания аренды {rental.get('id')}: {e}")
                    continue
            else:
                # Если дата окончания не указана, пытаемся вычислить на основе даты начала и типа напоминания
                # Это fallback для старых аренд без end_date
                start_date_str = rental.get('start_date')
                reminder_type = rental.get('reminder_type', 'daily')
                
                if not start_date_str:
                    continue
                
                try:
                    if isinstance(start_date_str, str):
                        start_date_obj = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
                    else:
                        start_date_obj = start_date_str.date() if hasattr(start_date_str, 'date') else start_date_str
                    
                    # Вычисляем примерную дату окончания на основе типа напоминания
                    # daily = 7 дней по умолчанию, weekly = 30 дней, monthly = 90 дней
                    rental_periods = {
                        'daily': 7,
                        'weekly': 30,
                        'monthly': 90
                    }
                    period_days = rental_periods.get(reminder_type, 7)
                    estimated_end_date = start_date_obj + timedelta(days=period_days)
                    
                    # Проверяем, заканчивается ли аренда завтра
                    if estimated_end_date == tomorrow:
                        ending_rentals.append(rental)
                        
                except (ValueError, TypeError, AttributeError) as e:
                    # Fix: Используем конкретные типы исключений для обработки ошибок парсинга дат
                    logger.warning(f"Ошибка при обработке даты аренды {rental.get('id')}: {e}")
                    continue
        
        # Если есть аренды, заканчивающиеся завтра, формируем сообщение
        if ending_rentals:
            notification_parts = ["🔔 **Завершение аренды (завтра)!**\n"]
            
            for rental in ending_rentals:
                car_name = rental.get('car_name', 'Неизвестный автомобиль')
                user_name = rental.get('first_name', f"ID: {rental['user_id']}")
                notification_parts.append(f"• У автомобиля **{car_name}**, арендованного пользователем {user_name}, завтра заканчивается срок аренды.")
            
            notification_text = "\n".join(notification_parts)
            
            # Загружаем всех админов одним запросом для оптимизации
            all_admins = await get_all_admins()
            valid_admin_ids = {admin['telegram_id'] for admin in all_admins}
            
            # Отправляем уведомления параллельно через оптимизированную функцию
            sent_count = await _send_notification_to_admins(bot, notification_text, admin_ids, valid_admin_ids)
            
            logger.info(f"✅ Отправлено {sent_count} уведомлений администраторам о {len(ending_rentals)} арендах, заканчивающихся завтра")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке завершающихся аренд: {e}")


async def check_maintenance_reminders_notification(bot: Bot, admin_ids: Optional[List[int]] = None) -> None:
    """
    Проверяет напоминания по обслуживанию автомобилей и отправляет уведомления админам (Модуль 5)
    
    Args:
        bot: Экземпляр бота
        admin_ids: Список ID администраторов для уведомления (если None, используется ADMIN_IDS из config)
    """
    try:
        # Определяем список админов для уведомления
        if admin_ids is None:
            admin_ids = ADMIN_IDS
        
        if not admin_ids:
            logger.warning("Список администраторов для уведомлений о напоминаниях обслуживания пуст")
            return
        
        # Получаем записи обслуживания, для которых сегодня дата напоминания
        reminders = await get_maintenance_reminders_for_today()
        
        if reminders:
            # Группируем напоминания по автомобилям
            reminders_by_car = {}
            for reminder in reminders:
                car_name = reminder.get('car_name', 'Неизвестный автомобиль')
                if car_name not in reminders_by_car:
                    reminders_by_car[car_name] = []
                reminders_by_car[car_name].append(reminder)
            
            # Загружаем всех админов одним запросом для оптимизации (один раз для всех автомобилей)
            all_admins = await get_all_admins()
            valid_admin_ids = {admin['telegram_id'] for admin in all_admins}
            
            # Формируем одно сообщение на автомобиль
            for car_name, car_reminders in reminders_by_car.items():
                notification_parts = [f"🔔 **Напоминание по авто!**\n\n**{car_name}**\n"]
                
                for reminder in car_reminders:
                    description = reminder.get('description', '')
                    entry_type = reminder.get('entry_type', 'Обслуживание')
                    notification_parts.append(f"• {description} (Тип: {entry_type})")
                
                notification_text = "\n".join(notification_parts)
                
                # Отправляем уведомления параллельно через оптимизированную функцию
                sent_count = await _send_notification_to_admins(bot, notification_text, admin_ids, valid_admin_ids)
                
                logger.info(f"✅ Отправлено {sent_count} уведомлений администраторам о {len(car_reminders)} напоминаниях обслуживания для {car_name}")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке напоминаний обслуживания: {e}")

