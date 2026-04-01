from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import User

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload, contains_eager
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple


class UserRepository(BaseRepository[User], IDRepositoryMixin[User, int]):
    model = User

    def get_base_stmt(self):
        """Get base statement with subscription joined and eager loaded"""
        return (
            select(User)
        )

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
    
    async def get_users_by_ids(self, user_ids: List[int]) -> List[User]:
        """Get multiple users by their IDs"""
        stmt = self.get_base_stmt().where(User.id.in_(user_ids))
        return await self.get_all(stmt)
    
