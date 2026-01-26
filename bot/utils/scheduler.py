"""
Система напоминаний об оплате аренды
Интегрирован с APScheduler для проактивных уведомлений администратору (Модуль 1)
"""
import asyncio
import logging
from datetime import datetime, time as dt_time, timedelta, date
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.database.database import get_all_active_rentals, get_rentals_by_reminder_time, update_rental_last_reminder
from bot.utils.admin_notifications import check_ending_rentals_notification, check_maintenance_reminders_notification
from bot.config import NOTIFICATION_TIME

logger = logging.getLogger(__name__)

class PaymentReminderScheduler:
    """Планировщик напоминаний об оплате"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        self._task = None
    
    async def start(self):
        """Запуск планировщика"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ Планировщик напоминаний запущен")
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Планировщик напоминаний остановлен")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                current_date = now.date()
                
                # Fix based on audit: Фильтрация на уровне БД вместо загрузки всех аренд
                # Получаем только аренды с текущим временем напоминания
                rentals = await get_rentals_by_reminder_time(current_time)
                
                for rental in rentals:
                    reminder_type = rental.get('reminder_type', 'daily')
                    
                    # Проверяем, нужно ли отправить напоминание в зависимости от типа
                    should_send = await self._should_send_reminder(rental, current_date)
                    
                    if should_send:
                        await self._send_reminder(rental, current_date)
                
                # Проверяем каждую минуту
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(60)
    
    async def _should_send_reminder(self, rental: Dict[str, Any], current_date: date) -> bool:
        """Проверяет, нужно ли отправить напоминание в зависимости от типа"""
        reminder_type = rental.get('reminder_type', 'daily')
        start_date_str = rental.get('start_date')
        last_reminder_date_str = rental.get('last_reminder_date')
        
        if not start_date_str:
            return False
        
        # Парсим дату начала аренды
        try:
            if isinstance(start_date_str, str):
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
            else:
                start_date = start_date_str.date() if hasattr(start_date_str, 'date') else start_date_str
        except:
            logger.error(f"Ошибка парсинга даты начала аренды: {start_date_str}")
            return False
        
        # Парсим дату последнего напоминания
        last_reminder_date = None
        if last_reminder_date_str:
            try:
                if isinstance(last_reminder_date_str, str):
                    last_reminder_date = datetime.strptime(last_reminder_date_str, '%Y-%m-%d').date()
                else:
                    last_reminder_date = last_reminder_date_str.date() if hasattr(last_reminder_date_str, 'date') else last_reminder_date_str
            except:
                pass
        
        if reminder_type == 'daily':
            # Ежедневно - отправляем каждый день, если еще не отправляли сегодня
            return last_reminder_date != current_date
        
        elif reminder_type == 'weekly':
            # Еженедельно - каждые 7 дней от начала аренды
            days_since_start = (current_date - start_date).days
            
            # Проверяем, прошло ли 7 дней или кратно 7
            if days_since_start < 7:
                return False
            
            # Проверяем, не отправляли ли уже напоминание в этот период
            if last_reminder_date:
                days_since_last = (current_date - last_reminder_date).days
                if days_since_last < 7:
                    return False
            
            # Проверяем, что сегодня кратно 7 дням от начала
            return days_since_start % 7 == 0
        
        elif reminder_type == 'monthly':
            # Ежемесячно - каждые 30 дней от начала аренды
            days_since_start = (current_date - start_date).days
            
            # Проверяем, прошло ли 30 дней
            if days_since_start < 30:
                return False
            
            # Проверяем, не отправляли ли уже напоминание в этот период
            if last_reminder_date:
                days_since_last = (current_date - last_reminder_date).days
                if days_since_last < 30:
                    return False
            
            # Проверяем, что сегодня кратно 30 дням от начала
            return days_since_start % 30 == 0
        
        return False
    
    async def _send_reminder(self, rental: Dict[str, Any], reminder_date: date):
        """Отправка напоминания пользователю"""
        try:
            user_id = rental['user_id']
            car_name = rental.get('car_name', 'Автомобиль')
            daily_price = rental.get('daily_price', 0)
            reminder_type = rental.get('reminder_type', 'daily')
            start_date_str = rental.get('start_date')
            
            # Вычисляем общую сумму в зависимости от типа напоминания
            if reminder_type == 'daily':
                amount = daily_price
                period_text = "Ежедневная оплата"
            elif reminder_type == 'weekly':
                amount = daily_price * 7
                period_text = "Оплата за неделю (7 дней)"
            elif reminder_type == 'monthly':
                amount = daily_price * 30
                period_text = "Оплата за месяц (30 дней)"
            else:
                amount = daily_price
                period_text = "Ежедневная оплата"
            
            price_formatted = f"{amount:,} ₽"
            
            # Вычисляем количество дней аренды
            days_rented = 0
            if start_date_str:
                try:
                    if isinstance(start_date_str, str):
                        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
                    else:
                        start_date = start_date_str.date() if hasattr(start_date_str, 'date') else start_date_str
                    days_rented = (reminder_date - start_date).days
                except:
                    pass
            
            text = f"""💳 <b>НАПОМИНАНИЕ ОБ ОПЛАТЕ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚗 <b>Автомобиль:</b> {car_name}
💰 <b>Сумма к оплате:</b> <code>{price_formatted}</code>
📅 <b>Период:</b> {period_text}
📆 <b>Дней в аренде:</b> {days_rented}
━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Пожалуйста, произведите оплату за аренду автомобиля</i>

📞 <i>Для оплаты свяжитесь с менеджером</i>"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode='HTML'
            )
            
            # Обновляем дату последнего напоминания
            await update_rental_last_reminder(rental['id'], reminder_date.strftime('%Y-%m-%d'))
            
            logger.info(f"✅ Напоминание отправлено пользователю {user_id} (тип: {reminder_type})")
            
        except TelegramForbiddenError:
            # Пользователь заблокировал бота - это нормальная ситуация
            logger.warning(f"Пользователь {user_id} заблокировал бота, напоминание не отправлено")
        except TelegramBadRequest as e:
            logger.warning(f"Ошибка Telegram API при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке напоминания пользователю {user_id}: {e}")

# Глобальные экземпляры планировщиков
scheduler: PaymentReminderScheduler = None
apscheduler: Optional[AsyncIOScheduler] = None
notification_bot: Optional[Bot] = None

async def init_scheduler(bot: Bot):
    """Инициализация планировщиков (старый цикл + APScheduler для уведомлений админам)"""
    global scheduler, apscheduler, notification_bot
    
    # Инициализируем старый планировщик напоминаний об оплате
    scheduler = PaymentReminderScheduler(bot)
    await scheduler.start()
    
    # Инициализируем APScheduler для проактивных уведомлений администратору (Модуль 1)
    notification_bot = bot
    apscheduler = AsyncIOScheduler()
    
    # Парсим время уведомления (формат: HH:MM)
    try:
        hour, minute = map(int, NOTIFICATION_TIME.split(':'))
    except:
        hour, minute = 10, 0  # По умолчанию 10:00
        logger.warning(f"Некорректный формат NOTIFICATION_TIME, используется значение по умолчанию: 10:00")
    
    # Настраиваем ежедневную проверку завершающихся аренд (Модуль 1)
    apscheduler.add_job(
        check_ending_rentals_notification,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[bot],
        id='daily_ending_rentals_notification',
        replace_existing=True
    )
    
    # Настраиваем ежедневную проверку напоминаний обслуживания (Модуль 5)
    apscheduler.add_job(
        check_maintenance_reminders_notification,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[bot],
        id='daily_maintenance_reminders_notification',
        replace_existing=True
    )
    
    apscheduler.start()
    logger.info(f"✅ APScheduler запущен для уведомлений администратору (время: {NOTIFICATION_TIME})")

async def stop_scheduler():
    """Остановка всех планировщиков"""
    global scheduler, apscheduler
    
    # Останавливаем старый планировщик
    if scheduler:
        await scheduler.stop()
    
    # Останавливаем APScheduler
    if apscheduler:
        apscheduler.shutdown()
        logger.info("⏹️ APScheduler остановлен")

