from sqlalchemy import and_

from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin, Options
from src.models import Checkin, StudentCard


class CheckinRepository(BaseRepository[Checkin], IDRepositoryMixin[Checkin, int]):
    model = Checkin

    async def _update_model(self, model: Checkin, flush=True, **kw):
        await self.update(
            obj=model,
            update_dict=kw,
            flush=flush
        )

    async def get_by_owner_id(self, owner_id, event_id = None, action_id = None, student_card = None, options: Options = ()):
        stmt = self.get_base_stmt().where(
            and_(
                Checkin.owner_id == owner_id,
                Checkin.action_id == action_id,
                Checkin.event_id == event_id,
                Checkin.student_card.has(StudentCard.card_number == student_card),
            )
        ).options(*options)
        return await self.get_one_or_none(stmt)