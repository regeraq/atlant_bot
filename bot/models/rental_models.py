"""
Pydantic модели для аренд
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re


class RentalCreate(BaseModel):
    """Модель для создания аренды"""
    user_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    car_id: int = Field(..., gt=0, description="ID автомобиля")
    daily_price: int = Field(..., gt=0, le=1000000, description="Цена за день")
    reminder_time: str = Field(..., description="Время напоминания в формате ЧЧ:ММ")
    reminder_type: Literal['daily', 'weekly', 'monthly'] = Field(
        default='daily',
        description="Тип напоминания"
    )
    
    @field_validator('reminder_time')
    @classmethod
    def validate_reminder_time(cls, v: str) -> str:
        """Валидация времени напоминания"""
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
        if not re.match(time_pattern, v):
            raise ValueError("Время должно быть в формате ЧЧ:ММ (например, 12:00)")
        return v.strip()
    
    @field_validator('reminder_type')
    @classmethod
    def validate_reminder_type(cls, v: str) -> str:
        """Валидация типа напоминания"""
        if v not in ['daily', 'weekly', 'monthly']:
            raise ValueError("Тип напоминания должен быть: daily, weekly или monthly")
        return v


class RentalUpdate(BaseModel):
    """Модель для обновления аренды"""
    reminder_time: Optional[str] = None
    reminder_type: Optional[Literal['daily', 'weekly', 'monthly']] = None
    
    @field_validator('reminder_time')
    @classmethod
    def validate_reminder_time(cls, v: Optional[str]) -> Optional[str]:
        """Валидация времени напоминания"""
        if v is not None:
            time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
            if not re.match(time_pattern, v):
                raise ValueError("Время должно быть в формате ЧЧ:ММ (например, 12:00)")
            return v.strip()
        return v


class RentalResponse(BaseModel):
    """Модель ответа с информацией об аренде"""
    id: int
    user_id: int
    car_id: int
    car_name: Optional[str] = None
    daily_price: int
    reminder_time: str
    reminder_type: str
    start_date: Optional[str] = None
    last_reminder_date: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True






