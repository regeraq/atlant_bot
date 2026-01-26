"""
📢 Система универсальной рассылки сообщений
Поддерживает: текст, фото, видео, документы, кнопки
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.database.database import add_broadcast_log
from bot.utils.constants import (
    BROADCAST_BATCH_SIZE, BROADCAST_BATCH_PAUSE_SMALL, 
    BROADCAST_BATCH_PAUSE_LARGE, BROADCAST_LARGE_THRESHOLD,
    MAX_ERRORS_TO_LOG, DB_MAX_TEXT_LENGTH
)

# Типы контента для рассылки
CONTENT_TYPES = {
    'text': 'Текстовое сообщение',
    'photo': 'Фотография с подписью',
    'video': 'Видео с подписью',
    'document': 'Документ с подписью',
    'animation': 'GIF анимация с подписью'
}

class BroadcastManager:
    """Менеджер рассылки сообщений"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def send_broadcast(
        self,
        content_type: str,
        text: Optional[str] = None,
        file_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        admin_id: int = None,
        preview_only: bool = False
    ) -> Dict[str, Any]:
        """
        Отправляет рассылку всем пользователям
        
        Args:
            content_type: Тип контента (text, photo, video, document, animation)
            text: Текст сообщения или подпись
            file_id: ID файла для медиа-контента
            reply_markup: Клавиатура с кнопками
            admin_id: ID администратора, который запустил рассылку
            preview_only: Если True, отправляет только админу для предварительного просмотра
        
        Returns:
            Статистика рассылки
        """
        
        if preview_only and admin_id:
            # Предварительный просмотр только для админа
            try:
                await self._send_message_to_user(
                    user_id=admin_id,
                    content_type=content_type,
                    text=text,
                    file_id=file_id,
                    reply_markup=reply_markup
                )
                return {"preview": True, "success": True}
            except Exception as e:
                return {"preview": True, "success": False, "error": str(e)}
        
        # Получаем пользователей порциями для оптимизации памяти (Fix based on audit)
        # Используем chunked загрузку вместо загрузки всех пользователей в память
        from bot.database.database import get_users_chunked
        
        # Статистика рассылки
        stats = {
            "total": 0,  # Будет подсчитано при обработке
            "sent": 0,
            "failed": 0,
            "blocked": 0,
            "errors": []
        }
        
        # Обрабатываем пользователей порциями (chunks) для оптимизации памяти
        batch_num = 0
        has_users = False
        
        async for users_chunk in get_users_chunked():
            has_users = True
            stats["total"] += len(users_chunk)
            
            # Разбиваем chunk на батчи для отправки
            batches = [users_chunk[i:i + BROADCAST_BATCH_SIZE] for i in range(0, len(users_chunk), BROADCAST_BATCH_SIZE)]
            
            for batch in batches:
                batch_num += 1
                batch_tasks = []
                
                for user in batch:
                    task = self._send_message_to_user(
                        user_id=user['telegram_id'],
                        content_type=content_type,
                        text=text,
                        file_id=file_id,
                        reply_markup=reply_markup
                    )
                    batch_tasks.append(task)
                
                # Выполняем батч параллельно
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Обрабатываем результаты
                for result in batch_results:
                    if isinstance(result, Exception):
                        if "forbidden" in str(result).lower() or "blocked" in str(result).lower():
                            stats["blocked"] += 1
                        else:
                            stats["failed"] += 1
                            stats["errors"].append(str(result))
                    elif result.get("success"):
                        stats["sent"] += 1
                    else:
                        stats["failed"] += 1
                        if "error" in result:
                            stats["errors"].append(result["error"])
                
                # Пауза между батчами для соблюдения rate limit
                # Используем константы из constants.py
                pause_time = BROADCAST_BATCH_PAUSE_SMALL if stats["total"] < BROADCAST_LARGE_THRESHOLD else BROADCAST_BATCH_PAUSE_LARGE
                await asyncio.sleep(pause_time)
        
        if not has_users:
            return {
                "total": 0,
                "sent": 0,
                "failed": 0,
                "blocked": 0,
                "errors": ["Нет пользователей для рассылки"]
            }
        
        # Сохраняем статистику в БД (только если admin_id указан)
        if admin_id:
            try:
                await add_broadcast_log(
                    admin_id=admin_id,
                    content_type=content_type,
                    text=text[:DB_MAX_TEXT_LENGTH] if text else None,  # Используем константу
                    total_users=stats["total"],
                    sent_count=stats["sent"],
                    failed_count=stats["failed"],
                    blocked_count=stats["blocked"]
                )
            except Exception as e:
                self.logger.error(f"Ошибка записи статистики рассылки: {e}")
        
        return stats
    
    async def _send_message_to_user(
        self,
        user_id: int,
        content_type: str,
        text: Optional[str] = None,
        file_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> Dict[str, Any]:
        """Отправляет сообщение одному пользователю"""
        
        try:
            if content_type == 'text':
                await self.bot.send_message(
                    chat_id=user_id,
                    text=text or "Пустое сообщение",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            elif content_type == 'photo':
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            elif content_type == 'video':
                await self.bot.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            elif content_type == 'document':
                await self.bot.send_document(
                    chat_id=user_id,
                    document=file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            elif content_type == 'animation':
                await self.bot.send_animation(
                    chat_id=user_id,
                    animation=file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            return {"success": True}
            
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            return {"success": False, "blocked": True}
        
        except TelegramBadRequest as e:
            # Некорректный запрос
            return {"success": False, "error": f"Некорректный запрос: {e}"}
        
        except Exception as e:
            # Другие ошибки
            return {"success": False, "error": str(e)}

def format_broadcast_stats(stats: Dict[str, Any]) -> str:
    """Форматирует статистику рассылки для отображения"""
    
    if stats.get("preview"):
        if stats.get("success"):
            return "✅ <b>Предварительный просмотр успешен!</b>\n\nВы можете отправить рассылку всем пользователям."
        else:
            return f"❌ <b>Ошибка предварительного просмотра</b>\n\n{stats.get('error', 'Неизвестная ошибка')}"
    
    total = stats.get("total", 0)
    sent = stats.get("sent", 0) 
    failed = stats.get("failed", 0)
    blocked = stats.get("blocked", 0)
    
    success_rate = (sent / total * 100) if total > 0 else 0
    
    result = f"""📊 <b>Статистика рассылки</b>
    
👥 Всего пользователей: <b>{total:,}</b>
✅ Успешно отправлено: <b>{sent:,}</b> ({success_rate:.1f}%)
❌ Не удалось отправить: <b>{failed:,}</b>
🚫 Заблокировали бота: <b>{blocked:,}</b>"""
    
    if stats.get("errors"):
        errors_preview = stats["errors"][:MAX_ERRORS_TO_LOG]  # Используем константу
        errors_text = "\n".join(f"• {error[:100]}" for error in errors_preview)
        if len(stats["errors"]) > MAX_ERRORS_TO_LOG:
            errors_text += f"\n... и еще {len(stats['errors']) - MAX_ERRORS_TO_LOG} ошибок"
        
        result += f"\n\n⚠️ <b>Примеры ошибок:</b>\n{errors_text}"
    
    return result

async def send_new_car_notification(bot: Bot, car_data: dict, admin_id: int = None) -> Dict[str, Any]:
    """
    Автоматическая рассылка уведомления о новой машине всем пользователям
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from bot.database.database import get_contact
    
    broadcast_manager = BroadcastManager(bot)
    
    # Получаем контакт для связи
    contact = await get_contact('booking')
    contact_telegram = contact.get('telegram_username', 'olimp_auto') if contact else 'olimp_auto'
    contact_telegram = contact_telegram.lstrip('@')
    
    car_id = car_data.get('id')
    
    # Формируем красивое сообщение о новой машине
    text = f"""🚗 <b>НОВЫЙ АВТОМОБИЛЬ В АВТОПАРКЕ!</b>

━━━━━━━━━━━━━━━━━━━━━━
🔥 <b>{car_data['name']}</b>
━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Описание:</b>
<i>{car_data.get('description', 'Описание отсутствует')}</i>

💰 <b>Цена аренды:</b> <code>{car_data['daily_price']:,} ₽</code> <i>в сутки</i>

✨ <b>Автомобиль уже доступен для бронирования!</b>

👆 Используйте кнопки ниже для бронирования или связи с менеджером."""
    
    # Создаем клавиатуру с кнопками
    keyboard_buttons = []
    
    # Кнопка "Посмотреть детали" (если есть car_id)
    if car_id:
        keyboard_buttons.append([InlineKeyboardButton(
            text="🚗 Посмотреть детали автомобиля",
            callback_data=f"car_details:{car_id}"
        )])
    
    # Кнопки действий
    action_buttons = []
    
    # Кнопка "Каталог автомобилей" (callback для перехода к каталогу)
    action_buttons.append(InlineKeyboardButton(
        text="📋 Каталог автомобилей",
        callback_data="show_catalog_from_notification"
    ))
    
    # Кнопка связи с менеджером
    action_buttons.append(InlineKeyboardButton(
        text="📞 Связаться с менеджером",
        url=f"https://t.me/{contact_telegram}"
    ))
    
    keyboard_buttons.append(action_buttons)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Отправляем рассылку
    stats = await broadcast_manager.send_broadcast(
        content_type='text',
        text=text,
        reply_markup=keyboard,
        admin_id=admin_id,
        preview_only=False
    )
    
    return stats