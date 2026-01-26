"""
Pydantic модели для пользователей
"""
from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Модель для создания пользователя"""
    telegram_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    username: Optional[str] = Field(None, max_length=100, description="Username пользователя")
    first_name: Optional[str] = Field(None, max_length=200, description="Имя пользователя")


class UserResponse(BaseModel):
    """Модель ответа с информацией о пользователе"""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True






