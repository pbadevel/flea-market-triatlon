from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from .users import User

class Review(RecordModel):
    reviewed_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ad_id: Mapped[int | None] = mapped_column(ForeignKey("ads.id"), nullable=True)
    rating: Mapped[int]
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_user: Mapped["User"] = relationship("User", back_populates="reviews_received", foreign_keys=[reviewed_user_id])
    reviewer: Mapped["User"] = relationship("User", back_populates="reviews_given", foreign_keys=[reviewer_user_id])

class ContactLog(RecordModel):
    buyer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), nullable=False, index=True)

class DetailsLog(RecordModel):
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), nullable=False, index=True)
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)