from fastapi import APIRouter, Query
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from src.models import Ad, AdStatus, AdPhoto
from src.kit.database.service import database_service
from src.schemas.ads import AdOut
from typing import Optional

router = APIRouter(prefix="/ads", tags=["ads"])

@router.get("")
async def list_ads(
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    ad_type: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    async with database_service.get_session() as db:
        stmt = select(Ad).where(Ad.status == AdStatus.approved)
        
        stmt = stmt.options(joinedload(Ad.photos))
        
        # Фильтры
        if category:
            stmt = stmt.where(Ad.category == category)
        if subcategory:
            stmt = stmt.where(Ad.subcategory == subcategory)
        if country:
            stmt = stmt.where(Ad.country == country)
        if city:
            stmt = stmt.where(Ad.city == city)
        if condition:
            stmt = stmt.where(Ad.condition == condition)
        if ad_type:
            stmt = stmt.where(Ad.ad_type == ad_type)
        if min_price is not None:
            stmt = stmt.where(Ad.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Ad.price <= max_price)
        if search:
            stmt = stmt.where(
                Ad.title.ilike(f"%{search}%") | 
                Ad.description.ilike(f"%{search}%")
            )
        
        # Пагинация
        total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.offset((page - 1) * limit).limit(limit).order_by(Ad.created_at.desc())
        
        result = await db.execute(stmt)
        ads = result.scalars().unique().all()
        
        # ✅ Сериализуем с фото
        return {
            "data": [AdOut.from_orm_with_photos(ad) for ad in ads],
            "total": total,
            "page": page,
            "limit": limit,
        }