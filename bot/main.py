import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from bot.utils.helpers import safe_callback_answer

from bot.config import BOT_TOKEN
from bot.database.database import init_db, add_sample_cars, add_user, add_admin, is_admin, get_all_admins, get_contact
from bot.database.db_pool import db_pool
from bot.keyboards.user_keyboards import get_main_menu
from bot.keyboards.admin_keyboards import get_admin_main_menu
from bot.handlers.user_handlers import (
    handle_cars_button, handle_cars_page_callback, handle_car_details_callback,
    handle_back_to_catalog_callback, handle_refresh_cars_callback,
    handle_book_car_callback, handle_car_unavailable_callback,
    handle_page_info_callback, handle_notify_car_callback
)
from bot.handlers.admin import (
    handle_admin_panel_button, handle_admin_panel_callback,
    handle_admin_manage_cars_callback, handle_admin_cars_page_callback,
    handle_admin_edit_car_callback, handle_admin_add_car_callback,
    handle_admin_stats_callback, handle_delete_car_callback,
    handle_confirm_delete_car_callback, handle_edit_car_status_callback,
    handle_admin_manage_admins_callback, handle_admin_add_admin_callback, handle_admin_list_admins_callback,
    handle_admin_delete_admin_callback, handle_admin_confirm_delete_admin_callback,
    handle_admin_confirm_delete_admin_final_callback,
    handle_admin_refresh_cars_callback, handle_admin_refresh_stats_callback, handle_admin_page_info_callback,
    handle_car_name_input, handle_car_description_input, handle_car_price_input,
    handle_edit_car_name_callback, handle_edit_car_desc_callback, handle_edit_car_price_callback,
    handle_new_car_name_input, handle_new_car_desc_input, handle_new_car_price_input,
    handle_cancel_action_callback, CarCreationStates, CarEditStates, AdminManagementStates,
    handle_edit_car_images_callback, handle_upload_image_callback, handle_delete_image_callback,
    handle_car_image_1_input, handle_car_image_2_input, handle_car_image_3_input, CarImageStates,
    handle_admin_id_input, handle_admin_export_db_callback, RentalManagementStates,
    handle_admin_rental_user_input, handle_admin_rental_reminder_time_input,
    handle_admin_rental_reminder_time_update, handle_admin_rental_reminder_type_callback,
    handle_admin_manage_rentals_callback, handle_admin_add_rental_callback,
    handle_admin_select_car_for_rental_callback, handle_admin_rental_cars_page_callback,
    handle_admin_rental_details_callback, handle_admin_rental_reminder_callback,
    handle_admin_rental_end_date_callback, handle_admin_rental_end_date_update,
    handle_admin_end_rental_callback, handle_admin_confirm_end_rental_callback,
    handle_admin_rentals_page_callback, handle_admin_refresh_rentals_callback,
    ContactManagementStates,
    handle_car_add_images_callback, handle_car_skip_images_callback,
    handle_car_broadcast_yes_callback, handle_car_broadcast_no_callback
)
from bot.handlers.contact_handlers import (
    handle_admin_manage_contacts_callback,
    handle_admin_contact_edit_name_callback, handle_admin_contact_edit_phone_callback,
    handle_admin_contact_edit_telegram_callback, handle_contact_name_input,
    handle_contact_phone_input, handle_contact_telegram_input
)
from bot.handlers.admin.user_notes import (
    handle_user_notes_callback, handle_user_note_add_callback,
    handle_user_note_text_input, handle_user_note_delete_callback
)
from bot.handlers.admin.incidents import (
    handle_rental_incidents_callback, handle_incident_add_callback,
    handle_incident_type_callback, handle_incident_description_input,
    handle_incident_amount_input, handle_incident_photo_decision_callback,
    handle_incident_photo_input, handle_incident_delete_callback
)
from bot.handlers.admin.maintenance import (
    handle_car_maintenance_callback, handle_maintenance_add_callback,
    handle_maintenance_type_callback, handle_maintenance_description_input,
    handle_maintenance_mileage_input, handle_maintenance_event_date_input,
    handle_maintenance_reminder_decision_callback, handle_maintenance_reminder_date_input,
    handle_maintenance_remove_reminder_callback
)
from bot.handlers.admin.referral import (
    handle_referral_system_callback, handle_referral_toggle_callback,
    handle_referral_edit_percentage_callback, handle_referral_percentage_input,
    handle_referral_edit_duration_callback, handle_referral_duration_input
)
from bot.handlers.admin.states import UserNotesStates, IncidentManagementStates, MaintenanceStates, ReferralManagementStates
from bot.handlers.broadcast_handlers import (
    handle_admin_broadcast_callback, handle_broadcast_text_callback,
    handle_broadcast_photo_callback, handle_broadcast_video_callback, 
    handle_broadcast_document_callback, handle_broadcast_text_input,
    handle_broadcast_media_input, handle_broadcast_preview_callback,
    handle_broadcast_send_all_callback, handle_broadcast_confirm_send_callback,
    handle_broadcast_history_callback, handle_broadcast_reset_callback,
    handle_broadcast_cancel_callback, BroadcastStates
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Проверяем наличие реального токена
if BOT_TOKEN == "TEST_TOKEN" or not BOT_TOKEN:
    print("🤖 Telegram Bot Rental Car - Структура проекта готова!")
    print("=" * 50)
    print("✅ База данных SQLite настроена")
    print("✅ Модели таблиц созданы (users, admins, cars)")
    print("✅ Обработчики команд готовы (/start, /help)")
    print("✅ Клавиатуры интерфейса настроены")
    print("=" * 50)
    print("⚠️  Для запуска бота установите BOT_TOKEN:")
    print("1. Создайте бота через @BotFather в Telegram")
    print("2. Установите переменную: export BOT_TOKEN='ваш_токен'")
    print("3. Перезапустите бота")
    print("=" * 50)
    exit(0)

# Создание объектов бота и диспетчера только с валидным токеном
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# === ОБРАБОТЧИКИ КОМАНД (должны быть первыми) ===

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start (Модули 6, 7: поддержка рефералов и UTM)"""
    from bot.database.database import (
        get_user_by_referral_code, set_user_referrer, 
        ensure_user_referral_code, update_user_source
    )
    
    # Парсим параметры команды /start (реферальный код или UTM-метка)
    referral_code = None
    source = None
    
    if message.text and len(message.text.split()) > 1:
        # Получаем параметр после /start
        param = message.text.split()[1]
        
        # Проверяем, является ли это реферальным кодом (Модуль 6)
        referrer_user = await get_user_by_referral_code(param)
        if referrer_user:
            referral_code = param
            # referrer_id будет установлен после регистрации пользователя
        else:
            # Это может быть UTM-метка (Модуль 7)
            # Ограничиваем длину UTM-метки до 100 символов
            source = param[:100] if len(param) > 100 else param
    
    # Регистрируем пользователя в базе данных
    is_new_user = False
    if message.from_user:
        is_new_user = await add_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            referral_code=None,  # Будет сгенерирован отдельно
            source=source  # Модуль 7
        )
        
        # Если это новый пользователь и есть реферальный код, устанавливаем реферера (Модуль 6)
        if is_new_user and referral_code and referrer_user:
            # Проверка на self-referral: пользователь не может использовать свой собственный реферальный код
            if referrer_user['telegram_id'] != message.from_user.id:
                await set_user_referrer(message.from_user.id, referrer_user['telegram_id'])
            else:
                logger.warning(f"Попытка self-referral предотвращена для пользователя {message.from_user.id}")
        
        # Гарантируем наличие реферального кода у пользователя (Модуль 6)
        await ensure_user_referral_code(message.from_user.id)
    
    user_name = message.from_user.first_name if message.from_user else "пользователь"
    if not user_name:
        user_name = "пользователь"
    
    # Проверяем, является ли пользователь администратором
    user_is_admin = False
    if message.from_user:
        user_is_admin = await is_admin(message.from_user.id)
    
    if user_is_admin:
        welcome_text = f"""👋 <b>Добро пожаловать, {user_name}!</b>

🔧 <b>Панель администратора</b>

📋 <b>Доступные функции:</b>
• 🚗 Управление автопарком
• 📝 Работа с арендой
• 📢 Рассылка сообщений
• 📊 Статистика
• 👥 Управление доступом
• 📞 Управление контактами

👇 Используйте кнопки меню для навигации."""
        reply_markup = get_admin_main_menu()
    else:
        # Получаем минимальную цену из доступных автомобилей
        from bot.database.database import get_all_cars
        available_cars = await get_all_cars(available_only=True)
        
        if available_cars:
            min_price = min(car['daily_price'] for car in available_cars)
        else:
            min_price = 5000  # Значение по умолчанию, если нет доступных машин
        
        welcome_text = f"""👋 <b>Добро пожаловать, {user_name}!</b>

🚗 <b>OLIMP AUTO</b>
Аренда автомобилей с правом выкупа

🎯 <b>Почему выбирают нас:</b>
• 🚙 Широкий выбор автомобилей
• 💰 От {min_price:,} ₽/сутки
• ⚡ Быстрое оформление
• 🛡️ Полная поддержка 24/7

👇 Используйте кнопки меню для навигации."""
        reply_markup = get_main_menu()
    
    await message.answer(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """<b>📚 Справка</b>

<b>Команды</b>
/start — главное меню
/help — эта справка

<b>Функции</b>
• 🚗 Каталог автомобилей — просмотр доступных машин
• 👤 Мой профиль — информация об активной аренде
• 📞 Контакты — связь с менеджером

Используйте кнопки меню для навигации."""
    
    await message.answer(help_text, parse_mode='HTML')

# === ОБРАБОТЧИКИ CALLBACK QUERIES (ПОЛЬЗОВАТЕЛИ) ===

@dp.callback_query(F.data.startswith("cars_page:"))
async def callback_cars_page(callback: CallbackQuery):
    """Обработчик пагинации каталога"""
    await handle_cars_page_callback(callback)

@dp.callback_query(F.data.startswith("car_details:"))
async def callback_car_details(callback: CallbackQuery):
    """Обработчик детальной информации об автомобиле"""
    await handle_car_details_callback(callback)

@dp.callback_query(F.data == "back_to_catalog")
async def callback_back_to_catalog(callback: CallbackQuery):
    """Обработчик возврата к каталогу"""
    await handle_back_to_catalog_callback(callback)

@dp.callback_query(F.data == "refresh_cars")
async def callback_refresh_cars(callback: CallbackQuery):
    """Обработчик обновления каталога"""
    await handle_refresh_cars_callback(callback)

@dp.callback_query(F.data.startswith("book_car:"))
async def callback_book_car(callback: CallbackQuery):
    """Обработчик бронирования автомобиля"""
    await handle_book_car_callback(callback)

@dp.callback_query(F.data == "car_unavailable")
async def callback_car_unavailable(callback: CallbackQuery):
    """Обработчик недоступного автомобиля"""
    await handle_car_unavailable_callback(callback)

@dp.callback_query(F.data.startswith("notify_car:"))
async def callback_notify_car(callback: CallbackQuery):
    """Обработчик уведомления о появлении автомобиля"""
    await handle_notify_car_callback(callback)

@dp.callback_query(F.data == "contact_manager")
async def callback_contact_manager(callback: CallbackQuery):
    """Обработчик связи с менеджером"""
    from bot.database.database import get_contact
    contact = await get_contact('booking')
    if contact and (contact.get('telegram_id') or contact.get('telegram_username')):
        await safe_callback_answer(
            callback,
            "Нажмите на кнопку выше, чтобы связаться с менеджером",
            show_alert=True
        )
    else:
        await safe_callback_answer(
            callback,
            "Контакт менеджера не настроен. Обратитесь к администратору.",
            show_alert=True
        )

@dp.callback_query(F.data == "show_phone_number")
async def callback_show_phone_number(callback: CallbackQuery):
    """Показ номера телефона для копирования"""
    from bot.database.database import get_contact
    contact = await get_contact('booking')
    
    if contact:
        phone = contact.get('phone', 'Не указан')
        await safe_callback_answer(
            callback,
            f"📱 Номер телефона: {phone}\n\nВы можете скопировать его из сообщения выше.",
            show_alert=True
        )
        # Отправляем номер отдельным сообщением для удобного копирования
        await callback.message.answer(
            f"📱 <b>Номер телефона для связи:</b>\n\n<code>{phone}</code>\n\n💡 <i>Нажмите на номер, чтобы скопировать</i>",
            parse_mode='HTML'
        )
    else:
        await safe_callback_answer(
            callback,
            "Контакт не настроен. Обратитесь к администратору.",
            show_alert=True
        )

@dp.callback_query(F.data == "page_info")
async def callback_page_info(callback: CallbackQuery):
    """Обработчик информации о странице"""
    await handle_page_info_callback(callback)

@dp.callback_query(F.data == "user_invite_friend")
async def callback_user_invite_friend(callback: CallbackQuery):
    """Обработчик кнопки 'Пригласить друга' (Модуль 6)"""
    from bot.handlers.user_handlers import handle_user_invite_friend_callback
    await handle_user_invite_friend_callback(callback)

# === ОБРАБОТЧИКИ CALLBACK QUERIES (АДМИНИСТРАТОРЫ) ===

@dp.callback_query(F.data == "back_to_admin_panel")
async def callback_back_to_admin_panel(callback: CallbackQuery):
    """Возврат в админ панель"""
    await handle_admin_panel_callback(callback)

@dp.callback_query(F.data == "admin_manage_cars")
async def callback_admin_manage_cars(callback: CallbackQuery):
    """Управление автомобилями"""
    await handle_admin_manage_cars_callback(callback)

@dp.callback_query(F.data.startswith("admin_cars_page:"))
async def callback_admin_cars_page(callback: CallbackQuery):
    """Пагинация админ автомобилей"""
    await handle_admin_cars_page_callback(callback)

@dp.callback_query(F.data.startswith("admin_edit_car:"))
async def callback_admin_edit_car(callback: CallbackQuery):
    """Редактирование автомобиля"""
    await handle_admin_edit_car_callback(callback)

@dp.callback_query(F.data == "admin_add_car")
async def callback_admin_add_car(callback: CallbackQuery, state: FSMContext):
    """Добавление автомобиля"""
    await handle_admin_add_car_callback(callback, state)

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика"""
    await handle_admin_stats_callback(callback)

@dp.callback_query(F.data.startswith("delete_car:"))
async def callback_delete_car(callback: CallbackQuery):
    """Подтверждение удаления автомобиля"""
    await handle_delete_car_callback(callback)

@dp.callback_query(F.data.startswith("confirm_delete_car:"))
async def callback_confirm_delete_car(callback: CallbackQuery):
    """Окончательное удаление автомобиля"""
    await handle_confirm_delete_car_callback(callback)

@dp.callback_query(F.data.startswith("edit_car_status:"))
async def callback_edit_car_status(callback: CallbackQuery):
    """Изменение статуса автомобиля"""
    await handle_edit_car_status_callback(callback)

@dp.callback_query(F.data == "admin_manage_admins")
async def callback_admin_manage_admins(callback: CallbackQuery):
    """Управление админами"""
    await handle_admin_manage_admins_callback(callback)

@dp.callback_query(F.data == "admin_add_admin")
async def callback_admin_add_admin(callback: CallbackQuery, state: FSMContext):
    """Добавление администратора"""
    await handle_admin_add_admin_callback(callback, state)

@dp.callback_query(F.data == "admin_list_admins")
async def callback_admin_list_admins(callback: CallbackQuery):
    """Список администраторов"""
    await handle_admin_list_admins_callback(callback)

@dp.callback_query(F.data == "admin_delete_admin")
async def callback_admin_delete_admin(callback: CallbackQuery):
    """Удаление администратора"""
    await handle_admin_delete_admin_callback(callback)

@dp.callback_query(F.data.startswith("admin_confirm_delete_admin:"))
async def callback_admin_confirm_delete_admin(callback: CallbackQuery):
    """Подтверждение удаления администратора"""
    await handle_admin_confirm_delete_admin_callback(callback)

@dp.callback_query(F.data.startswith("admin_confirm_delete_admin_final:"))
async def callback_admin_confirm_delete_admin_final(callback: CallbackQuery):
    """Окончательное удаление администратора"""
    await handle_admin_confirm_delete_admin_final_callback(callback)

@dp.callback_query(F.data == "admin_refresh_cars")
async def callback_admin_refresh_cars(callback: CallbackQuery):
    """Обновление списка автомобилей"""
    await handle_admin_refresh_cars_callback(callback)

@dp.callback_query(F.data == "admin_refresh_stats")
async def callback_admin_refresh_stats(callback: CallbackQuery):
    """Обновление статистики"""
    await handle_admin_refresh_stats_callback(callback)

@dp.callback_query(F.data == "admin_page_info")
async def callback_admin_page_info(callback: CallbackQuery):
    """Информация о странице админки"""
    await handle_admin_page_info_callback(callback)

@dp.callback_query(F.data == "admin_export_db")
async def callback_admin_export_db(callback: CallbackQuery):
    """Выгрузка базы данных"""
    await handle_admin_export_db_callback(callback)

@dp.callback_query(F.data == "admin_manage_contacts")
async def callback_admin_manage_contacts(callback: CallbackQuery):
    """Управление контактами"""
    await handle_admin_manage_contacts_callback(callback)

@dp.callback_query(F.data == "admin_contact_edit_name")
async def callback_admin_contact_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование имени контакта"""
    await handle_admin_contact_edit_name_callback(callback, state)

@dp.callback_query(F.data == "admin_contact_edit_phone")
async def callback_admin_contact_edit_phone(callback: CallbackQuery, state: FSMContext):
    """Редактирование телефона контакта"""
    await handle_admin_contact_edit_phone_callback(callback, state)

@dp.callback_query(F.data == "admin_contact_edit_telegram")
async def callback_admin_contact_edit_telegram(callback: CallbackQuery, state: FSMContext):
    """Редактирование Telegram контакта"""
    await handle_admin_contact_edit_telegram_callback(callback, state)

# === ОБРАБОТЧИКИ УПРАВЛЕНИЯ АРЕНДОЙ ===

@dp.callback_query(F.data == "admin_manage_rentals")
async def callback_admin_manage_rentals(callback: CallbackQuery):
    """Управление арендой"""
    await handle_admin_manage_rentals_callback(callback)

@dp.callback_query(F.data == "admin_add_rental")
async def callback_admin_add_rental(callback: CallbackQuery, state: FSMContext):
    """Добавление аренды"""
    await handle_admin_add_rental_callback(callback, state)

@dp.callback_query(F.data.startswith("admin_rental_details:"))
async def callback_admin_rental_details(callback: CallbackQuery):
    """Детали аренды"""
    await handle_admin_rental_details_callback(callback)

@dp.callback_query(F.data.startswith("admin_rental_reminder:"))
async def callback_admin_rental_reminder(callback: CallbackQuery, state: FSMContext):
    """Изменение времени напоминания"""
    await handle_admin_rental_reminder_callback(callback, state)

@dp.callback_query(F.data.startswith("admin_rental_end_date:"))
async def callback_admin_rental_end_date(callback: CallbackQuery, state: FSMContext):
    """Изменение даты окончания аренды"""
    await handle_admin_rental_end_date_callback(callback, state)

@dp.callback_query(F.data.startswith("admin_end_rental:"))
async def callback_admin_end_rental(callback: CallbackQuery):
    """Подтверждение завершения аренды"""
    await handle_admin_end_rental_callback(callback)

@dp.callback_query(F.data.startswith("admin_confirm_end_rental:"))
async def callback_admin_confirm_end_rental(callback: CallbackQuery):
    """Окончательное завершение аренды"""
    await handle_admin_confirm_end_rental_callback(callback)

@dp.callback_query(F.data.startswith("admin_rentals_page:"))
async def callback_admin_rentals_page(callback: CallbackQuery):
    """Пагинация аренд"""
    await handle_admin_rentals_page_callback(callback)

@dp.callback_query(F.data == "admin_refresh_rentals")
async def callback_admin_refresh_rentals(callback: CallbackQuery):
    """Обновление списка аренд"""
    await handle_admin_refresh_rentals_callback(callback)

@dp.callback_query(F.data == "admin_rentals_page_info")
async def callback_admin_rentals_page_info(callback: CallbackQuery):
    """Информация о странице аренд"""
    await safe_callback_answer(callback, "📄 Информация о текущей странице")

# === ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ АВТОМОБИЛЕЙ ===

@dp.callback_query(F.data.startswith("edit_car_name:"))
async def callback_edit_car_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия автомобиля"""
    await handle_edit_car_name_callback(callback, state)

@dp.callback_query(F.data.startswith("edit_car_desc:"))
async def callback_edit_car_desc(callback: CallbackQuery, state: FSMContext):
    """Редактирование описания автомобиля"""
    await handle_edit_car_desc_callback(callback, state)

@dp.callback_query(F.data.startswith("edit_car_price:"))
async def callback_edit_car_price(callback: CallbackQuery, state: FSMContext):
    """Редактирование цены автомобиля"""
    await handle_edit_car_price_callback(callback, state)

@dp.callback_query(F.data == "cancel_action")
async def callback_cancel_action(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены действия с очисткой состояния"""
    await handle_cancel_action_callback(callback, state)

# === ОБРАБОТЧИКИ УПРАВЛЕНИЯ ИЗОБРАЖЕНИЯМИ ===

@dp.callback_query(F.data.startswith("edit_car_images:"))
async def callback_edit_car_images(callback: CallbackQuery):
    """Управление изображениями автомобиля"""
    await handle_edit_car_images_callback(callback)

@dp.callback_query(F.data.startswith("upload_image_"))
async def callback_upload_image(callback: CallbackQuery, state: FSMContext):
    """Начало загрузки изображения"""
    await handle_upload_image_callback(callback, state)

@dp.callback_query(F.data.startswith("delete_image_"))
async def callback_delete_image(callback: CallbackQuery):
    """Удаление изображения"""
    await handle_delete_image_callback(callback)

@dp.callback_query(F.data.startswith("car_add_images:"))
async def callback_car_add_images(callback: CallbackQuery, state: FSMContext):
    """Начало добавления фотографий при создании автомобиля"""
    await handle_car_add_images_callback(callback, state)

@dp.callback_query(F.data.startswith("car_skip_images:"))
async def callback_car_skip_images(callback: CallbackQuery, state: FSMContext):
    """Пропуск добавления фотографий"""
    await handle_car_skip_images_callback(callback, state, bot)

@dp.callback_query(F.data.startswith("car_broadcast_yes:"))
async def callback_car_broadcast_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение рассылки о новом автомобиле"""
    await handle_car_broadcast_yes_callback(callback, state, bot)

@dp.callback_query(F.data.startswith("car_broadcast_no:"))
async def callback_car_broadcast_no(callback: CallbackQuery, state: FSMContext):
    """Отказ от рассылки о новом автомобиле"""
    await handle_car_broadcast_no_callback(callback, state)

@dp.callback_query(F.data == "show_catalog_from_notification")
async def callback_show_catalog_from_notification(callback: CallbackQuery):
    """Показ каталога из уведомления о новом автомобиле"""
    from bot.handlers.user_handlers import handle_cars_button
    # Создаем фейковое сообщение для вызова handle_cars_button
    class FakeMessage:
        """Вспомогательный класс для имитации Message из CallbackQuery"""
        def __init__(self, callback_msg, user):
            self.message_id = callback_msg.message_id
            self.chat = callback_msg.chat
            self.from_user = user
            self.text = "🚗 Каталог автомобилей"
            self.bot = callback_msg.bot
            self.answer = callback_msg.answer
            self.delete = callback_msg.delete
    
    fake_message = FakeMessage(callback.message, callback.from_user)
    await handle_cars_button(fake_message)
    await safe_callback_answer(callback)

# === FSM ОБРАБОТЧИКИ (СОЗДАНИЕ АВТОМОБИЛЕЙ) ===

@dp.message(CarCreationStates.waiting_for_name)
async def process_car_name(message: Message, state: FSMContext):
    """Обработка ввода названия автомобиля"""
    await handle_car_name_input(message, state)

@dp.message(CarCreationStates.waiting_for_description)
async def process_car_description(message: Message, state: FSMContext):
    """Обработка ввода описания автомобиля"""
    await handle_car_description_input(message, state)

@dp.message(CarCreationStates.waiting_for_price)
async def process_car_price(message: Message, state: FSMContext):
    """Обработка ввода цены автомобиля"""
    await handle_car_price_input(message, state, bot)

# === FSM ОБРАБОТЧИКИ (РЕДАКТИРОВАНИЕ АВТОМОБИЛЕЙ) ===

@dp.message(CarEditStates.waiting_for_new_name)
async def process_new_car_name(message: Message, state: FSMContext):
    """Обработка ввода нового названия автомобиля"""
    await handle_new_car_name_input(message, state)

@dp.message(CarEditStates.waiting_for_new_description)
async def process_new_car_description(message: Message, state: FSMContext):
    """Обработка ввода нового описания автомобиля"""
    await handle_new_car_desc_input(message, state)

@dp.message(CarEditStates.waiting_for_new_price)
async def process_new_car_price(message: Message, state: FSMContext):
    """Обработка ввода новой цены автомобиля"""
    await handle_new_car_price_input(message, state)

# === FSM ОБРАБОТЧИКИ (ЗАГРУЗКА ИЗОБРАЖЕНИЙ) ===

@dp.message(CarImageStates.waiting_for_image_1)
async def process_car_image_1(message: Message, state: FSMContext):
    """Обработка загрузки первого изображения автомобиля"""
    await handle_car_image_1_input(message, state, bot)

@dp.message(CarImageStates.waiting_for_image_2)
async def process_car_image_2(message: Message, state: FSMContext):
    """Обработка загрузки второго изображения автомобиля"""
    await handle_car_image_2_input(message, state, bot)

@dp.message(CarImageStates.waiting_for_image_3)
async def process_car_image_3(message: Message, state: FSMContext):
    """Обработка загрузки третьего изображения автомобиля"""
    await handle_car_image_3_input(message, state, bot)

# === FSM ОБРАБОТЧИКИ (УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ) ===

@dp.message(AdminManagementStates.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    """Обработка ввода Telegram ID администратора"""
    await handle_admin_id_input(message, state)

# === ОБРАБОТЧИКИ РАССЫЛКИ ===

@dp.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Главное меню рассылки"""
    await handle_admin_broadcast_callback(callback, state)

@dp.callback_query(F.data == "broadcast_text")
async def callback_broadcast_text(callback: CallbackQuery, state: FSMContext):
    """Создание текстовой рассылки"""
    await handle_broadcast_text_callback(callback, state)

@dp.callback_query(F.data == "broadcast_photo")
async def callback_broadcast_photo(callback: CallbackQuery, state: FSMContext):
    """Создание рассылки с фото"""
    await handle_broadcast_photo_callback(callback, state)

@dp.callback_query(F.data == "broadcast_video")
async def callback_broadcast_video(callback: CallbackQuery, state: FSMContext):
    """Создание рассылки с видео"""
    await handle_broadcast_video_callback(callback, state)

@dp.callback_query(F.data == "broadcast_document")
async def callback_broadcast_document(callback: CallbackQuery, state: FSMContext):
    """Создание рассылки с документом"""
    await handle_broadcast_document_callback(callback, state)

@dp.callback_query(F.data == "broadcast_preview")
async def callback_broadcast_preview(callback: CallbackQuery, state: FSMContext):
    """Предварительный просмотр рассылки"""
    await handle_broadcast_preview_callback(callback, state, bot)

@dp.callback_query(F.data == "broadcast_send_all")
async def callback_broadcast_send_all(callback: CallbackQuery, state: FSMContext):
    """Подтверждение массовой рассылки"""
    await handle_broadcast_send_all_callback(callback, state)

@dp.callback_query(F.data == "broadcast_confirm_send")
async def callback_broadcast_confirm_send(callback: CallbackQuery, state: FSMContext):
    """Отправка рассылки всем"""
    await handle_broadcast_confirm_send_callback(callback, state, bot)

@dp.callback_query(F.data == "broadcast_history")
async def callback_broadcast_history(callback: CallbackQuery):
    """История рассылок"""
    await handle_broadcast_history_callback(callback)

@dp.callback_query(F.data == "broadcast_reset")
async def callback_broadcast_reset(callback: CallbackQuery, state: FSMContext):
    """Сброс рассылки"""
    await handle_broadcast_reset_callback(callback, state)

@dp.callback_query(F.data == "broadcast_main")
async def callback_broadcast_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню рассылки"""
    await handle_broadcast_cancel_callback(callback, state)

# === FSM ОБРАБОТЧИКИ (РАССЫЛКА) ===

@dp.message(BroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    """Обработка ввода текста для рассылки"""
    await handle_broadcast_text_input(message, state, bot)

@dp.message(BroadcastStates.waiting_for_media)
async def process_broadcast_media(message: Message, state: FSMContext):
    """Обработка ввода медиа для рассылки"""
    await handle_broadcast_media_input(message, state, bot)

# === FSM ОБРАБОТЧИКИ (АРЕНДА) ===

@dp.message(RentalManagementStates.waiting_for_user_input)
async def process_rental_user_input(message: Message, state: FSMContext):
    """Обработка ввода пользователя для аренды"""
    await handle_admin_rental_user_input(message, state)

@dp.callback_query(F.data.startswith("rental_car_select:"))
async def callback_rental_car_select(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора автомобиля при создании аренды"""
    await handle_admin_select_car_for_rental_callback(callback, state)

@dp.callback_query(F.data.startswith("rental_cars_page:"))
async def callback_rental_cars_page(callback: CallbackQuery, state: FSMContext):
    """Пагинация при выборе автомобиля для аренды"""
    await handle_admin_rental_cars_page_callback(callback, state)

@dp.callback_query(F.data.startswith("rental_reminder_type:"))
async def callback_rental_reminder_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа напоминания при создании аренды"""
    await handle_admin_rental_reminder_type_callback(callback, state)

@dp.message(RentalManagementStates.waiting_for_reminder_time)
async def process_rental_reminder_time(message: Message, state: FSMContext):
    """Обработка ввода времени напоминания"""
    # Проверяем, обновляем ли мы существующую аренду или создаем новую
    data = await state.get_data()
    if data.get('rental_id'):
        await handle_admin_rental_reminder_time_update(message, state)
    else:
        await handle_admin_rental_reminder_time_input(message, state)

@dp.message(RentalManagementStates.waiting_for_deposit_amount)
async def process_rental_deposit_amount(message: Message, state: FSMContext):
    """Обработка ввода суммы залога"""
    from bot.handlers.admin.rentals import handle_admin_rental_deposit_amount_input
    await handle_admin_rental_deposit_amount_input(message, state)

@dp.message(RentalManagementStates.waiting_for_end_date)
async def process_rental_end_date(message: Message, state: FSMContext):
    """Обработка ввода даты окончания аренды"""
    await handle_admin_rental_end_date_update(message, state)

@dp.callback_query(F.data.startswith("deposit_"))
async def callback_deposit_status_change(callback: CallbackQuery):
    """Изменение статуса залога"""
    from bot.handlers.admin.rentals import handle_deposit_status_change_callback
    await handle_deposit_status_change_callback(callback)

# === FSM ОБРАБОТЧИКИ (УПРАВЛЕНИЕ КОНТАКТАМИ) ===

@dp.message(ContactManagementStates.waiting_for_name)
async def process_contact_name(message: Message, state: FSMContext):
    """Обработка ввода имени контакта"""
    await handle_contact_name_input(message, state)

@dp.message(ContactManagementStates.waiting_for_phone)
async def process_contact_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона контакта"""
    await handle_contact_phone_input(message, state)

@dp.message(ContactManagementStates.waiting_for_telegram)
async def process_contact_telegram(message: Message, state: FSMContext):
    """Обработка ввода Telegram контакта"""
    await handle_contact_telegram_input(message, state)

# === ОБРАБОТЧИКИ ЗАМЕТОК О ПОЛЬЗОВАТЕЛЯХ (МОДУЛЬ 2) ===

@dp.callback_query(F.data.startswith("user_notes:"))
async def callback_user_notes(callback: CallbackQuery):
    """Показ заметок о пользователе"""
    await handle_user_notes_callback(callback)

@dp.callback_query(F.data.startswith("user_note_add:"))
async def callback_user_note_add(callback: CallbackQuery, state: FSMContext):
    """Добавление заметки о пользователе"""
    await handle_user_note_add_callback(callback, state)

@dp.callback_query(F.data.startswith("user_note_delete:"))
async def callback_user_note_delete(callback: CallbackQuery):
    """Удаление заметки о пользователе"""
    await handle_user_note_delete_callback(callback)

@dp.message(UserNotesStates.waiting_for_note_text)
async def process_user_note_text(message: Message, state: FSMContext):
    """Обработка ввода текста заметки"""
    await handle_user_note_text_input(message, state)

# === ОБРАБОТЧИКИ ИНЦИДЕНТОВ (МОДУЛЬ 3) ===

@dp.callback_query(F.data.startswith("rental_incidents:"))
async def callback_rental_incidents(callback: CallbackQuery):
    """Показ инцидентов аренды"""
    await handle_rental_incidents_callback(callback)

@dp.callback_query(F.data.startswith("incident_add:"))
async def callback_incident_add(callback: CallbackQuery, state: FSMContext):
    """Добавление инцидента"""
    await handle_incident_add_callback(callback, state)

@dp.callback_query(F.data.startswith("incident_type:"))
async def callback_incident_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа инцидента"""
    await handle_incident_type_callback(callback, state)

@dp.callback_query(F.data.startswith("incident_photo_"))
async def callback_incident_photo_decision(callback: CallbackQuery, state: FSMContext):
    """Решение о фото инцидента"""
    await handle_incident_photo_decision_callback(callback, state)

@dp.callback_query(F.data.startswith("incident_delete:"))
async def callback_incident_delete(callback: CallbackQuery):
    """Удаление инцидента"""
    await handle_incident_delete_callback(callback)

@dp.message(IncidentManagementStates.waiting_for_incident_description)
async def process_incident_description(message: Message, state: FSMContext):
    """Обработка ввода описания инцидента"""
    await handle_incident_description_input(message, state)

@dp.message(IncidentManagementStates.waiting_for_incident_amount)
async def process_incident_amount(message: Message, state: FSMContext):
    """Обработка ввода суммы инцидента"""
    await handle_incident_amount_input(message, state)

@dp.message(IncidentManagementStates.waiting_for_incident_photo)
async def process_incident_photo(message: Message, state: FSMContext):
    """Обработка загрузки фото инцидента"""
    await handle_incident_photo_input(message, state)

# === ОБРАБОТЧИКИ ЖУРНАЛА ОБСЛУЖИВАНИЯ (МОДУЛЬ 5) ===

@dp.callback_query(F.data.startswith("car_maintenance:"))
async def callback_car_maintenance(callback: CallbackQuery):
    """Показ журнала обслуживания автомобиля"""
    await handle_car_maintenance_callback(callback)

@dp.callback_query(F.data.startswith("maintenance_add:"))
async def callback_maintenance_add(callback: CallbackQuery, state: FSMContext):
    """Добавление записи обслуживания"""
    await handle_maintenance_add_callback(callback, state)

@dp.callback_query(F.data.startswith("maintenance_type:"))
async def callback_maintenance_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа записи обслуживания"""
    await handle_maintenance_type_callback(callback, state)

@dp.callback_query(F.data.startswith("maintenance_reminder_"))
async def callback_maintenance_reminder_decision(callback: CallbackQuery, state: FSMContext):
    """Решение о напоминании обслуживания"""
    await handle_maintenance_reminder_decision_callback(callback, state)

@dp.callback_query(F.data.startswith("maintenance_remove_reminder:"))
async def callback_maintenance_remove_reminder(callback: CallbackQuery):
    """Удаление напоминания обслуживания"""
    await handle_maintenance_remove_reminder_callback(callback)

@dp.message(MaintenanceStates.waiting_for_description)
async def process_maintenance_description(message: Message, state: FSMContext):
    """Обработка ввода описания обслуживания"""
    await handle_maintenance_description_input(message, state)

@dp.message(MaintenanceStates.waiting_for_mileage)
async def process_maintenance_mileage(message: Message, state: FSMContext):
    """Обработка ввода пробега"""
    await handle_maintenance_mileage_input(message, state)

@dp.message(MaintenanceStates.waiting_for_event_date)
async def process_maintenance_event_date(message: Message, state: FSMContext):
    """Обработка ввода даты события"""
    await handle_maintenance_event_date_input(message, state)

@dp.message(MaintenanceStates.waiting_for_reminder_date)
async def process_maintenance_reminder_date(message: Message, state: FSMContext):
    """Обработка ввода даты напоминания"""
    await handle_maintenance_reminder_date_input(message, state)

# === ОБРАБОТЧИКИ РЕФЕРАЛЬНОЙ СИСТЕМЫ (МОДУЛЬ 6) ===

@dp.callback_query(F.data == "admin_referral_system")
async def callback_admin_referral_system(callback: CallbackQuery):
    """Управление реферальной системой"""
    await handle_referral_system_callback(callback)

@dp.callback_query(F.data == "referral_toggle")
async def callback_referral_toggle(callback: CallbackQuery):
    """Переключение реферальной системы"""
    await handle_referral_toggle_callback(callback)

@dp.callback_query(F.data == "referral_edit_percentage")
async def callback_referral_edit_percentage(callback: CallbackQuery, state: FSMContext):
    """Редактирование процента скидки"""
    await handle_referral_edit_percentage_callback(callback, state)

@dp.callback_query(F.data == "referral_edit_duration")
async def callback_referral_edit_duration(callback: CallbackQuery, state: FSMContext):
    """Редактирование срока действия"""
    await handle_referral_edit_duration_callback(callback, state)

@dp.message(ReferralManagementStates.waiting_for_percentage)
async def process_referral_percentage(message: Message, state: FSMContext):
    """Обработка ввода процента скидки"""
    await handle_referral_percentage_input(message, state)

@dp.message(ReferralManagementStates.waiting_for_duration)
async def process_referral_duration(message: Message, state: FSMContext):
    """Обработка ввода срока действия"""
    await handle_referral_duration_input(message, state)

# === ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ ===

@dp.message(F.text.in_(["🚗 Каталог автомобилей", "Каталог автомобилей"]))
async def message_cars(message: Message):
    """Обработчик кнопки '🚗 Каталог автомобилей'"""
    await handle_cars_button(message)

@dp.message(F.text.in_(["👤 Мой профиль", "Мой профиль"]))
async def message_profile(message: Message):
    """Обработчик кнопки '👤 Мой профиль'"""
    from bot.handlers.user_handlers import handle_user_profile
    await handle_user_profile(message)

@dp.message(F.text.in_(["📞 Контакты", "Контакты"]))
async def message_contacts(message: Message):
    """Обработчик кнопки '📞 Контакты'"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from bot.database.database import get_contact
    
    # Получаем контакты из БД
    contact = await get_contact('booking')
    
    if contact:
        contact_name = contact.get('name', 'Денис')
        contact_phone = contact.get('phone', '+7 919 634-90-91')
        contact_telegram = contact.get('telegram_username', 'olimp_auto')
    else:
        contact_name = 'Денис'
        contact_phone = '+7 919 634-90-91'
        contact_telegram = 'olimp_auto'
    
    contact_text = f"""📞 <b>КОНТАКТЫ</b>

🚗 <b>OLIMP AUTO</b>

👤 <b>Менеджер:</b> {contact_name}

📱 <b>Телефон:</b>
<code>{contact_phone}</code>

💬 <b>Telegram:</b>
@{contact_telegram}

📍 <b>Адрес:</b>
г. Казань, ул. Абсалямова, д. 36

🕐 <b>Режим работы:</b>
Пн-Пт: 09:00 - 21:00
Сб-Вс: 10:00 - 19:00

💡 <i>Свяжитесь с нами для консультации или бронирования</i>"""
    
    # Telegram не поддерживает tel: протокол для inline кнопок
    # Используем только Telegram ссылку и callback для показа номера
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Telegram", url=f"https://t.me/{contact_telegram.lstrip('@')}")],
        [InlineKeyboardButton(text="📱 Показать номер", callback_data="show_phone_number")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await message.answer(contact_text, reply_markup=keyboard, parse_mode='HTML')

@dp.message(F.text.in_(["ℹ️ Помощь", "Помощь"]))
async def message_help(message: Message):
    """Обработчик кнопки 'ℹ️ Помощь'"""
    await cmd_help(message)

@dp.message(F.text.in_(["🔧 Админ панель", "Админ панель"]))
async def message_admin_panel(message: Message):
    """Обработчик кнопки '🔧 Админ панель'"""
    await handle_admin_panel_button(message)

@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    # Удаляем предыдущее сообщение для чистоты чата
    try:
        await callback.message.delete()
    except (TelegramBadRequest, TelegramAPIError):
        pass
    
    user_name = callback.from_user.first_name if callback.from_user else "пользователь"
    if not user_name:
        user_name = "пользователь"
    
    user_is_admin = False
    if callback.from_user:
        user_is_admin = await is_admin(callback.from_user.id)
    
    if user_is_admin:
        welcome_text = f"""<b>Добро пожаловать, {user_name}</b>

<b>🔧 Панель администратора</b>"""
        reply_markup = get_admin_main_menu()
    else:
        welcome_text = f"""👋 <b>Добро пожаловать, {user_name}!</b>

🚗 <b>OLIMP AUTO</b>
Аренда автомобилей с правом выкупа

👇 Используйте кнопки меню для навигации."""
        reply_markup = get_main_menu()
    
    await callback.message.answer(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    await safe_callback_answer(callback)

# === УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (должен быть последним) ===

@dp.message(F.text)
async def handle_text_messages(message: Message, state: FSMContext):
    """Обработчик остальных текстовых сообщений (не команды и не в FSM состоянии)"""
    # Пропускаем команды - они обрабатываются выше через фильтр Command
    if message.text and message.text.startswith("/"):
        return
    
    # Проверяем, не находимся ли мы в FSM состоянии
    current_state = await state.get_state()
    if current_state is not None:
        # Если есть активное состояние, не обрабатываем здесь - пусть FSM обработчики работают
        return
    
    await message.answer(
        """<b>Команда не распознана</b>

Используйте кнопки меню для навигации.

Доступные действия:
• Каталог автомобилей
• Контакты
• Помощь

Отправьте /help для справки.""",
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )

async def initialize_first_admin():
    """Инициализация первого администратора"""
    # Проверяем, есть ли уже админы в системе
    existing_admins = await get_all_admins()
    if existing_admins:
        print(f"✅ В системе уже есть {len(existing_admins)} администратор(ов)")
        return
    
    # Читаем ID первого админа из переменной окружения
    first_admin_id = os.getenv('FIRST_ADMIN_ID')
    
    if not first_admin_id:
        print("⚠️  FIRST_ADMIN_ID не установлен!")
        print("Для создания первого админа установите переменную:")
        print("export FIRST_ADMIN_ID='ваш_telegram_id'")
        print("Получить свой ID можно через @userinfobot")
        return
    
    try:
        admin_id = int(first_admin_id)
    except ValueError:
        print("❌ FIRST_ADMIN_ID должен быть числом")
        return
    
    # Добавляем первого админа
    success = await add_admin(admin_id)
    if success:
        print("✅ Первый администратор успешно добавлен")
        print("🔧 Админ панель будет доступна для этого пользователя")
    else:
        print("❌ Ошибка при добавлении администратора")
    
async def load_booking_contact_from_db():
    """Загружает контакт для бронирования из базы данных, если не установлен через переменную окружения"""
    from bot.config import BOOKING_CONTACT_ID
    
    # Если уже установлен через переменную окружения, не перезаписываем
    if BOOKING_CONTACT_ID is not None:
        return
    
    try:
        contact = await get_contact('booking')
        if contact and contact.get('telegram_id'):
            # Обновляем BOOKING_CONTACT_ID в модуле config
            import bot.config
            bot.config.BOOKING_CONTACT_ID = int(contact['telegram_id'])
            print(f"✅ ID контакта для бронирования загружен из базы данных: {contact['telegram_id']}")
        else:
            print("ℹ️  Контакт для бронирования не настроен в базе данных")
            print("💡 Вы можете настроить его через админ-панель → Контакты")
    except Exception as e:
        print(f"⚠️  Ошибка при загрузке контакта из базы данных: {e}")

async def main():
    """Главная функция запуска бота"""
    try:
        # Инициализация базы данных
        await init_db()
        
        # Загрузка контакта для бронирования из базы данных (если не установлен через переменную окружения)
        await load_booking_contact_from_db()
        
        # Добавление тестовых автомобилей при первом запуске
        await add_sample_cars()
        
        # Инициализация первого администратора
        await initialize_first_admin()
        
        # Запуск планировщика напоминаний
        from bot.utils.scheduler import init_scheduler
        await init_scheduler(bot)
        
        # Запуск бота
        print("Бот запущен...")
        print("📱 Доступные функции:")
        print("  🚗 Каталог автомобилей")
        print("  💰 Просмотр цен и описаний") 
        print("  📝 Бронирование (в разработке)")
        print("  🔧 Админ панель (для администраторов)")
        print("=" * 50)
        await dp.start_polling(bot)
        
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        # Останавливаем планировщик
        from bot.utils.scheduler import stop_scheduler
        await stop_scheduler()
        
        # Закрываем пул соединений с БД
        await db_pool.close()
        await bot.session.close()
        print("✅ Бот остановлен, соединения закрыты")

if __name__ == "__main__":
    asyncio.run(main())