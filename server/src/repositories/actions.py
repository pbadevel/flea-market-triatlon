from typing import List, TYPE_CHECKING
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import Action, Checkin
from src.utils import get_omsk_now
from src.logging import get_logger


log = get_logger()


class ActionRepository(BaseRepository[Action], IDRepositoryMixin[Action, int]):
    model = Action

    async def get_active_actions(self) -> List[Action]:
        # 1. Получаем активные мероприятия (с датой начала в будущем)
        now = get_omsk_now()

        action_stmt = (
            select(Action)
            .where(
                Action.active == True,
                # Action.started_at > now  # Только будущие мероприятия
            )
            .order_by(Action.started_at)
        )
        
        return await self.get_all(action_stmt)
    

    async def get_user_registered_actions(self, user_id: int, action_ids: list[int]):
        from src.repositories import CheckinRepository

        checkin_stmt = select(Checkin).where(
            and_(
                Checkin.owner_id == user_id,
                Checkin.is_attended == False,
                Checkin.action_id.is_not(None), Checkin.action_id.in_(action_ids)
            )
        ).options(selectinload(Checkin.action))

        user_checkins = await CheckinRepository(self.session).get_all(checkin_stmt)

        # Создаем множества для быстрой проверки
        return  {
            checkin for checkin in user_checkins if checkin.action_id
        }
    

    async def get_registrations_in_actions(self, user_id: int, action_ids: list[int]):
        from src.repositories import CheckinRepository

        checkin_stmt = select(Checkin).where(
            and_(
                Checkin.owner_id == user_id,
                Checkin.action_id.is_not(None), Checkin.action_id.in_(action_ids)
            )
        )

        user_checkins = await CheckinRepository(self.session).get_all(checkin_stmt)

        # Создаем множества для быстрой проверки
        return  {
            checkin.action_id for checkin in user_checkins if checkin.action_id
        }
    
    async def get_action_reg_count(self, action_id: int):
        action_reg_stmt = (
            select(func.count(Checkin.id))
            .where(
                Checkin.action_id == action_id,
                or_(
                    Checkin.is_attended == False,
                    Checkin.is_attended == True
                )
            )
        )
        action_reg_result = await self.session.execute(action_reg_stmt)
        return action_reg_result.scalar()
        