from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import Ad, AdPhoto, AdStatus, User
from src.kit.pagination import PaginationParams


class AdRepository(BaseRepository[Ad], IDRepositoryMixin[Ad, int]):
    model = Ad

    def get_base_stmt(self):
        """Get base statement with relationships loaded"""
        return (
            select(Ad)
            .options(
                selectinload(Ad.photos),
                selectinload(Ad.seller)
            )
        )

    async def get_user_ads(
        self,
        user_id: int,
        status: Optional[AdStatus] = None,
        limit: int = 20,
        page: int = 1,
    ) -> Tuple[List[Ad], int]:
        """Get ads for specific user with optional status filter"""
        stmt = self.get_base_stmt().where(Ad.seller_user_id == user_id)
        
        filters = []
        if status:
            filters.append(Ad.status == status.value)
        
        return await self.paginate(stmt, limit, page, filters)

    async def get_pending_ads(
        self,
        limit: int = 20,
        page: int = 1,
    ) -> Tuple[List[Ad], int]:
        """Get all pending ads for moderation"""
        stmt = self.get_base_stmt().where(Ad.status == AdStatus.pending.value)
        return await self.paginate(stmt, limit, page, [])

    async def get_ad_with_photos(self, ad_id: int) -> Optional[Ad]:
        """Get ad with photos and seller"""
        stmt = (
            self.get_base_stmt()
            .where(Ad.id == ad_id)
            .options(
                selectinload(Ad.seller).selectinload(User.credentials),
                selectinload(Ad.photos),
            )
        )
        return await self.get_one_or_none(stmt)

    async def update_status(
        self,
        ad_id: int,
        status: AdStatus,
        rejection_reason: Optional[str] = None,
        channel_message_id: Optional[int] = None,
    ) -> Optional[Ad]:
        """Update ad status"""
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Ad)
            .where(Ad.id == ad_id)
            .options(
                selectinload(Ad.seller).selectinload(User.credentials),
            )
        )
        result = await self.session.execute(stmt)
        ad = result.unique().scalar_one_or_none()
        if not ad:
            return None
        
        ad.status = status.value
        if rejection_reason:
            ad.rejection_reason = rejection_reason
        if channel_message_id:
            ad.channel_message_id = channel_message_id
        
        await self.session.flush()
        return ad