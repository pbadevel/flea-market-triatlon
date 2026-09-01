from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Ad, AdPhoto, AdStatus, User
from src.repositories.ads import AdRepository
from src.schemas.ads import AdCreate, AdPhotoCreate
from src.services.storage import LocalFileStorage
from src.logging import get_logger

log = get_logger()


class AdService:
    def __init__(self):
        self.storage = LocalFileStorage()

    async def create_ad(
        self,
        session: AsyncSession,
        user: User,
        data: AdCreate,
    ) -> Ad:
        """Create new ad with pending status"""
        repository = AdRepository(session)

        # Create ad
        ad = Ad(
            seller_user_id=user.id,
            title=data.title,
            price=data.price,
            city=data.city,
            country=data.country,
            category=data.category,
            subcategory=data.subcategory,
            size=data.size,
            condition=data.condition,
            description=data.description,
            ad_type=data.ad_type,
            delivery_method=data.delivery_method,
            contact_method=data.contact_method,
            status=AdStatus.pending.value,
        )
        
        ad = await repository.create(ad, flush=True)

        # Create photos
        for photo_data in data.photos:
            photo = AdPhoto(
                ad_id=ad.id,
                file_id=photo_data.file_id,
                storage_path=photo_data.storage_path,
                position=photo_data.position,
            )
            session.add(photo)

        await session.flush()
        
        # Reload with photos
        ad = await repository.get_ad_with_photos(ad.id)
        
        log.info(f"Ad created: {ad.id} by user {user.id}", extra={"ad_id": ad.id, "user_id": user.id})
        
        return ad

    async def get_ad_by_id(
        self,
        session: AsyncSession,
        id: int,
        with_photos = True
        ):
        options = []
        if with_photos:
            options.append(selectinload(Ad.photos))
        repository = AdRepository(session)
        return await repository.get_by_id(id=id, options=(*options,))
        


    async def get_user_ads(
        self,
        session: AsyncSession,
        user_id: int,
        status: Optional[AdStatus] = None,
        limit: int = 20,
        page: int = 1,
    ) -> Tuple[List[Ad], int]:
        """Get user's ads"""
        repository = AdRepository(session)
        return await repository.get_user_ads(user_id, status, limit, page)

    async def get_ad_for_moderation(
        self,
        session: AsyncSession,
        ad_id: int,
    ) -> Optional[Ad]:
        """Get ad for moderation"""
        repository = AdRepository(session)
        return await repository.get_ad_with_photos(ad_id)

    async def moderate_ad(
        self,
        session: AsyncSession,
        ad_id: int,
        action: str,
        rejection_reason: Optional[str] = None,
        channel_message_id: Optional[int] = None,
    ) -> Optional[Ad]:
        """Moderate ad (approve or reject)"""
        repository = AdRepository(session)
        
        status = AdStatus.approved if action == "approve" else AdStatus.rejected
        
        ad = await repository.update_status(
            ad_id=ad_id,
            status=status,
            rejection_reason=rejection_reason,
            channel_message_id=channel_message_id,
        )
        
        if ad:
            log.info(
                f"Ad moderated: {ad_id} -> {status}",
                extra={"ad_id": ad_id, "action": action, "status": status.value}
            )
        
        return ad

    async def upload_photo(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        extension: str = ".jpg",
    ) -> str:
        """Upload photo and return storage path"""
        return await self.storage.save(file_bytes=file_bytes, filename=filename, extension=extension)
    
    def get_repository(self, session: AsyncSession):
        return AdRepository(session)

ad_service = AdService()