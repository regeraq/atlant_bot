"""
Обработчики для Telegram Mini App (Web App)
"""
import json
import logging
from aiogram import Router, F
from aiogram.types import Message
from bot.database.database import get_car_by_id, add_user
from bot.config import BOOKING_CONTACT_ID

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.web_app_data)
async def process_web_app_data(message: Message):
    """
    Обработчик данных, отправленных из Web App
    
    Ожидаемый формат данных (JSON):
    {
        "action": "book_car",
        "car_id": 1,
        "car_name": "Hyundai Solaris"
    }
    """
    try:
        # Получаем сырые данные из Web App
        raw_data = message.web_app_data.data
        
        # Парсим JSON
        data = json.loads(raw_data)
        
        action = data.get("action")
        
        if action == "book_car":
            car_id = data.get("car_id")
            car_name = data.get("car_name")
            
            # Убеждаемся, что пользователь добавлен в базу данных
            user_id = message.from_user.id
            user_name = message.from_user.first_name or "Пользователь"
            username = message.from_user.username
            
            try:
                await add_user(user_id, username, user_name)
            except Exception as e:
                logger.warning(f"Пользователь уже существует или ошибка добавления: {e}")
            
            # Получаем информацию об автомобиле из базы данных
            car = None
            if car_id:
                car = await get_car_by_id(car_id)
            
            # Формируем ответ пользователю
            if car:
                car_name = car.get('name', car_name)
                daily_price = car.get('daily_price', 0)
                is_available = car.get('available', False)
                
                if not is_available:
                    await message.answer(
                        f"❌ <b>Автомобиль недоступен</b>\n\n"
                        f"🚘 <b>{car_name}</b>\n\n"
                        f"К сожалению, этот автомобиль сейчас недоступен для бронирования.\n"
                        f"Пожалуйста, выберите другой автомобиль из каталога.",
                        parse_mode="HTML"
                    )
                    return
                
                # Форматируем цену
                price_text = f"{daily_price:,} ₽/сутки" if daily_price else "Цена не указана"
                
                # Формируем сообщение с информацией о бронировании
                booking_text = f"""✅ <b>Заявка на бронирование получена!</b>

🚘 <b>Автомобиль:</b> {car_name}
💰 <b>Стоимость:</b> {price_text}

📅 <b>Статус:</b> <i>Проверяю наличие свободных дат...</i>

📞 Наш менеджер свяжется с вами в ближайшее время для подтверждения бронирования.

💡 <i>Вы также можете связаться с менеджером напрямую через кнопку ниже.</i>"""
                
                # Создаем клавиатуру с кнопкой связи с менеджером
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📞 Связаться с менеджером",
                        url=f"tg://user?id={BOOKING_CONTACT_ID}" if BOOKING_CONTACT_ID else None,
                        callback_data="contact_manager" if not BOOKING_CONTACT_ID else None
                    )],
                    [InlineKeyboardButton(
                        text="🚗 Каталог автомобилей",
                        callback_data="back_to_catalog"
                    )]
                ])
                
                await message.answer(
                    booking_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                
                # TODO: Добавить логику сохранения заявки в базу данных
                # TODO: Добавить уведомление администраторам о новой заявке
                logger.info(f"Получена заявка на бронирование: пользователь {user_id}, автомобиль {car_id} ({car_name})")
                
            else:
                # Автомобиль не найден в базе данных
                await message.answer(
                    f"❌ <b>Ошибка</b>\n\n"
                    f"Автомобиль <b>{car_name}</b> не найден в базе данных.\n"
                    f"Пожалуйста, попробуйте выбрать другой автомобиль.",
                    parse_mode="HTML"
                )
        else:
            # Неизвестное действие
            await message.answer(
                "❌ Неизвестное действие из Web App.",
                parse_mode="HTML"
            )
            logger.warning(f"Неизвестное действие из Web App: {action}")
            
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON из Web App: {e}")
        await message.answer(
            "❌ <b>Ошибка обработки данных</b>\n\n"
            "Произошла ошибка при обработке данных бронирования.\n"
            "Пожалуйста, попробуйте еще раз или свяжитесь с менеджером.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке данных Web App: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать вашу заявку. Пожалуйста, попробуйте еще раз или свяжитесь с менеджером.",
            parse_mode="HTML"
        )

