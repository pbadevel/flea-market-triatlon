# src/schemas/profile.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserProfileOut(BaseModel):
    """Публичная информация о пользователе"""
    id: int
    tg_user_id: int
    username: Optional[str] = None  # Telegram username
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None  # Email из credentials
    is_email_verified: bool = False
    is_moderator: bool = False
    is_trusted_seller: bool = False
    agreed_to_terms: bool = False
    subscribed_to_channel: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Данные для обновления профиля"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)


class UserStats(BaseModel):
    """Статистика пользователя"""
    total_ads: int = 0
    active_ads: int = 0
    pending_ads: int = 0
    approved_ads: int = 0
    rejected_ads: int = 0
    sold_ads: int = 0