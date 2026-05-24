from src.models import Ad
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class AdPhotoOut(BaseModel):
    id: int
    file_id: Optional[str] = None
    storage_path: Optional[str] = None
    position: int
    
    @property
    def url(self) -> Optional[str]:
        if self.storage_path:
            return f"http://localhost:8000/static/{self.storage_path}"
        if self.file_id:
            return f"https://t.me/file/{self.file_id}"  # или твой CDN
        return None

class AdOut(BaseModel):
    id: int
    title: str
    price: int
    old_price: Optional[int] = None
    discount: Optional[int] = None
    cover_url: Optional[str] = None  # ← то, что ждёт фронт
    image_urls: Optional[list[str]] = Field(default_factory=list)  # ← опционально, если нужна галерея
    category: str
    subcategory: Optional[str] = None
    country: Optional[str] = None
    city: str
    size: Optional[str] = None
    condition: str
    created_at: str  # или datetime

    @classmethod
    def from_orm_with_photos(cls, ad: Ad, base_url: str = "http://localhost:8000/uploads/") -> "AdOut":
        
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
        
        discount = None
        # if ad.price and ad.old_price and ad.old_price > ad.price:
        #     discount = round((1 - ad.price / ad.old_price) * 100)
        
        return cls(
            id=ad.id,
            title=ad.title,
            price=ad.price,
            old_price=None,  # TODO: discounts
            discount=discount,
            cover_url=cover_url,
            image_urls=image_urls,
            category=ad.category,
            subcategory=ad.subcategory,
            country=ad.country,
            city=ad.city,
            size=ad.size,
            condition=ad.condition,
            created_at=ad.created_at.isoformat() if ad.created_at else "",
        )