from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import User

from sqlalchemy import select, func, or_, and_
from typing import Optional, List, Tuple


class UserRepository(BaseRepository[User], IDRepositoryMixin[User, int]):
    model = User

    def get_base_stmt(self):
        """Get base statement with subscription joined and eager loaded"""
        return (
            select(User)
        )
    
    async def get_by_email(self, email: str) -> User | None:
        """Get user by uniq email"""
        from src.models import UserCredentials
        
        stmt = (
            self.get_base_stmt()
            .join(UserCredentials, UserCredentials.user_id == User.id)
            .where(UserCredentials.email == email)
        )
        return await self.get_one_or_none(stmt)
    
    async def get_users_by_ids(self, user_ids: List[int]) -> List[User]:
        """Get multiple users by their IDs"""
        stmt = self.get_base_stmt().where(User.id.in_(user_ids))
        return await self.get_all(stmt)
    
    async def get_by_tg_id(self, tg_id: int) -> User | None :
        stmt = self.get_base_stmt().where(User.tg_user_id==tg_id)
        return await self.get_one_or_none(stmt)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Найти пользователя по username"""
        stmt = self.get_base_stmt().where(User.username == username)
        return await self.get_one_or_none(stmt)
    
    async def search_users(
        self,
        search_term: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
        options: Optional[list] = None
    ) -> Tuple[List[User], int]:
        """
        Search users with advanced filters
        
        Args:
            search_term: Search by ID, name, or username
            status: Filter by subscription status
            limit: Items per page
            page: Page number
        
        Returns:
            Tuple of (users, total_count)
        """
        stmt = self.get_base_stmt()
        filters = []
        
        # Apply search filter
        if search_term:
            try:
                # Try exact ID match first
                user_id = int(search_term)
                filters.append(User.id == user_id)
            except ValueError:
                # Fall back to text search
                search_pattern = f"%{search_term}%"
                filters.append(
                    or_(
                        User.first_name.ilike(search_pattern),
                        User.last_name.ilike(search_pattern),
                        User.username.ilike(search_pattern),
                    )
                )
        
        
        # Use paginate with filters
        return await self.paginate(stmt, limit, page, filters)
    
