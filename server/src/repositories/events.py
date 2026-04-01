from typing import List, TYPE_CHECKING
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import Event, Checkin
from src.utils import get_omsk_now
from src.logging import get_logger


log = get_logger()

class EventRepository(BaseRepository[Event], IDRepositoryMixin[Event, int]):
    model = Event


    async def get_active_events(self) -> List[Event]:
        # 1. Получаем активные мероприятия (с датой начала в будущем)
        now = get_omsk_now()

        event_stmt = (
            select(Event)
            .where(
                Event.active == True,
                Event.started_at > now  # Только будущие мероприятия
            )
            .order_by(Event.started_at)
        )
        
        return await self.get_all(event_stmt)
    
    async def get_user_registered_events(self, user_id: int, event_ids: list[int]):
        from src.repositories import CheckinRepository

        checkin_stmt = select(Checkin).where(
            and_(
                Checkin.owner_id == user_id,
                Checkin.is_attended == False,
                Checkin.event_id.is_not(None), Checkin.event_id.in_(event_ids)
            )
        ).options(selectinload(Checkin.event))

        user_checkins = await CheckinRepository(self.session).get_all(checkin_stmt)

        # Создаем множества для быстрой проверки
        return  {
            checkin for checkin in user_checkins if checkin.event_id
        }

    async def get_registrations_in_event(self, user_id: int, event_ids: list[int]):
        from src.repositories import CheckinRepository

        checkin_stmt = select(Checkin).where(
            and_(
                Checkin.owner_id == user_id,
                Checkin.event_id.is_not(None), Checkin.event_id.in_(event_ids)
            )
        )

        user_checkins = await CheckinRepository(self.session).get_all(checkin_stmt)

        # Создаем множества для быстрой проверки
        return  {
            checkin.event_id for checkin in user_checkins if checkin.event_id
        }
    
    async def get_event_reg_count(self, event_id: int):
        event_reg_stmt = (
            select(func.count(Checkin.id))
            .where(
                Checkin.event_id == event_id,
                or_(
                    Checkin.is_attended == False,
                    Checkin.is_attended == True
                )
            )
        )
        event_reg_result = await self.session.execute(event_reg_stmt)
        return event_reg_result.scalar()
        