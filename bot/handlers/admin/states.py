"""
FSM States для admin handlers
"""
from aiogram.fsm.state import State, StatesGroup


class CarCreationStates(StatesGroup):
    """Состояния для создания автомобиля"""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_images = State()
    waiting_for_broadcast_decision = State()


class CarEditStates(StatesGroup):
    """Состояния для редактирования автомобиля"""
    waiting_for_new_name = State()
    waiting_for_new_description = State()
    waiting_for_new_price = State()


class AdminManagementStates(StatesGroup):
    """Состояния для управления администраторами"""
    waiting_for_admin_id = State()


class CarImageStates(StatesGroup):
    """Состояния для загрузки изображений автомобиля"""
    waiting_for_image_1 = State()
    waiting_for_image_2 = State()
    waiting_for_image_3 = State()


class RentalManagementStates(StatesGroup):
    """Состояния для управления арендой"""
    waiting_for_user_input = State()
    waiting_for_car_selection = State()
    waiting_for_reminder_type = State()
    waiting_for_reminder_time = State()
    waiting_for_deposit_amount = State()  # Модуль 4
    waiting_for_end_date = State()


class ContactManagementStates(StatesGroup):
    """Состояния для управления контактами"""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_telegram = State()


class UserNotesStates(StatesGroup):
    """Состояния для работы с заметками о пользователях (Модуль 2)"""
    waiting_for_note_text = State()


class IncidentManagementStates(StatesGroup):
    """Состояния для управления инцидентами (Модуль 3)"""
    waiting_for_incident_type = State()
    waiting_for_incident_description = State()
    waiting_for_incident_amount = State()
    waiting_for_incident_photo_decision = State()
    waiting_for_incident_photo = State()


class MaintenanceStates(StatesGroup):
    """Состояния для журнала обслуживания (Модуль 5)"""
    waiting_for_entry_type = State()
    waiting_for_description = State()
    waiting_for_mileage = State()
    waiting_for_event_date = State()
    waiting_for_reminder_decision = State()
    waiting_for_reminder_date = State()


class ReferralManagementStates(StatesGroup):
    """Состояния для управления реферальной системой (Модуль 6)"""
    waiting_for_percentage = State()
    waiting_for_duration = State()





