from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Enum, BigInteger, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.enums import MediaFor, MediaType
from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from src.models import Event, Action


class Media(RecordModel):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # Добавлено
    type: Mapped[MediaType] = mapped_column(Enum(MediaType), default=MediaType.PHOTO)
    used_in: Mapped[MediaFor] = mapped_column(Enum(MediaFor), default=MediaFor.EVENT)
    safe_url: Mapped[str] = mapped_column(String, nullable=False)
    
    event_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, 
        ForeignKey('events.id'),
        nullable=True
    )
    action_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, 
        ForeignKey('actions.id'),
        nullable=True
    )
    
    # Связи
    event_rel: Mapped[Optional['Event']] = relationship(
        'Event',
        back_populates='media',
        foreign_keys=[event_id]
    )
    
    action_rel: Mapped[Optional['Action']] = relationship(
        'Action',
        back_populates='media',
        foreign_keys=[action_id]
    )