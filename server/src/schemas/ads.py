from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from src.models import Ad, AdPhoto, User, Review
from src.config import settings

class AdPhotoOut(BaseModel):
    id: int
    file_id: Optional[str] = None
    storage_path: Optional[str] = None
    position: int
    
    @property
    def url(self) -> Optional[str]:
        if self.storage_path:
            return f"{settings.API_DOMAIN_URL}/uploads/{self.storage_path}"
            # return f"http://localhost:8000/uploads/{self.storage_path}"
        if self.file_id:
            return f"https://t.me/file/{self.file_id}"
        return None

    class Config:
        from_attributes = True


class ReviewOut(BaseModel):
    id: int
    reviewer_username: Optional[str]
    reviewer_tg_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SellerOut(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_trusted_seller: bool
    is_moderator: bool
    rating: float
    review_count: int
    reviews: list[ReviewOut] = Field(default_factory=list)

    @classmethod
    def from_orm(cls, user: User) -> "SellerOut":
        # Считаем средний рейтинг
        reviews = user.reviews_received
        rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0.0
        
        # Формируем последние 5 отзывов
        recent_reviews = [
            ReviewOut(
                id=r.id,
                reviewer_username=r.reviewer.username if r.reviewer else None,
                reviewer_tg_id=r.reviewer.tg_user_id if r.reviewer else 0,
                rating=r.rating,
                comment=r.comment,
                created_at=r.created_at,
            )
            for r in sorted(reviews, key=lambda x: x.created_at, reverse=True)[:5]
        ]
        
        return cls(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_trusted_seller=user.is_trusted_seller,
            is_moderator=user.is_moderator,
            rating=rating,
            review_count=len(reviews),
            reviews=recent_reviews,
        )

    class Config:
        from_attributes = True


class AdOut(BaseModel):
    id: int
    title: str
    price: int
    old_price: Optional[int] = None
    discount: Optional[int] = None
    cover_url: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    category: str
    subcategory: Optional[str] = None
    country: Optional[str] = None
    city: str
    size: Optional[str] = None
    condition: str
    description: Optional[str] = None
    created_at: datetime
    seller: Optional[SellerOut] = None
    photos: list[AdPhotoOut] = Field(default_factory=list)

    @classmethod
    def from_orm_with_photos(cls, ad: Ad, base_url: str = f"{settings.API_DOMAIN_URL}/uploads/") -> "AdOut":
        # Сортируем фото по позиции

        cover_url = None
        image_urls = []
        
        if ad.photos:
            sorted_photos = sorted(ad.photos, key=lambda p: p.position)
            for photo in sorted_photos:
                url = None
                if photo.storage_path:
                    url = f"{base_url}/{photo.storage_path}"
                elif photo.file_id:
                    url = f"https://t.me/file/{photo.file_id}"
                
                if url:
                    image_urls.append(url)
                    if cover_url is None:
                        cover_url = url
        sorted_photos = sorted(ad.photos, key=lambda p: p.position) if ad.photos else []

        seller_data = None
        if ad.seller is not None and hasattr(ad.seller, 'reviews_received'):
            seller_data = SellerOut.from_orm(ad.seller)
        
        # Считаем скидку
        discount = None
        # if ad.price:
        #     discount = round((1 - ad.price / ad.old_price) * 100)
        
        return cls(
            id=ad.id,
            title=ad.title,
            price=ad.price,
            old_price=None,
            discount=discount,
            cover_url=cover_url,
            image_urls=image_urls,
            category=ad.category,
            subcategory=ad.subcategory,
            country=ad.country,
            city=ad.city,
            size=ad.size,
            condition=ad.condition,
            description=ad.description,
            created_at=ad.created_at,
            seller=seller_data,
            photos=[AdPhotoOut.from_orm(p) for p in sorted_photos],
        )

    class Config:
        from_attributes = True