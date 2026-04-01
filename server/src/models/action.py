from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from src.models import StudentCard, Checkin, Media


class Action(RecordModel):
    
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Добавлено
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_reg: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Связь с Media
    media: Mapped[List['Media']] = relationship(
        'Media',
        back_populates='action_rel',
        foreign_keys='Media.action_id'
    )
    
    # Связь с регистрациями
    checkins: Mapped[List['Checkin']] = relationship(
        'Checkin',
        back_populates='action',
        foreign_keys='Checkin.action_id'
    )