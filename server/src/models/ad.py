from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import BigInteger, Boolean, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kit.database.models import RecordModel
from .associations import ad_tags
from .enums import AdStatus, ContactMethod, AdType

if TYPE_CHECKING:
    from .users import User

class Ad(RecordModel):
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text)
    price: Mapped[int]
    city: Mapped[str]
    country: Mapped[str | None] = mapped_column(nullable=True)
    category: Mapped[str]
    subcategory: Mapped[str | None] = mapped_column(nullable=True)
    size: Mapped[str | None] = mapped_column(nullable=True)
    condition: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ad_type: Mapped[str] = mapped_column(default=AdType.sale.value, nullable=False)
    delivery_method: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default=AdStatus.pending.value, nullable=False, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_method: Mapped[str] = mapped_column(default=ContactMethod.telegram.value, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(default=False, nullable=False)
    cover_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    seller: Mapped["User"] = relationship("User", back_populates="ads", foreign_keys=[seller_user_id])
    photos: Mapped[List["AdPhoto"]] = relationship("AdPhoto", back_populates="ad", cascade="all, delete-orphan")
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=ad_tags, back_populates="ads")

class AdPhoto(RecordModel):
    ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), nullable=False, index=True)
    file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[int]
    ad: Mapped["Ad"] = relationship("Ad", back_populates="photos")

class AdEdit(RecordModel):
    original_ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text)
    price: Mapped[int]
    city: Mapped[str]
    country: Mapped[str | None] = mapped_column(nullable=True)
    category: Mapped[str]
    subcategory: Mapped[str | None] = mapped_column(nullable=True)
    size: Mapped[str | None] = mapped_column(nullable=True)
    condition: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ad_type: Mapped[str] = mapped_column(default=AdType.sale.value, nullable=False)
    delivery_method: Mapped[str | None] = mapped_column(nullable=True)
    contact_method: Mapped[str] = mapped_column(default=ContactMethod.telegram.value, nullable=False)
    cover_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)

class AdEditPhoto(RecordModel):
    edit_id: Mapped[int] = mapped_column(ForeignKey("ad_edits.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[int]

class Tag(RecordModel):
    name: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    tag_type: Mapped[str] = mapped_column(nullable=False)
    ads: Mapped[List["Ad"]] = relationship("Ad", secondary=ad_tags, back_populates="tags")