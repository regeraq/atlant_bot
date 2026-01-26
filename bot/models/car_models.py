"""
Pydantic модели для автомобилей
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CarCreate(BaseModel):
    """Модель для создания автомобиля"""
    name: str = Field(..., min_length=3, max_length=200, description="Название автомобиля")
    description: Optional[str] = Field(None, min_length=10, max_length=2000, description="Описание автомобиля")
    daily_price: int = Field(..., gt=0, le=1000000, description="Цена за день в рублях")
    available: bool = Field(default=True, description="Доступен ли автомобиль")
    image_1: Optional[str] = Field(None, description="File ID первого изображения")
    image_2: Optional[str] = Field(None, description="File ID второго изображения")
    image_3: Optional[str] = Field(None, description="File ID третьего изображения")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация названия"""
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Название должно содержать минимум 3 символа")
        return v
    
    @field_validator('daily_price')
    @classmethod
    def validate_price(cls, v: int) -> int:
        """Валидация цены"""
        if v <= 0:
            raise ValueError("Цена должна быть положительной")
        if v > 1000000:
            raise ValueError("Цена слишком большая (максимум 1000000)")
        return v


class CarUpdate(BaseModel):
    """Модель для обновления автомобиля"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    daily_price: Optional[int] = Field(None, gt=0, le=1000000)
    available: Optional[bool] = None
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Валидация названия"""
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError("Название должно содержать минимум 3 символа")
        return v
    
    @field_validator('daily_price')
    @classmethod
    def validate_price(cls, v: Optional[int]) -> Optional[int]:
        """Валидация цены"""
        if v is not None:
            if v <= 0:
                raise ValueError("Цена должна быть положительной")
            if v > 1000000:
                raise ValueError("Цена слишком большая (максимум 1000000)")
        return v


class CarResponse(BaseModel):
    """Модель ответа с информацией об автомобиле"""
    id: int
    name: str
    description: Optional[str]
    daily_price: int
    available: bool
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True






