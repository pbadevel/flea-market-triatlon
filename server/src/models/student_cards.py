from typing import List, TYPE_CHECKING
from sqlalchemy import BigInteger, ForeignKey, String, Date, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kit.database.models import RecordModel
from datetime import date, datetime
from src.utils import get_omsk_now

if TYPE_CHECKING:
    from src.models import User, Checkin


class StudentCard(RecordModel):
    
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), primary_key=True)
    full_name: Mapped[str] = mapped_column(String)
    phone_number: Mapped[str] = mapped_column(String, default='')
    gender: Mapped[str] = mapped_column(String)
    birth_date: Mapped[date] = mapped_column(Date)
    university: Mapped[str] = mapped_column(String(200))  
    major: Mapped[str] = mapped_column(String(100), default="Не указано") 
    study_end_date: Mapped[date] = mapped_column(Date)
    card_number: Mapped[str] = mapped_column(String, unique=True)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_omsk_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped['User'] = relationship(
        'User', 
        back_populates='student_card',
        foreign_keys=[owner_id]
    )
    
    checkins: Mapped[List['Checkin']] = relationship(
        'Checkin', 
        back_populates='student_card',
        foreign_keys='Checkin.card_number'
    )