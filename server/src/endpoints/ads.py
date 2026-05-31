# src/api/endpoints/ads.py
from fastapi import APIRouter, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload, selectinload
from src.models import Ad, AdStatus, Review, User
from src.kit.database.service import database_service
from src.schemas.ads import AdOut
from typing import Optional

router = APIRouter(prefix="/ads", tags=["ads"])

@router.get("")
async def list_ads(
    category: list[str] | None = Query(None),
    subcategory: list[str] | None = Query(None),
    country: list[str] | None = Query(None),
    city: list[str] | None = Query(None),
    condition: Optional[str] = Query(None),
    ad_type: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query('created_at_desc'),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    async with database_service.get_session() as db:
        stmt = select(Ad).where(Ad.status == AdStatus.approved)
        
        stmt = stmt.options(
            selectinload(Ad.photos),
            joinedload(Ad.seller).selectinload(User.reviews_received).options(
                joinedload(Review.reviewer)
            )
        )
        
        # Filters (multiple values = OR within group, AND across groups)
        category_filters: list = []
        if category:
            category_filters.append(Ad.category.in_(category))
        if subcategory:
            category_filters.append(Ad.subcategory.in_(subcategory))
        if category_filters:
            stmt = stmt.where(or_(*category_filters))

        # City is matched exactly as stored in DB. When cities are chosen, they
        # take precedence — many legacy ads have city set but country empty.
        if city:
            stmt = stmt.where(Ad.city.in_(city))
        elif country:
            stmt = stmt.where(Ad.country.in_(country))
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
        
        # Sorting
        if sort == 'price_asc':
            stmt = stmt.order_by(Ad.price.asc())
        elif sort == 'price_desc':
            stmt = stmt.order_by(Ad.price.desc())
        elif sort == 'created_at_asc':
            stmt = stmt.order_by(Ad.created_at.asc())
        else:  # created_at_desc (default)
            stmt = stmt.order_by(Ad.created_at.desc())
        
        # Pagination
        total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        
        result = await db.execute(stmt)
        ads = result.scalars().unique().all()

        
        return {
            "data": [AdOut.from_orm_with_photos(ad) for ad in ads],
            "total": total,
            "page": page,
            "limit": limit,
        }