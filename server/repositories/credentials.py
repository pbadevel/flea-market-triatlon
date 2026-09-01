from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import UserCredentials

from sqlalchemy import select, func, or_, and_
from typing import Optional, List, Tuple


class UserCredentialsRepository(BaseRepository[UserCredentials], IDRepositoryMixin[UserCredentials, int]):
    model = UserCredentials

    def get_base_stmt(self):
        """Get base statement with subscription joined and eager loaded"""
        return (
            select(UserCredentials)
        )
    
    async def get_creds_by_email(self, email: str) -> UserCredentials | None:
        stmt = select(UserCredentials).where(UserCredentials.email == email)
        return await self.get_one_or_none(stmt)
