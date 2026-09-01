# src/endpoints/client/reviews.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.kit.database.service import database_service
from src.auth.dependencies import WebUser
from src.models import Review, Ad, AdStatus, User
from src.schemas.reviews import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewOut)
async def create_review(
    data: ReviewCreate,
    user: WebUser,
):
    """
    Оставить отзыв о продавце после просмотра объявления.
    """
    async with database_service.get_session() as session:
        # Загружаем объявление с продавцом
        stmt = (
            select(Ad)
            .where(Ad.id == data.ad_id)
            .options(joinedload(Ad.seller))
        )
        result = await session.execute(stmt)
        ad = result.scalars().first()

        if not ad:
            raise HTTPException(404, "Объявление не найдено")

        if ad.seller_user_id == user.id:
            raise HTTPException(400, "Нельзя оставить отзыв на самого себя")

        if data.rating < 1 or data.rating > 5:
            raise HTTPException(400, "Оценка должна быть от 1 до 5")

        # Проверяем, не оставлял ли уже отзыв на это объявление
        existing = await session.execute(
            select(Review).where(
                Review.ad_id == data.ad_id,
                Review.reviewer_user_id == user.id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(400, "Вы уже оставили отзыв на это объявление")

        review = Review(
            reviewed_user_id=ad.seller_user_id,
            reviewer_user_id=user.id,
            ad_id=data.ad_id,
            rating=data.rating,
            comment=data.comment,
        )
        session.add(review)
        await session.commit()
        await session.refresh(review)

        # Загружаем ревьюера для полного ответа
        await session.execute(
            select(Review).where(Review.id == review.id).options(
                joinedload(Review.reviewer),
            )
        )

        return ReviewOut(
            id=review.id,
            reviewer_username=user.username,
            reviewer_user_id=user.id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
        )
