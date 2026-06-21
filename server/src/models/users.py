from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import BigInteger, Boolean, String, Enum
from src.enums import UserRole
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from .ad import Ad
    from .interaction import Review
    from .user_credentials import UserCredentials

class User(RecordModel):
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    
    role: Mapped[UserRole] = mapped_column(
            Enum(UserRole, native_enum=False), default=UserRole.USER
        )
    
    is_trusted_seller: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    agreed_to_terms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agreed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    subscribed_to_channel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscribed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    ads: Mapped[List["Ad"]] = relationship("Ad", back_populates="seller", foreign_keys="Ad.seller_user_id")
    reviews_received: Mapped[List["Review"]] = relationship("Review", back_populates="reviewed_user", foreign_keys="Review.reviewed_user_id")
    reviews_given: Mapped[List["Review"]] = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_user_id")
    
    credentials: Mapped["UserCredentials | None"] = relationship(
        "UserCredentials",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

class Blacklist(RecordModel):
    """Забаненные пользователи."""
    __tablename__ = "blacklist" # pyright: ignore # явное имя, чтобы не стало "blacklists" по авто-правилу
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)