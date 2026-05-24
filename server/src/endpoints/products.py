# src/api/endpoints/products.py
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.models.ad import Ad, AdStatus
from src.schemas.ads import AdOut
from src.kit.database.service import database_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}", response_model=AdOut)
async def get_product(
    product_id: int = Path(..., ge=1, description="ID товара")
):
    """
    Получить детальную информацию о товаре по ID
    """
    async with database_service.get_session() as db:
        stmt = (
            select(Ad)
            .where(Ad.id == product_id, Ad.status == AdStatus.approved)
            .options(joinedload(Ad.photos))
        )
        
        result = await db.execute(stmt)
        ad = result.scalars().unique().first()
        
        if not ad:
            raise HTTPException(
                status_code=404,
                detail=f"Товар с ID {product_id} не найден или не одобрен"
            )
        
        return AdOut.from_orm_with_photos(ad)