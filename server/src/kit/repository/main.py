from collections.abc import Sequence
from typing import Any, Self, Optional, List, Tuple, TypeVar, Generic

from sqlalchemy import Select, func, over, select
from sqlalchemy.sql import ColumnExpressionArgument
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

type Options = Sequence[ExecutableOption]


class BaseRepository[M]:
    model: type[M]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def get_base_stmt(self) -> Select[tuple[M]]:
        return select(self.model)
    

    def get_count_stmt_base(self):
        return select(func.count()).select_from(self.model)
    
    async def count_base(self, stmt) -> int:
        base_stmt = stmt 
        return (
            await self.session.execute(base_stmt)
        ).scalar_one()

    async def get_one_or_none(self, stmt: Select[tuple[M]]) -> M | None:
        return await self.session.scalar(stmt)

    async def get_all(self, stmt: Select[tuple[M]]) -> list[M]:
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def update(
        self, obj: M, update_dict: dict[str, Any], *, flush: bool = False, autocommit: bool = True
    ) -> M:
        for attr, value in update_dict.items():
            setattr(obj, attr, value)

        self.session.add(obj)

        if flush:
            await self.session.flush()

        if autocommit:
            await self.session.commit()


        return obj

    async def create(self, obj: M, *, flush: bool = False, autocommit: bool = True) -> M:
        self.session.add(obj)

        if flush:
            await self.session.flush()

        if autocommit:
            await self.session.commit()

        return obj

    async def delete(self, obj: M) -> None:
        await self.session.delete(obj)

    async def paginate(
        self, 
        stmt: Select[tuple[M]], 
        limit: int, 
        page: int,
        filters: Optional[List[ClauseElement]] = None,
        oOptions: Optional[list] = None
    ) -> Tuple[List[M], int]:
        """
        Paginate results with optional filters
        
        Args:
            stmt: Base SQLAlchemy select statement
            limit: Items per page
            page: Page number (1-indexed)
            filters: Optional list of filter conditions
        
        Returns:
            Tuple of (items, total_count)
        """
        # Apply filters if provided
        if filters:
            stmt = stmt.where(*filters)
        
        # Create a count query
        count_query = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_query) or 0
        
        # Apply pagination
        offset = (page - 1) * limit
        if oOptions:
            stmt = stmt.offset(offset).limit(limit).options(*oOptions)
        else:
            stmt = stmt.offset(offset).limit(limit)
        # Execute the paginated query
        result = await self.session.execute(stmt)
        items = list(result.scalars().unique().all())
        
        return items, total

    async def search_paginate(
        self,
        stmt: Select[tuple[M]],
        limit: int,
        page: int,
        search_column: Any = None,
        search_term: Optional[str] = None
    ) -> Tuple[List[M], int]:
        """
        Specialized pagination with search
        
        Args:
            stmt: Base SQLAlchemy select statement
            limit: Items per page
            page: Page number (1-indexed)
            search_column: Column to search on
            search_term: Search term (case-insensitive LIKE)
        
        Returns:
            Tuple of (items, total_count)
        """
        if search_term and search_column:
            search_pattern = f"%{search_term}%"
            stmt = stmt.where(search_column.ilike(search_pattern))
        
        return await self.paginate(stmt, limit, page)

    @classmethod
    def from_session(cls, session: AsyncSession) -> Self:
        return cls(session)
