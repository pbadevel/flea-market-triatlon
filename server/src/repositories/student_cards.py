from sqlalchemy.orm import selectinload

from src.kit.repository.main import BaseRepository
from src.kit.repository.main import Options
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import StudentCard




class StudentCardRepository(BaseRepository[StudentCard], IDRepositoryMixin[StudentCard, int]):
    model = StudentCard


    async def get_by_owner(
        self, 
        owner_id: int, 
        with_owner: bool = True
    ):
        options: Options = []

        if with_owner:
            options.append(
                selectinload(
                    StudentCard.user
                )
            )

        stmt = self.get_base_stmt().where(
            StudentCard.owner_id == owner_id
        ).options(*options)

        return await self.get_one_or_none(stmt)