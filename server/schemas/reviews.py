# src/schemas/reviews.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    ad_id: int = Field(..., ge=1, description="ID объявления")
    rating: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    comment: Optional[str] = Field(None, max_length=500, description="Текст отзыва")


class ReviewOut(BaseModel):
    id: int
    reviewer_username: Optional[str] = None
    reviewer_user_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
