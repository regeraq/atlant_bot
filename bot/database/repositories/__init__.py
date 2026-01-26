"""
Repository Pattern для работы с БД
"""
from .car_repository import CarRepository
from .user_repository import UserRepository
from .rental_repository import RentalRepository

__all__ = [
    'CarRepository',
    'UserRepository',
    'RentalRepository',
]
