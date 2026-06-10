# src/endpoints/admin/moderators.py
from fastapi import APIRouter, Depends, Path, HTTPException, Query
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload

from src.kit.database.service import database_service
from src.auth.dependencies import WebModerator
from src.models import Ad, AdStatus, User, Review
from src.schemas.ads import MyAdOut, AdModerate, AdminAdDetail
from src.services import ad_service
from src.repositories.ads import AdRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ads/pending", response_model=dict)
async def get_pending_ads(
    admin: WebModerator,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all pending ads for moderation (admin only)"""
    async with database_service.get_session() as session:
        repository = AdRepository(session)
        ads, total = await repository.get_pending_ads(limit=limit, page=page)
        
        return {
            "data": [MyAdOut.from_orm_with_status(ad) for ad in ads],
            "total": total,
            "page": page,
            "limit": limit,
        }


@router.post("/ads/{ad_id}/moderate", response_model=MyAdOut)
async def moderate_ad(
    ad_id: int,
    data: AdModerate,
    admin: WebModerator,
):
    """
    Moderate ad (approve or reject) - admin only
    """
    async with database_service.get_session() as session:
        ad = await ad_service.moderate_ad(
            session=session,
            ad_id=ad_id,
            action=data.action,
            rejection_reason=data.rejection_reason,
        )
        
        if not ad:
            raise HTTPException(404, "Ad not found")
        
        # TODO: Если одобрено - отправить в Telegram канал
        # if data.action == "approve":
        #     from src.bot.services import send_ad_to_channel_api
        #     channel_message_id = await send_ad_to_channel_api(ad)
        #     ad.channel_message_id = channel_message_id
        #     await session.flush()
        
        await session.commit()
        
        return MyAdOut.from_orm_with_status(ad)


@router.get("/stats", response_model=dict)
async def get_admin_stats(admin: WebModerator):
    """Get admin statistics"""
    async with database_service.get_session() as session:
        # Count ads by status
        stmt = select(Ad.status, func.count(Ad.id)).group_by(Ad.status)
        result = await session.execute(stmt)
        ads_by_status = {status: count for status, count in result.all()}

        
        # Count users
        users_count = await session.scalar(select(func.count(User.id)))
        
        # Count pending ads
        pending_count = ads_by_status.get(AdStatus.pending.value, 0)
        approved_count = ads_by_status.get(AdStatus.approved.value, 0)
        rejected_count = ads_by_status.get(AdStatus.rejected.value, 0)
        
        return {
            "total_users": users_count,
            "total_ads": sum(ads_by_status.values()),
            "pending_ads": pending_count,
            "approved_ads": approved_count,
            "rejected_ads": rejected_count,
            "ads_by_status": ads_by_status,
        }


@router.get("/ads/all", response_model=dict)
async def get_all_ads(
    admin: WebModerator,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all ads with filters (admin only)"""
    async with database_service.get_session() as session:
        stmt = select(Ad).options(
            selectinload(Ad.photos),
            selectinload(Ad.seller)
        )
        
        filters = []
        if status:
            filters.append(Ad.status == status)
        
        if filters:
            stmt = stmt.where(*filters)
        
        stmt = stmt.order_by(Ad.created_at.desc())
        
        # Pagination
        from sqlalchemy import select as select_count
        total = await session.scalar(
            select_count(func.count()).select_from(Ad).where(*filters) if filters else select(func.count()).select_from(Ad)
        )
        
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        ads = result.scalars().unique().all()
        
        return {
            "data": [MyAdOut.from_orm_with_status(ad) for ad in ads],
            "total": total,
            "page": page,
            "limit": limit,
        }
    


@router.get("/ads/{ad_id}", response_model=AdminAdDetail)
async def get_ad_detail(
    admin: WebModerator,  # Сначала аргумент БЕЗ знака "="
    ad_id: int = Path(..., ge=1, description="ID объявления"), # Затем аргумент СО знаком "="
):

    """
    Получить полную информацию об объявлении для модерации
    Включает все фотографии, данные продавца, теги
    """
    async with database_service.get_session() as session:
        stmt = (
            select(Ad)
            .where(Ad.id == ad_id)
            .options(
                selectinload(Ad.photos),
                selectinload(Ad.tags),
                # ИСПРАВЛЕНО: загружаем продавца + его отзывы + авторов отзывов
                joinedload(Ad.seller)
                    .selectinload(User.reviews_received)
                    .selectinload(Review.reviewer)
            )
        )
        
        result = await session.execute(stmt)
        ad = result.scalars().unique().first()
        
        if not ad:
            raise HTTPException(404, "Объявление не найдено")
        
        return AdminAdDetail.from_orm_full(ad)