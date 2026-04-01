from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config import settings
from src.enums import UserRole
from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from src.models import StudentCard, Checkin


class User(RecordModel):
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str | None]
    username: Mapped[str | None]
    is_premium: Mapped[bool] = mapped_column(default=False)
    avatar: Mapped[str | None] = mapped_column(default=None)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default=settings.default_timezone
    )

    student_card: Mapped[Optional['StudentCard']] = relationship(
        'StudentCard', 
        back_populates='user', 
        foreign_keys='StudentCard.owner_id',
        uselist=False
    )
    
    checkins: Mapped[List['Checkin']] = relationship(
        'Checkin', 
        back_populates='user',
        foreign_keys='Checkin.owner_id'
    )

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name