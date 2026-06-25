from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from .users import User


class Notification(RecordModel):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ad_id: Mapped[int | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="notifications")
