# student_checkin.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from src.models import User, StudentCard, Event, Action


class Checkin(RecordModel):
    """Модель для регистрации и посещения мероприятий"""
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    card_number: Mapped[str] = mapped_column(String, ForeignKey('student_cards.card_number'), nullable=False)
    
    # Связь с Event или Action
    event_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('events.id'), nullable=True)
    action_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('actions.id'), nullable=True)
    
    # Время регистрации
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Время отметки о посещении
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Статус посещения
    is_attended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Связи
    user: Mapped['User'] = relationship(
        'User', 
        back_populates='checkins',
        foreign_keys=[owner_id]
    )
    
    student_card: Mapped['StudentCard'] = relationship(
        'StudentCard',
        back_populates='checkins',
        foreign_keys=[card_number]
    )
    
    event: Mapped[Optional['Event']] = relationship(
        'Event',
        back_populates='checkins',
        foreign_keys=[event_id]
    )
    
    action: Mapped[Optional['Action']] = relationship(
        'Action',
        back_populates='checkins',
        foreign_keys=[action_id]
    )