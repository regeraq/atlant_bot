from aiogram import types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from bot.database.database import (
    get_all_cars, get_car_by_id, add_user, get_active_rental_by_user
)
from bot.utils.helpers import safe_callback_answer
from datetime import timedelta, datetime
from bot.keyboards.user_keyboards import (
    get_cars_catalog_keyboard, get_car_details_keyboard, 
    get_empty_catalog_keyboard, get_main_menu
)
from bot.config import BOOKING_CONTACT_ID
from bot.database.database import get_contact

async def handle_cars_button(message: Message):
    """Обработчик кнопки 'Автомобили'"""
    # Регистрируем пользователя в базе данных
    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # Получаем все доступные автомобили
    cars = await get_all_cars(available_only=True)
    
    if not cars:
        await message.answer(
            """<b>Автопарк временно недоступен</b>

Мы обновляем автопарк и добавляем новые автомобили.

Попробуйте позже — мы уведомим, когда появятся новые автомобили.""",
            reply_markup=get_empty_catalog_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Отправляем каталог автомобилей с улучшенным дизайном
    from bot.utils.formatters import format_divider
    
    text = f"""🚗 <b>КАТАЛОГ АВТОМОБИЛЕЙ</b>

{format_divider("thin")}
📊 <b>Доступно:</b> {len(cars)} автомобилей
{format_divider("thin")}

💡 <i>Выберите автомобиль для просмотра подробной информации</i>"""
    
    await message.answer(
        text,
        reply_markup=get_cars_catalog_keyboard(cars),
        parse_mode='HTML'
    )

async def handle_cars_page_callback(callback: CallbackQuery):
    """Обработчик пагинации каталога автомобилей"""
    # Извлекаем номер страницы из callback_data
    page = int(callback.data.split(':')[1])
    
    # Получаем все доступные автомобили
    cars = await get_all_cars(available_only=True)
    
    if not cars:
        await callback.message.edit_text(
            """<b>Автопарк временно недоступен</b>

Мы обновляем автопарк и добавляем новые автомобили.

Попробуйте позже — мы уведомим, когда появятся новые автомобили.""",
            reply_markup=get_empty_catalog_keyboard(),
            parse_mode='HTML'
        )
        await safe_callback_answer(callback)
        return
    
    # Обновляем сообщение с новой страницей
    from bot.utils.formatters import format_divider
    
    text = f"""🚗 <b>КАТАЛОГ АВТОМОБИЛЕЙ</b>

{format_divider("thin")}
📊 <b>Доступно:</b> {len(cars)} автомобилей
{format_divider("thin")}

💡 <i>Выберите автомобиль для просмотра подробной информации</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cars_catalog_keyboard(cars, page=page),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

async def handle_car_details_callback(callback: CallbackQuery):
    """Обработчик просмотра детальной информации об автомобиле"""
    # Извлекаем ID автомобиля из callback_data
    car_id = int(callback.data.split(':')[1])
    
    # Получаем информацию об автомобиле
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Формируем детальную информацию с улучшенным дизайном
    from bot.utils.formatters import format_status_badge, format_price, format_divider
    
    status_text = "Доступен" if car['available'] else "Недоступен"
    status_badge = format_status_badge(status_text, car['available'])
    price_formatted = format_price(car['daily_price'])
    
    text = f"""🚗 <b>{car['name']}</b>

{format_divider("thin")}
💰 <b>Цена:</b> {price_formatted}/день
{status_badge}
{format_divider("thin")}

📝 <b>Описание</b>
{car['description']}"""
    
    if not car['available']:
        text += "\n\n<i>Автомобиль временно в аренде</i>"
    
    # Собираем все доступные изображения
    images = []
    for i in range(1, 4):
        image_field = f"image_{i}"
        if car.get(image_field):
            images.append(car[image_field])
    
    # Отправляем фотографии, если они есть
    if images:
        
        if len(images) == 1:
            # Отправляем одну фотографию с описанием
            await callback.message.answer_photo(
                photo=images[0],
                caption=text,
                reply_markup=get_car_details_keyboard(car_id, car['available']),
                parse_mode='HTML'
            )
        else:
            # Отправляем медиа группу
            media_group = []
            for i, image_id in enumerate(images):
                if i == 0:
                    # Добавляем описание к первому изображению
                    media_group.append(InputMediaPhoto(media=image_id, caption=text, parse_mode='HTML'))
                else:
                    media_group.append(InputMediaPhoto(media=image_id))
            
            await callback.message.answer_media_group(media=media_group)
            
            # Отправляем клавиатуру отдельным сообщением
            await callback.message.answer(
                "Выберите действие",
                reply_markup=get_car_details_keyboard(car_id, car['available'])
            )
    else:
        # Если фотографий нет, отправляем только текст
        await callback.message.answer(
            text,
            reply_markup=get_car_details_keyboard(car_id, car['available']),
            parse_mode='HTML'
        )
    
    await safe_callback_answer(callback)

async def handle_back_to_catalog_callback(callback: CallbackQuery):
    """Обработчик возврата к каталогу"""
    # Получаем все доступные автомобили
    cars = await get_all_cars(available_only=True)
    
    # Удаляем предыдущее сообщение (может быть с фотографией)
    try:
        await callback.message.delete()
    except Exception:
        pass  # Игнорируем ошибки удаления
    
    if not cars:
        await callback.message.answer(
            """<b>Автопарк временно недоступен</b>

Мы обновляем автопарк и добавляем новые автомобили.

Попробуйте позже — мы уведомим, когда появятся новые автомобили.""",
            reply_markup=get_empty_catalog_keyboard(),
            parse_mode='HTML'
        )
        await safe_callback_answer(callback)
        return
    
    # Отправляем новое сообщение с каталогом
    from bot.utils.formatters import format_divider
    
    text = f"""🚗 <b>КАТАЛОГ АВТОМОБИЛЕЙ</b>

{format_divider("thin")}
📊 <b>Доступно:</b> {len(cars)} автомобилей
{format_divider("thin")}

💡 <i>Выберите автомобиль для просмотра подробной информации</i>"""
    
    await callback.message.answer(
        text,
        reply_markup=get_cars_catalog_keyboard(cars, page=0),
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

async def handle_refresh_cars_callback(callback: CallbackQuery):
    """Обработчик обновления каталога автомобилей"""
    from datetime import datetime
    
    # Получаем все доступные автомобили
    cars = await get_all_cars(available_only=True)
    
    current_time = datetime.now().strftime('%H:%M:%S')
    
    if not cars:
        text = f"""🚗 <b>КАТАЛОГ АВТОМОБИЛЕЙ</b>

━━━━━━━━━━━━━━━━━━━━━━
🚫 <b>Автопарк временно недоступен</b>
━━━━━━━━━━━━━━━━━━━━━━

Мы обновляем автопарк и добавляем новые автомобили.

Попробуйте позже — мы уведомим, когда появятся новые автомобили.

⏰ Обновлено: {current_time}"""
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_empty_catalog_keyboard(),
                parse_mode='HTML'
            )
        except Exception:
            # Если не удалось отредактировать (например, сообщение слишком старое), отправляем новое
            await callback.message.answer(
                text,
                reply_markup=get_empty_catalog_keyboard(),
                parse_mode='HTML'
            )
        await safe_callback_answer(callback, "🔄 Каталог обновлен")
        return
    
    # Обновляем каталог с временной меткой
    from bot.utils.formatters import format_divider
    
    text = f"""🚗 <b>КАТАЛОГ АВТОМОБИЛЕЙ</b>

{format_divider("thin")}
📊 <b>Доступно:</b> {len(cars)} автомобилей
⏰ <b>Обновлено:</b> {current_time}
{format_divider("thin")}

💡 <i>Выберите автомобиль для просмотра деталей:</i>"""
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_cars_catalog_keyboard(cars, page=0),
            parse_mode='HTML'
        )
    except Exception:
        # Если не удалось отредактировать (например, сообщение слишком старое), отправляем новое
        await callback.message.answer(
            text,
            reply_markup=get_cars_catalog_keyboard(cars, page=0),
            parse_mode='HTML'
        )
    await safe_callback_answer(callback, "🔄 Каталог обновлен")

async def handle_book_car_callback(callback: CallbackQuery):
    """Обработчик бронирования автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Формируем сообщение для бронирования с улучшенным дизайном
    from bot.utils.formatters import format_price, format_divider, format_section
    
    price_formatted = format_price(car['daily_price'])
    
    text = f"""🚗 <b>БРОНИРОВАНИЕ АВТОМОБИЛЯ</b>

{format_divider("thin")}
🚙 <b>{car['name']}</b>
💰 <b>Цена:</b> {price_formatted}/день
{format_divider("thin")}

{format_section(
    "Следующие шаги",
    """1️⃣ Свяжитесь с менеджером
2️⃣ Укажите даты аренды
3️⃣ Подтвердите бронирование

⚡ <b>Менеджер ответит в течение 5 минут!</b>""",
    "📋"
)}"""
    
    # Проверяем, настроен ли контакт для бронирования
    if BOOKING_CONTACT_ID:
        # Создаем клавиатуру с кнопкой для связи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Связаться с менеджером", url=f"tg://user?id={BOOKING_CONTACT_ID}", style="primary")],
            [
                InlineKeyboardButton(text="К автомобилю", callback_data=f"car_details:{car_id}"),
                InlineKeyboardButton(text="Каталог", callback_data="back_to_catalog")
            ],
            [InlineKeyboardButton(text="Главное меню", callback_data="back_to_main")]
        ])
        
    else:
        text = f"""<b>Контакт для бронирования не настроен</b>

Администратор должен настроить контакт.
Свяжитесь с поддержкой через раздел "Контакты"."""
        
        # Клавиатура без кнопки связи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="← К автомобилю", callback_data=f"car_details:{car_id}"),
                InlineKeyboardButton(text="Каталог", callback_data="back_to_catalog")
            ],
            [InlineKeyboardButton(text="Контакты", callback_data="back_to_main")]
        ])
    
    # Отправляем новое сообщение с информацией о бронировании
    await callback.message.answer(
        text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    if BOOKING_CONTACT_ID:
        await safe_callback_answer(callback, "Нажмите кнопку для связи с менеджером")
    else:
        await safe_callback_answer(callback, "Контакт для бронирования не настроен", show_alert=True)

async def handle_car_unavailable_callback(callback: CallbackQuery):
    """Обработчик недоступного автомобиля"""
    await safe_callback_answer(callback, "Этот автомобиль сейчас недоступен", show_alert=True)

async def handle_notify_car_callback(callback: CallbackQuery):
    """Обработчик уведомления о появлении автомобиля"""
    car_id = int(callback.data.split(':')[1])
    car = await get_car_by_id(car_id)
    
    if not car:
        await safe_callback_answer(callback, "❌ Автомобиль не найден", show_alert=True)
        return
    
    # Здесь можно добавить логику сохранения подписки на уведомления
    # Пока просто подтверждаем
    await safe_callback_answer(
        callback,
        f"Вы будете уведомлены, когда {car['name']} станет доступен",
        show_alert=True
    )

async def handle_page_info_callback(callback: CallbackQuery):
    """Обработчик информации о странице"""
    await safe_callback_answer(callback, "Информация о текущей странице каталога")

async def handle_user_profile(message: Message):
    """Обработчик просмотра профиля пользователя с улучшенным дизайном (Bot API 9.4)"""
    from bot.keyboards.user_keyboards import get_main_menu, get_profile_keyboard
    from bot.utils.formatters import (
        format_profile_header, format_section, format_info_line,
        format_status_badge, format_rental_summary, format_divider,
        format_days_count, format_deposit_status
    )
    from datetime import datetime
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    # Получаем активную аренду пользователя
    rental = await get_active_rental_by_user(user_id)
    
    if rental:
        # У пользователя есть активная аренда
        car_name = rental.get('car_name', 'Неизвестный автомобиль')
        daily_price = rental.get('daily_price', 0)
        price_formatted = f"{daily_price:,} ₽"
        reminder_time = rental.get('reminder_time', '12:00')
        reminder_type = rental.get('reminder_type', 'daily')
        start_date = rental.get('start_date', '')
        end_date = rental.get('end_date', '')
        referral_discount = rental.get('referral_discount_percentage', 0) or 0
        deposit_amount = float(rental.get('deposit_amount', 0) or 0)
        deposit_status = rental.get('deposit_status', 'pending')
        
        # Вычисляем количество дней аренды
        days_rented = 0
        try:
            if start_date:
                if isinstance(start_date, str):
                    start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                else:
                    start_date_obj = start_date
                start_date_formatted = start_date_obj.strftime('%d.%m.%Y')
                days_rented = (datetime.now().date() - start_date_obj.date()).days
            else:
                start_date_formatted = 'Не указана'
        except (ValueError, TypeError, AttributeError):
            start_date_formatted = 'Не указана'
        
        type_names = {
            'daily': 'Каждый день',
            'weekly': 'Каждую неделю (7 дней)',
            'monthly': 'Каждый месяц (30 дней)'
        }
        type_name = type_names.get(reminder_type, 'Каждый день')
        
        # Вычисляем следующую дату напоминания
        next_reminder_text = ""
        if start_date and reminder_type != 'daily':
            try:
                if isinstance(start_date, str):
                    start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                else:
                    start_date_obj = start_date
                start_date_only = start_date_obj.date()
                current_date = datetime.now().date()
                
                if reminder_type == 'weekly':
                    days_passed = (current_date - start_date_only).days
                    next_reminder_days = 7 - (days_passed % 7)
                    if next_reminder_days == 7:
                        next_reminder_days = 0
                    next_reminder_date = current_date + timedelta(days=next_reminder_days)
                    next_reminder_text = f"\n📅 <b>Следующее напоминание:</b> {next_reminder_date.strftime('%d.%m.%Y')}"
                elif reminder_type == 'monthly':
                    days_passed = (current_date - start_date_only).days
                    next_reminder_days = 30 - (days_passed % 30)
                    if next_reminder_days == 30:
                        next_reminder_days = 0
                    next_reminder_date = current_date + timedelta(days=next_reminder_days)
                    next_reminder_text = f"\n📅 <b>Следующее напоминание:</b> {next_reminder_date.strftime('%d.%m.%Y')}"
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Форматируем дату окончания
        end_date_formatted = 'Не указана'
        if end_date:
            try:
                if isinstance(end_date, str):
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    end_date_obj = end_date
                end_date_formatted = end_date_obj.strftime('%d.%m.%Y')
            except:
                pass
        
        # Форматируем информацию с использованием новых утилит
        from bot.utils.formatters import format_price, format_date as fmt_date
        
        # Расчет общей стоимости
        total_cost = daily_price * days_rented
        if referral_discount > 0:
            discount_amount = total_cost * (referral_discount / 100)
            total_cost -= discount_amount
            discount_info = f"\n🎁 <b>Скидка {referral_discount}%:</b> -{format_price(discount_amount)}"
        else:
            discount_info = ""
        
        # Информация о залоге
        deposit_info = ""
        if deposit_amount > 0:
            deposit_emoji, deposit_status_text = format_deposit_status(deposit_status)
            deposit_info = f"\n{deposit_emoji} <b>Залог:</b> {format_price(deposit_amount)} ({deposit_status_text})"
        
        # Создаем красивый профиль
        header = format_profile_header(user_name)
        divider = format_divider("thick")
        
        # Секция аренды - создаем вручную для лучшего контроля
        days_text = format_days_count(days_rented)
        price_text = format_price(daily_price)
        total_cost = daily_price * days_rented
        
        discount_info = ""
        if referral_discount > 0:
            discount_amount = total_cost * (referral_discount / 100)
            total_cost -= discount_amount
            discount_info = f"\n🎁 <b>Скидка {referral_discount}%:</b> -{format_price(discount_amount)}"
        
        deposit_info = ""
        if deposit_amount > 0:
            deposit_emoji, deposit_status_text = format_deposit_status(deposit_status)
            deposit_info = f"\n{deposit_emoji} <b>Залог:</b> {format_price(deposit_amount)} ({deposit_status_text})"
        
        rental_section = f"""
🚗 <b>{car_name}</b>

💰 <b>Стоимость:</b> {price_text}/день
📅 <b>Начало:</b> {start_date_formatted}
📅 <b>Окончание:</b> {end_date_formatted}
📆 <b>Дней в аренде:</b> {days_text}
💵 <b>Общая стоимость:</b> {format_price(total_cost)}{discount_info}{deposit_info}
"""
        
        # Секция напоминаний
        reminder_emoji = "⏰" if reminder_type == 'daily' else "📅"
        reminder_section = f"""
{reminder_emoji} <b>Напоминания об оплате</b>
{format_info_line("Время", reminder_time, "🕐")}
{format_info_line("Частота", type_name, "🔄")}{next_reminder_text}
"""
        
        # Статус аренды
        status_badge = format_status_badge("Активная аренда", True)
        
        text = f"""{header}

{divider}

{status_badge}

{rental_section}

{reminder_section}

{divider}

💡 <i>Для вопросов свяжитесь с менеджером</i>"""
        
        # Создаем красивую клавиатуру
        from bot.keyboards.user_keyboards import get_profile_keyboard
        from bot.database.database import get_setting
        referral_enabled = await get_setting('referral_system_enabled')
        
        profile_keyboard = get_profile_keyboard(
            has_rental=True,
            referral_enabled=(referral_enabled == 'true'),
            booking_contact_id=BOOKING_CONTACT_ID
        )
        
        # Если есть изображения автомобиля, отправляем их
        images = []
        for i in range(1, 4):
            image_field = f"image_{i}"
            if rental.get(image_field):
                images.append(rental[image_field])
        
        if images:
            from aiogram.types import InputMediaPhoto
            
            if len(images) == 1:
                await message.answer_photo(
                    photo=images[0],
                    caption=text,
                    reply_markup=profile_keyboard,
                    parse_mode='HTML'
                )
            else:
                media_group = []
                for i, image_id in enumerate(images):
                    if i == 0:
                        media_group.append(InputMediaPhoto(media=image_id, caption=text, parse_mode='HTML'))
                    else:
                        media_group.append(InputMediaPhoto(media=image_id))
                
                await message.answer_media_group(media=media_group)
                await message.answer(
                    "Информация об аренде",
                    reply_markup=profile_keyboard
                )
        else:
            await message.answer(
                text,
                reply_markup=profile_keyboard,
                parse_mode='HTML'
            )
    else:
        # У пользователя нет активной аренды - красивый дизайн
        header = format_profile_header(user_name)
        divider = format_divider("thick")
        status_badge = format_status_badge("Нет активной аренды", False)
        
        text = f"""{header}

{divider}

{status_badge}

{format_section(
    "Как взять автомобиль в аренду",
    """1️⃣ Просмотрите каталог автомобилей
2️⃣ Выберите понравившийся автомобиль
3️⃣ Свяжитесь с менеджером для бронирования

⚡ <b>Быстрое оформление — всего 5 минут!</b>""",
    "🚗"
)}

{divider}

💡 <i>Начните с просмотра каталога</i>"""
        
        from bot.keyboards.user_keyboards import get_profile_keyboard
        from bot.database.database import get_setting
        
        referral_enabled = await get_setting('referral_system_enabled')
        
        profile_keyboard = get_profile_keyboard(
            has_rental=False,
            referral_enabled=(referral_enabled == 'true'),
            booking_contact_id=None
        )
        
        await message.answer(
            text,
            reply_markup=profile_keyboard,
            parse_mode='HTML'
        )


# Модуль 6: Реферальная система
async def handle_user_invite_friend_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Пригласить друга' (Модуль 6)"""
    from bot.database.database import ensure_user_referral_code, get_setting
    from bot.config import BOT_TOKEN
    from aiogram import Bot
    
    # Проверяем, включена ли реферальная система
    referral_enabled = await get_setting('referral_system_enabled')
    if referral_enabled != 'true':
        await safe_callback_answer(callback, "❌ Реферальная система отключена", show_alert=True)
        return
    
    # Получаем или генерируем реферальный код пользователя
    user_id = callback.from_user.id
    referral_code = await ensure_user_referral_code(user_id)
    
    if not referral_code:
        await safe_callback_answer(callback, "❌ Ошибка при генерации реферального кода", show_alert=True)
        return
    
    # Получаем процент бонуса
    bonus_percentage = await get_setting('referral_bonus_percentage')
    bonus_percentage = int(bonus_percentage) if bonus_percentage else 10
    
    # Получаем срок действия бонуса
    bonus_duration = await get_setting('referral_bonus_duration_days')
    bonus_duration = int(bonus_duration) if bonus_duration else 30
    
    # Получаем имя бота - используем бота из callback вместо создания нового
    bot_username = "your_bot"  # Fallback
    try:
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
    except Exception as e:
        logger.warning(f"Не удалось получить имя бота: {e}")
        # Пытаемся создать новый экземпляр бота только если нужно
        try:
            bot = Bot(token=BOT_TOKEN)
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            await bot.session.close()
        except:
            pass
    
    referral_link = f"t.me/{bot_username}?start={referral_code}"
    
    # Проверяем, может ли пользователь получить бонус за пригласившего
    from bot.database.database import check_user_referral_bonus_eligibility
    bonus_info = await check_user_referral_bonus_eligibility(user_id)
    
    bonus_status_text = ""
    if bonus_info:
        days_remaining = bonus_info.get('days_remaining', 0)
        bonus_status_text = f"\n\n🎁 <b>У вас активный бонус!</b>\nОсталось дней для использования: <b>{days_remaining}</b>"
    else:
        bonus_status_text = f"\n\n💡 <i>Бонус действует в течение {bonus_duration} дней после регистрации приглашенного друга</i>"
    
    text = f"""🤝 <b>ПРИГЛАСИТЬ ДРУГА</b>

━━━━━━━━━━━━━━━━━━━━━━
📎 <b>Ваша персональная ссылка:</b>

<code>{referral_link}</code>

💡 <b>Как это работает:</b>
• Ваш друг получит скидку <b>{bonus_percentage}%</b> на первую аренду
• Скидка действует <b>{bonus_duration} дней</b> после регистрации
• Бонус можно использовать только один раз{bonus_status_text}

━━━━━━━━━━━━━━━━━━━━━━

📋 <i>Поделитесь этой ссылкой с друзьями!</i>"""
    
    await callback.message.edit_text(text, parse_mode='HTML')
    await safe_callback_answer(callback)